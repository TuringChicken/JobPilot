from types import SimpleNamespace

import pytest
from openai import OpenAIError
from pydantic import BaseModel

from app.config import Settings
from app.services.llm import LLMError, StructuredLLM, build_llm


class Answer(BaseModel):
    value: str


class FakeCompletions:
    """Stands in for client.chat.completions; `parse` = json_schema mode, `create` = JSON mode."""

    def __init__(self, parsed=None, content=None, error=None):
        self.parsed, self.content, self.error, self.kwargs = parsed, content, error, None

    def _respond(self, kwargs, message):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    def parse(self, **kwargs):
        return self._respond(kwargs, SimpleNamespace(parsed=self.parsed))

    def create(self, **kwargs):
        return self._respond(kwargs, SimpleNamespace(content=self.content))


def fake_llm(json_schema_mode=True, reasoning_effort=None, extra_body=None, **kwargs):
    completions = FakeCompletions(**kwargs)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    llm = StructuredLLM(client, "test-model", json_schema_mode, reasoning_effort, extra_body)
    return llm, completions


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, api_key="k", **overrides)


# --- json_schema mode (Azure) ---


def test_schema_mode_returns_structured_output_and_sends_schema():
    llm, completions = fake_llm(parsed=Answer(value="ok"))
    assert llm.parse("sys", "user", Answer) == Answer(value="ok")
    assert completions.kwargs["model"] == "test-model"
    assert completions.kwargs["response_format"] is Answer
    assert "reasoning_effort" not in completions.kwargs
    assert "extra_body" not in completions.kwargs


def test_schema_mode_forwards_reasoning_effort_when_set():
    llm, completions = fake_llm(reasoning_effort="low", parsed=Answer(value="ok"))
    llm.parse("sys", "user", Answer)
    assert completions.kwargs["reasoning_effort"] == "low"


def test_schema_mode_rejects_missing_output():
    llm, _ = fake_llm(parsed=None)
    with pytest.raises(LLMError):
        llm.parse("sys", "user", Answer)


def test_wraps_sdk_errors():
    llm, _ = fake_llm(error=OpenAIError("connection refused"))
    with pytest.raises(LLMError):
        llm.parse("sys", "user", Answer)


# --- JSON-object mode (DashScope) ---


def test_json_mode_embeds_schema_and_validates_output():
    llm, completions = fake_llm(
        json_schema_mode=False, extra_body={"enable_thinking": False}, content='{"value": "ok"}'
    )
    assert llm.parse("sys", "user", Answer) == Answer(value="ok")
    assert completions.kwargs["response_format"] == {"type": "json_object"}
    assert completions.kwargs["extra_body"] == {"enable_thinking": False}
    system = completions.kwargs["messages"][0]["content"]
    assert system.startswith("sys")
    assert '"value"' in system and "JSON Schema" in system


@pytest.mark.parametrize("content", ['{"wrong": 1}', "not json", ""])
def test_json_mode_rejects_invalid_output(content):
    llm, _ = fake_llm(json_schema_mode=False, content=content)
    with pytest.raises(LLMError):
        llm.parse("sys", "user", Answer)


def test_json_mode_logs_failing_fields_without_values(caplog):
    llm, _ = fake_llm(json_schema_mode=False, content='{"value": ["Secret Resume Text"]}')
    with pytest.raises(LLMError):
        llm.parse("sys", "user", Answer)
    assert "value (string_type)" in caplog.text
    assert "Secret Resume Text" not in caplog.text


# --- provider selection ---


def test_build_llm_defaults_to_dashscope_and_requires_key():
    assert make_settings().llm_provider == "dashscope"
    assert build_llm(make_settings()) is None


def test_build_llm_dashscope_uses_json_mode_without_thinking():
    llm = build_llm(make_settings(dashscope_api_key="sk-test"))
    assert llm is not None
    assert llm.model == "qwen3.8-27b"
    assert llm.json_schema_mode is False
    assert llm.extra_body == {"enable_thinking": False}
    assert str(llm.client.base_url).startswith("https://dashscope.aliyuncs.com/compatible-mode/v1")


def test_build_llm_dashscope_ignores_azure_only_reasoning_effort():
    llm = build_llm(make_settings(dashscope_api_key="sk-test", llm_reasoning_effort="low"))
    assert llm.reasoning_effort is None


def test_build_llm_azure_requires_credentials():
    assert build_llm(make_settings(llm_provider="azure")) is None


def test_build_llm_azure_uses_deployment_name_and_schema_mode():
    llm = build_llm(
        make_settings(
            llm_provider="azure",
            azure_openai_endpoint="https://res.openai.azure.com/openai/v1/",
            azure_openai_api_key="secret",
            azure_openai_chat_deployment="gpt-deploy",
        )
    )
    assert llm is not None
    assert llm.model == "gpt-deploy"
    assert llm.json_schema_mode is True
    assert str(llm.client.base_url).startswith("https://res.openai.azure.com/openai/v1")
