from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Ops Approval Workflow"
    env: str = "local"
    db_path: str = "data/app.db"
    llm_mode: str = "mock"
    llm_fallback_enabled: bool = True
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "AI_OPS_OPENAI_API_KEY"),
    )
    openai_model: str = Field(
        default="gpt-5.4-mini",
        validation_alias=AliasChoices("AI_OPS_OPENAI_MODEL", "OPENAI_MODEL"),
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("AI_OPS_OPENAI_BASE_URL", "OPENAI_BASE_URL"),
    )
    openai_timeout_seconds: float = Field(
        default=15,
        validation_alias=AliasChoices("AI_OPS_OPENAI_TIMEOUT_SECONDS", "OPENAI_TIMEOUT_SECONDS"),
    )
    openai_max_output_tokens: int = 700

    model_config = SettingsConfigDict(
        env_prefix="AI_OPS_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
