"""Fixtures shared by the whole suite.

The database fixtures live here rather than in a subdirectory's conftest so that any test can
ask for one. Unit tests that do not ask for a database never touch one.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


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

from tests.support.db import prepare_database, truncate_all  # noqa: E402


@pytest.fixture(scope="session")
def database() -> None:
    import asyncio

    asyncio.run(prepare_database(os.environ["CLEARED_MIGRATION_DATABASE_URL"]))


@pytest.fixture
async def app_session(database: None) -> AsyncIterator[AsyncSession]:
    """A session as the application role: row-level security applies."""
    engine = create_async_engine(os.environ["CLEARED_DATABASE_URL"], poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.fixture
async def owner_session(database: None) -> AsyncIterator[AsyncSession]:
    """A session as the owner role, used to arrange fixtures.

    The owner may bypass row-level security, but this fixture sets the tenant anyway so that
    the arrangement path looks like the application's.
    """
    engine = create_async_engine(os.environ["CLEARED_MIGRATION_DATABASE_URL"], poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_tables(request: pytest.FixtureRequest) -> AsyncIterator[None]:
    """Empty the tables after every test that used the database."""
    yield
    if "database" not in request.fixturenames:
        return

    engine = create_async_engine(os.environ["CLEARED_MIGRATION_DATABASE_URL"], poolclass=NullPool)
    try:
        await truncate_all(engine)
    finally:
        await engine.dispose()
