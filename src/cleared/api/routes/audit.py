"""The audit trail."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from cleared.api.deps import PrincipalDep, SessionDep
from cleared.db.tenant import tenant_scope
from cleared.domain.models import AuditEvent

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: object
    actor_name: str
    action: str
    entity: str
    entity_id: object
    data: dict[str, object]
    created_at: object


@router.get("", summary="What has happened in this agency")
async def list_events(
    principal: PrincipalDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditEventOut]:
    async with tenant_scope(session, principal.organization_id):
        rows = (
            await session.scalars(
                select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
            )
        ).all()
        return [AuditEventOut.model_validate(row) for row in rows]
