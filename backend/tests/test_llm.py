from types import SimpleNamespace

import pytest
from openai import OpenAIError
from pydantic import BaseModel

from app.config import Settings
from app.services.llm import LLMError, StructuredLLM, build_llm


class Answer(BaseModel):
    value: str


class FakeCompletions:
    def __init__(self, parsed=None, error=None):
        self.parsed, self.error, self.kwargs = parsed, error, None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        message = SimpleNamespace(parsed=self.parsed)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def fake_llm(reasoning_effort=None, **kwargs):
    completions = FakeCompletions(**kwargs)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return StructuredLLM(client, "test-model", reasoning_effort), completions


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, api_key="k", **overrides)


def test_parse_returns_structured_output_and_sends_schema():
    llm, completions = fake_llm(parsed=Answer(value="ok"))
    assert llm.parse("sys", "user", Answer) == Answer(value="ok")
    assert completions.kwargs["model"] == "test-model"
    assert completions.kwargs["response_format"] is Answer
    assert "reasoning_effort" not in completions.kwargs


def test_parse_forwards_reasoning_effort_when_set():
    llm, completions = fake_llm(reasoning_effort="none", parsed=Answer(value="ok"))
    llm.parse("sys", "user", Answer)
    assert completions.kwargs["reasoning_effort"] == "none"


def test_parse_wraps_sdk_errors():
    llm, _ = fake_llm(error=OpenAIError("connection refused"))
    with pytest.raises(LLMError):
        llm.parse("sys", "user", Answer)


def test_parse_rejects_missing_output():
    llm, _ = fake_llm(parsed=None)
    with pytest.raises(LLMError):
        llm.parse("sys", "user", Answer)


def test_build_llm_requires_credentials():
    assert build_llm(make_settings()) is None


def test_build_llm_uses_azure_deployment_name():
    llm = build_llm(
        make_settings(
            azure_openai_endpoint="https://res.openai.azure.com/openai/v1/",
            azure_openai_api_key="secret",
            azure_openai_chat_deployment="gpt-deploy",
        )
    )
    assert llm is not None
    assert llm.model == "gpt-deploy"
    assert str(llm.client.base_url).startswith("https://res.openai.azure.com/openai/v1")
