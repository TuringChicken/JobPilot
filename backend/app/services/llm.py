import logging
from dataclasses import dataclass

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

from app.config import Settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class StructuredLLM:
    """Structured-output chat calls against the Azure OpenAI v1 (OpenAI-compatible) API."""

    client: OpenAI
    model: str
    reasoning_effort: str | None = None

    def parse[T: BaseModel](self, instructions: str, content: str, schema: type[T]) -> T:
        extra = {"reasoning_effort": self.reasoning_effort} if self.reasoning_effort else {}
        try:
            completion = self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": content},
                ],
                response_format=schema,
                **extra,
            )
        except (OpenAIError, ValidationError) as exc:
            # Log the error type only; messages may echo prompt content (resume/JD text).
            logger.warning("LLM call failed: %s", type(exc).__name__)
            raise LLMError(f"LLM call failed ({type(exc).__name__}).") from exc

        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise LLMError("LLM returned no structured output.")
        return parsed


def build_llm(settings: Settings) -> StructuredLLM | None:
    """Return the configured LLM, or None if Azure OpenAI credentials are missing."""
    api_key = settings.azure_openai_api_key.get_secret_value()
    if not (settings.azure_openai_endpoint and api_key and settings.azure_openai_chat_deployment):
        return None
    client = OpenAI(
        base_url=settings.azure_openai_endpoint,
        api_key=api_key,
        timeout=settings.llm_timeout_seconds,
    )
    return StructuredLLM(
        client, settings.azure_openai_chat_deployment, settings.llm_reasoning_effort
    )
