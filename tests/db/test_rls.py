"""Tenant isolation is a database guarantee, not a convention.

Every one of these tests would still pass if the application forgot a `where` clause, which is
the point: the guarantee lives in the policy, not in the query.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from cleared.db.tenant import set_tenant
from cleared.domain.models import Organization, User


def new_id() -> uuid.UUID:
    return uuid.uuid4()


async def seed_org(session: AsyncSession, name: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Arrange one organisation with one user, as the owner role, tenant set first."""
    org_id, user_id = new_id(), new_id()
    async with session.begin():
        await set_tenant(session, org_id)
        session.add(Organization(id=org_id, name=name.title(), slug=name.lower()))
        await session.flush()
        session.add(
            User(
                id=user_id,
                organization_id=org_id,
                email=f"admin@{name.lower()}.example",
                name="Admin",
                role="admin",
                password_hash="x",
            )
        )
    return org_id, user_id


@pytest.fixture
async def two_orgs(owner_session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    first, _ = await seed_org(owner_session, "northwind")
    second, _ = await seed_org(owner_session, "beacon")
    return first, second


async def test_app_role_sees_nothing_without_a_tenant(app_session: AsyncSession) -> None:
    users = await app_session.scalars(select(User))
    organisations = await app_session.scalars(select(Organization))

    assert users.all() == []
    assert organisations.all() == []


async def test_app_role_only_sees_its_own_tenant(
    app_session: AsyncSession, two_orgs: tuple[uuid.UUID, uuid.UUID]
) -> None:
    northwind, _ = two_orgs

    async with app_session.begin():
        await set_tenant(app_session, northwind)
        users = (await app_session.scalars(select(User))).all()
        organisations = (await app_session.scalars(select(Organization))).all()

    assert [user.email for user in users] == ["admin@northwind.example"]
    assert [organisation.name for organisation in organisations] == ["Northwind"]


async def test_app_role_cannot_write_into_another_tenant(
    app_session: AsyncSession, two_orgs: tuple[uuid.UUID, uuid.UUID]
) -> None:
    northwind, beacon = two_orgs

    with pytest.raises(DBAPIError) as raised:
        async with app_session.begin():
            await set_tenant(app_session, northwind)
            app_session.add(
                User(
                    organization_id=beacon,
                    email="intruder@beacon.example",
                    name="Intruder",
                    role="admin",
                    password_hash="x",
                )
            )

    assert "row-level security" in str(raised.value).lower()


async def test_app_role_cannot_update_another_tenant(
    app_session: AsyncSession, two_orgs: tuple[uuid.UUID, uuid.UUID]
) -> None:
    northwind, _ = two_orgs

    async with app_session.begin():
        await set_tenant(app_session, northwind)
        result = await app_session.execute(
            update(User).where(User.email == "admin@beacon.example").values(name="Changed")
        )

    assert result.rowcount == 0  # type: ignore[attr-defined]


# Global tables are reviewed, not accidental. Anything else must be tenant-isolated.
GLOBAL_TABLES = {"alembic_version", "sessions"}

TENANT_TABLES = {"organizations", "users"}


async def test_every_tenant_table_has_the_standard_policy(owner_session: AsyncSession) -> None:
    """A new table without a policy is a leak, so both sets are asserted explicitly."""

    async with owner_session.begin():
        rows = await owner_session.execute(
            text(
                """
                select c.relname as table_name, p.polname as policy_name
                from pg_class c
                join pg_namespace n on n.oid = c.relnamespace
                join pg_policy p on p.polrelid = c.oid
                where n.nspname = 'public' and c.relkind = 'r'
                """
            )
        )
        policies = {row.table_name: row.policy_name for row in rows}

        everything = await owner_session.execute(
            text(
                """
                select c.relname
                from pg_class c
                join pg_namespace n on n.oid = c.relnamespace
                where n.nspname = 'public' and c.relkind = 'r'
                """
            )
        )
        all_tables = set(everything.scalars().all())

        protected = await owner_session.execute(
            text(
                """
                select c.relname
                from pg_class c
                join pg_namespace n on n.oid = c.relnamespace
                where n.nspname = 'public' and c.relkind = 'r' and c.relrowsecurity
                """
            )
        )
        protected_tables = set(protected.scalars().all())

    assert protected_tables == TENANT_TABLES
    assert {table: policies[table] for table in TENANT_TABLES} == dict.fromkeys(
        TENANT_TABLES, "tenant_isolation"
    )
    # Every table is either isolated or on the reviewed list. No silent third option.
    assert all_tables - protected_tables == GLOBAL_TABLES
