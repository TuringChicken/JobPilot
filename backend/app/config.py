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

    llm_timeout_seconds: float = 120.0
    # None = model default. Only reasoning-model deployments accept this parameter.
    llm_reasoning_effort: Literal["none", "low", "medium", "high"] | None = None

    azure_openai_endpoint: str = ""
    azure_openai_api_key: SecretStr = SecretStr("")
    azure_openai_chat_deployment: str = ""

    cors_origins: list[str] = []
    max_resume_bytes: int = 5 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
