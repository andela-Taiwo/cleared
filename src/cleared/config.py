"""Application configuration.

Settings come from the environment (and `.env` in development). Configuration that the app
cannot run without — the database URL and the signing key — has no default on purpose: a
missing secret should fail at boot, not at the first request.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CLEARED_",
        extra="ignore",
    )

    environment: Literal["dev", "test", "prod"] = "dev"

    # Runtime connection: the non-owner role, subject to row-level security.
    database_url: str
    # Migrations connect as the owner role, which may change the schema.
    migration_database_url: str | None = None

    secret_key: SecretStr = Field(min_length=32)
    session_cookie_name: str = "cleared_session"
    session_ttl_hours: int = 12

    upload_dir: Path = Path("var/uploads")
    web_origin: str = "http://localhost:5173"
    scheduler_token: SecretStr | None = None

    log_level: str = "INFO"
    log_json: bool = False

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
