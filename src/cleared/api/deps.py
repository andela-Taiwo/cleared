"""Request-scoped dependencies."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from cleared.api.errors import Problem
from cleared.config import get_settings
from cleared.db.session import get_session
from cleared.db.tenant import set_tenant
from cleared.domain.models import AuthSession, User
from cleared.security.sessions import hash_token

settings = get_settings()


@dataclass(frozen=True)
class Principal:
    """Who is making this request, and which tenant it belongs to."""

    user_id: uuid.UUID
    organization_id: uuid.UUID
    email: str
    name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


async def get_principal(
    request: Request, session: Annotated[AsyncSession, Depends(get_session)]
) -> Principal:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise Problem(401, "Not signed in")

    digest = hash_token(token)

    async with session.begin():
        auth_session = await session.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == digest,
                AuthSession.expires_at > func.now(),
            )
        )
        if auth_session is None:
            raise Problem(401, "Session expired")

        # The session names its tenant; from here on, every query is filtered by the database.
        await set_tenant(session, auth_session.organization_id)
        user = await session.get(User, auth_session.user_id)
        if user is None or not user.is_active:
            raise Problem(401, "Session expired")

        await session.execute(
            update(AuthSession)
            .where(AuthSession.id == auth_session.id)
            .values(last_used_at=func.now())
        )

    return Principal(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        name=user.name,
        role=user.role,
    )


SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[Principal, Depends(get_principal)]


async def require_editor(principal: PrincipalDep) -> Principal:
    """Admins and coordinators may change the roster; viewers may only read it."""
    if principal.role not in ("admin", "coordinator"):
        raise Problem(403, "Your role cannot change the roster")
    return principal


async def require_admin(principal: PrincipalDep) -> Principal:
    if not principal.is_admin:
        raise Problem(403, "Only an administrator can do that")
    return principal


EditorDep = Annotated[Principal, Depends(require_editor)]
AdminDep = Annotated[Principal, Depends(require_admin)]
