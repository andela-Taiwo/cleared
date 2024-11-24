"""Database harness.

Two rules, both enforced here rather than in a comment:

1. Tests only ever touch a database whose name ends in `_test`. The name is checked in the URL
   *and* with `select current_database()`, because a URL is easy to override by accident.
2. The schema is dropped and rebuilt from the real migrations at the start of the session, so
   the tests exercise the migrations rather than `metadata.create_all`.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urlparse

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[2]


def database_name(url: str) -> str:
    return urlparse(url.replace("+asyncpg", "")).path.lstrip("/")


def assert_test_database(url: str) -> str:
    name = database_name(url)
    if not name.endswith("_test"):
        raise RuntimeError(
            f"Refusing to run the test suite against {name!r}: the database name must end in _test."
        )
    return name


async def prepare_database(owner_url: str) -> None:
    """Drop the schema, rebuild it from migrations."""
    expected = assert_test_database(owner_url)

    engine = create_async_engine(owner_url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            actual = await connection.scalar(text("select current_database()"))
            if actual != expected:
                raise RuntimeError(f"Connected to {actual!r}, expected {expected!r}.")

            await connection.execute(text("drop schema public cascade"))
            await connection.execute(text("create schema public"))
            # Dropping the schema also drops its default privileges, so both the schema grant
            # and the default privileges are restored here, before any table is created.
            await connection.execute(text("grant usage on schema public to cleared_app"))
            await connection.execute(
                text(
                    "alter default privileges for role cleared_owner in schema public "
                    "grant select, insert, update, delete on tables to cleared_app"
                )
            )
            await connection.execute(
                text(
                    "alter default privileges for role cleared_owner in schema public "
                    "grant usage, select on sequences to cleared_app"
                )
            )
    finally:
        await engine.dispose()

    config = Config(str(ROOT / "alembic.ini"))
    await asyncio.to_thread(command.upgrade, config, "head")

    # Tables that already existed when the default privileges were restored keep their old
    # grants, so make the grant explicit.
    engine = create_async_engine(owner_url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.execute(
                text(
                    "grant select, insert, update, delete on all tables in schema public "
                    "to cleared_app"
                )
            )
    finally:
        await engine.dispose()


async def truncate_all(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        await connection.execute(
            text("truncate table users, organizations restart identity cascade")
        )
        await connection.commit()
