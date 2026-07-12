from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI Ops Approval Workflow", min_length=1)
    env: str = Field(default="local", min_length=1)
    db_path: str = Field(default="data/app.db", min_length=1)
    api_key: SecretStr | None = None
    llm_mode: Literal["mock", "openai"] = "mock"
    llm_fallback_enabled: bool = True
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "AI_OPS_OPENAI_API_KEY"),
    )
    openai_model: str = Field(
        default="gpt-5.4-mini",
        min_length=1,
        validation_alias=AliasChoices("AI_OPS_OPENAI_MODEL", "OPENAI_MODEL"),
    )
    openai_base_url: AnyHttpUrl = Field(
        default=AnyHttpUrl("https://api.openai.com/v1"),
        validation_alias=AliasChoices("AI_OPS_OPENAI_BASE_URL", "OPENAI_BASE_URL"),
    )
    openai_timeout_seconds: float = Field(
        default=15,
        gt=0,
        le=120,
        validation_alias=AliasChoices("AI_OPS_OPENAI_TIMEOUT_SECONDS", "OPENAI_TIMEOUT_SECONDS"),
    )
    openai_max_output_tokens: int = Field(default=700, ge=100, le=4_000)

    model_config = SettingsConfigDict(
        env_prefix="AI_OPS_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
