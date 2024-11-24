from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tests.support.db import prepare_database, truncate_all


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    import asyncio

    from tests.support.db import assert_test_database

    owner_url = os.environ["CLEARED_MIGRATION_DATABASE_URL"]
    assert_test_database(owner_url)
    asyncio.run(prepare_database(owner_url))


@pytest.fixture
async def app_session() -> AsyncIterator[AsyncSession]:
    """A session as the application role: row-level security applies."""
    engine = create_async_engine(os.environ["CLEARED_DATABASE_URL"], poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.fixture
async def owner_session() -> AsyncIterator[AsyncSession]:
    """A session as the owner role, used only to arrange fixtures.

    Row-level security is forced, but the owner is the table owner, so `FORCE` still applies —
    the owner therefore sets the tenant too when it reads tenant data.
    """
    engine = create_async_engine(os.environ["CLEARED_MIGRATION_DATABASE_URL"], poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_tables(database: None) -> AsyncIterator[None]:
    from sqlalchemy.ext.asyncio import create_async_engine as create_engine

    engine = create_engine(os.environ["CLEARED_MIGRATION_DATABASE_URL"], poolclass=NullPool)
    try:
        yield
    finally:
        await truncate_all(engine)
        await engine.dispose()
