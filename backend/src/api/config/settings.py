# src/api/config/settings.py
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # No defaults — the app must refuse to start without these.
    database_url: str
    redis_url: str
    qdrant_url: str
    jwt_secret_key: str

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Filled in later phases; empty is valid for now.
    llm_api_key: str = ""
    llm_base_url: str = ""
    embedding_model: str = ""
    storage_bucket: str = ""
    storage_endpoint_url: str = ""
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
