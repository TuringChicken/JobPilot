import json
import logging
from dataclasses import dataclass
from typing import Any

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

from app.config import Settings

logger = logging.getLogger(__name__)

_JSON_OBJECT_SUFFIX = (
    "\n\nRespond with a single JSON object only, no prose or code fences. "
    "It must validate against this JSON Schema:\n{schema}"
)


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class StructuredLLM:
    """Structured-output chat calls over an OpenAI-compatible API (Azure v1, DashScope).

    json_schema_mode=True uses native schema-constrained decoding (response_format=<model>).
    False uses plain JSON-object mode with the schema embedded in the system prompt, for
    providers without json_schema support; the output is still validated by Pydantic.
    """

    client: OpenAI
    model: str
    json_schema_mode: bool = True
    reasoning_effort: str | None = None
    extra_body: dict[str, Any] | None = None

    def parse[T: BaseModel](self, instructions: str, content: str, schema: type[T]) -> T:
        kwargs: dict[str, Any] = {}
        if self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body

        try:
            if self.json_schema_mode:
                parsed = self._parse_json_schema(instructions, content, schema, kwargs)
            else:
                parsed = self._parse_json_object(instructions, content, schema, kwargs)
        except (OpenAIError, ValidationError) as exc:
            # Log the error type only; messages may echo prompt content (resume/JD text).
            logger.warning("LLM call failed: %s%s", type(exc).__name__, _error_locations(exc))
            raise LLMError(f"LLM call failed ({type(exc).__name__}).") from exc

        if parsed is None:
            raise LLMError("LLM returned no structured output.")
        return parsed

    def _parse_json_schema[T: BaseModel](
        self, instructions: str, content: str, schema: type[T], kwargs: dict[str, Any]
    ) -> T | None:
        completion = self.client.chat.completions.parse(
            model=self.model,
            messages=_messages(instructions, content),
            response_format=schema,
            **kwargs,
        )
        return completion.choices[0].message.parsed

    def _parse_json_object[T: BaseModel](
        self, instructions: str, content: str, schema: type[T], kwargs: dict[str, Any]
    ) -> T | None:
        system = instructions + _JSON_OBJECT_SUFFIX.format(
            schema=json.dumps(schema.model_json_schema(), ensure_ascii=False)
        )
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=_messages(system, content),
            response_format={"type": "json_object"},
            **kwargs,
        )
        text = completion.choices[0].message.content
        return schema.model_validate_json(text) if text else None


def _error_locations(exc: Exception) -> str:
    """Field paths and error types of a ValidationError, without the offending values."""
    if not isinstance(exc, ValidationError):
        return ""
    errors = exc.errors(include_input=False, include_context=False, include_url=False)
    return " " + ", ".join(
        f"{'.'.join(map(str, e['loc'])) or '<root>'} ({e['type']})" for e in errors[:10]
    )


def _messages(system: str, user: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_llm(settings: Settings) -> StructuredLLM | None:
    """Return the configured LLM, or None if the selected provider lacks credentials."""
    if settings.llm_provider == "dashscope":
        api_key = settings.dashscope_api_key.get_secret_value()
        if not api_key:
            return None
        client = OpenAI(
            base_url=settings.dashscope_base_url,
            api_key=api_key,
            timeout=settings.llm_timeout_seconds,
        )
        return StructuredLLM(
            client,
            settings.dashscope_model,
            json_schema_mode=False,
            # Hybrid Qwen3 models can't combine thinking with JSON mode; keep it off.
            extra_body={"enable_thinking": False},
        )

    api_key = settings.azure_openai_api_key.get_secret_value()
    if not (settings.azure_openai_endpoint and api_key and settings.azure_openai_chat_deployment):
        return None
    client = OpenAI(
        base_url=settings.azure_openai_endpoint,
        api_key=api_key,
        timeout=settings.llm_timeout_seconds,
    )
    return StructuredLLM(
        client,
        settings.azure_openai_chat_deployment,
        reasoning_effort=settings.llm_reasoning_effort,
    )
