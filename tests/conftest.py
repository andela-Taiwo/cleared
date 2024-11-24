from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class TestDatabases(BaseSettings):
    """Test database URLs: `.env.test`, then `.env`, then the environment."""

    model_config = SettingsConfigDict(
        env_file=(".env.test", ".env"), env_prefix="CLEARED_TEST_", extra="ignore"
    )

    app_database_url: str = (
        "postgresql+asyncpg://cleared_app:cleared_app@127.0.0.1:5432/cleared_test"
    )
    owner_database_url: str = (
        "postgresql+asyncpg://cleared_owner:cleared_owner@127.0.0.1:5432/cleared_test"
    )


_databases = TestDatabases()

# Set before any application module is imported, so `Settings` never sees a development URL.
os.environ["CLEARED_ENVIRONMENT"] = "test"
os.environ["CLEARED_DATABASE_URL"] = _databases.app_database_url
os.environ["CLEARED_MIGRATION_DATABASE_URL"] = _databases.owner_database_url
os.environ.setdefault("CLEARED_SECRET_KEY", "test-only-secret-key-not-for-production")
