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
    migration_database_url: str
    redis_url: str
    qdrant_url: str
    jwt_secret_key: str

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # How long a resolved membership may be reused without re-reading the row.
    # Correctness comes from invalidating the key on every membership write; this only
    # bounds staleness for changes made outside the service (§7.8), so it is short.
    membership_cache_ttl_seconds: int = 30

    # Filled in later phases; empty is valid for now.
    llm_api_key: str = ""
    llm_base_url: str = ""
    embedding_model: str = ""

    # Object storage — Phase 6. Empty is still valid: the app boots without it and
    # logs a warning, and only the document routes refuse (503). Making these
    # required would stop the whole API starting on a machine with no bucket, which
    # would take authentication and every other phase down with it.
    storage_bucket: str = ""
    storage_endpoint_url: str = ""
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    # Cloudflare R2 has one region and calls it "auto". A real S3 bucket needs its own.
    storage_region: str = "auto"

    # The upload ceiling, enforced against bytes actually read. 100 MiB covers the
    # document formats this system ingests; raising it is a settings change, and the
    # streaming upload path means it costs memory nowhere.
    max_upload_bytes: int = 100 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
