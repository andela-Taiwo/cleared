"""Tenant context.

Every request that touches tenant data runs inside one transaction, and the first statement in
that transaction tells PostgreSQL which tenant it is. `set_config(..., true)` is transaction
local, so a pooled connection cannot carry one request's tenant into the next.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant(session: AsyncSession, organization_id: uuid.UUID) -> None:
    await session.execute(
        text("select set_config('app.tenant_id', :tenant, true)"),
        {"tenant": str(organization_id)},
    )


@asynccontextmanager
async def tenant_scope(
    session: AsyncSession, organization_id: uuid.UUID
) -> AsyncGenerator[AsyncSession, None]:
    """Open a transaction scoped to one tenant."""
    async with session.begin():
        await set_tenant(session, organization_id)
        yield session
