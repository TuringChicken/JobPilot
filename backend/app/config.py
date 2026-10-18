from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_ignore_empty: "KEY=" in .env means "use the default", not an empty-string value.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True
    )

    api_key: SecretStr
    database_url: str = "sqlite:///./data/jobpilot.db"

    llm_provider: Literal["ollama", "azure"] = "ollama"
    llm_timeout_seconds: float = 300.0
    # None = model default. "none" disables thinking on Ollama reasoning models (faster,
    # but noticeably more prone to following instructions embedded in the input).
    llm_reasoning_effort: Literal["none", "low", "medium", "high"] | None = None

    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen3:8b"

    azure_openai_endpoint: str = ""
    azure_openai_api_key: SecretStr = SecretStr("")
    azure_openai_chat_deployment: str = ""

    cors_origins: list[str] = []
    max_resume_bytes: int = 5 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
