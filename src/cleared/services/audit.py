"""Writing audit events.

Called inside the caller's transaction, so the record and the change it describes commit
together or not at all.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from cleared.domain.models import AuditEvent

if TYPE_CHECKING:
    from cleared.api.deps import Principal


def record(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    actor_name: str,
    action: str,
    entity: str,
    entity_id: uuid.UUID | None = None,
    data: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditEvent(
            id=uuid7(),
            organization_id=organization_id,
            actor_id=actor_id,
            actor_name=actor_name,
            action=action,
            entity=entity,
            entity_id=entity_id,
            data=data or {},
        )
    )


def record_for(
    session: AsyncSession,
    principal: Principal,
    *,
    action: str,
    entity: str,
    entity_id: uuid.UUID | None = None,
    data: dict[str, object] | None = None,
) -> None:
    record(
        session,
        organization_id=principal.organization_id,
        actor_id=principal.user_id,
        actor_name=principal.name,
        action=action,
        entity=entity,
        entity_id=entity_id,
        data=data,
    )
