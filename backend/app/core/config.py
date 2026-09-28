"""Application settings, read from environment variables (prefix `EDGELEDGER_`) and `.env`.

Secrets are `SecretStr` so they never appear in reprs or logs. Provider keys are backend-only
and must never be sent to the browser (CLAUDE.md 6).
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EDGELEDGER_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["dev", "test", "staging", "prod"] = "dev"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://edgeledger:edgeledger@localhost:5432/edgeledger"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_bucket: str = "edgeledger-dev"
    s3_access_key: SecretStr = SecretStr("")
    s3_secret_key: SecretStr = SecretStr("")

    # Licensed data providers (PRD 4.8). Empty until real keys exist; tests use recorded fixtures.
    sportmonks_api_key: SecretStr = SecretStr("")
    the_odds_api_key: SecretStr = SecretStr("")
    football_data_api_key: SecretStr = SecretStr("")


@lru_cache
def get_settings() -> Settings:
    return Settings()
