from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Ops Approval Workflow"
    env: str = "local"
    db_path: str = "data/app.db"
    llm_mode: str = "mock"

    model_config = SettingsConfigDict(
        env_prefix="AI_OPS_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

