"""Arranging realistic data for tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from cleared.db.tenant import set_tenant
from cleared.domain.models import Organization, User
from cleared.security.passwords import hash_password

PASSWORD = "correct-horse-battery-staple"


@dataclass(frozen=True)
class Agency:
    organization_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    password: str


async def create_agency(
    session: AsyncSession,
    *,
    name: str = "northwind",
    email: str | None = None,
    role: str = "admin",
    timezone: str = "America/New_York",
) -> Agency:
    """One organisation with one signed-in-able user.

    The tenant is set before the rows are written because row-level security applies to the
    owner role too; that is exactly how signup will work.
    """
    organization_id = uuid7()
    user_id = uuid7()
    address = email or f"{role}@{name}.example"

    async with session.begin():
        await set_tenant(session, organization_id)
        session.add(
            Organization(
                id=organization_id,
                name=name.replace("-", " ").title(),
                slug=name,
                timezone=timezone,
            )
        )
        await session.flush()
        session.add(
            User(
                id=user_id,
                organization_id=organization_id,
                email=address,
                name=f"{role.title()} User",
                role=role,
                password_hash=hash_password(PASSWORD),
            )
        )

    return Agency(
        organization_id=organization_id, user_id=user_id, email=address, password=PASSWORD
    )
