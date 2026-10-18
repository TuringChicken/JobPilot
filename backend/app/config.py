from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_key: SecretStr
    database_url: str = "sqlite:///./data/jobpilot.db"

    azure_openai_endpoint: str = ""
    azure_openai_api_key: SecretStr = SecretStr("")
    azure_openai_chat_deployment: str = ""

    cors_origins: list[str] = []
    max_resume_bytes: int = 5 * 1024 * 1024

    @property
    def llm_configured(self) -> bool:
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key.get_secret_value()
            and self.azure_openai_chat_deployment
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
