"""Authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from cleared.api.deps import PrincipalDep, SessionDep
from cleared.api.errors import Problem
from cleared.config import get_settings
from cleared.db.tenant import set_tenant
from cleared.domain.models import Organization
from cleared.schemas.auth import LoginRequest, MeResponse
from cleared.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()

SESSION_COOKIE_PATH = "/"


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        path=SESSION_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=settings.is_prod,
    )


@router.post("/login", summary="Sign in")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
) -> dict[str, str]:
    try:
        account = await auth_service.authenticate(session, payload.email, payload.password)
    except auth_service.InvalidCredentials:
        raise Problem(401, "Email or password is incorrect") from None
    except auth_service.AccountDisabled:
        raise Problem(403, "This account has been disabled") from None

    token = await auth_service.start_session(
        session,
        account=account,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    _set_session_cookie(response, token)
    return {"status": "ok"}


@router.post("/logout", summary="Sign out")
async def logout(
    request: Request,
    response: Response,
    session: SessionDep,
) -> dict[str, str]:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await auth_service.end_session(session, token)
    response.delete_cookie(settings.session_cookie_name, path=SESSION_COOKIE_PATH)
    return {"status": "ok"}


@router.get("/me", summary="The signed-in user")
async def me(principal: PrincipalDep, session: SessionDep) -> MeResponse:
    async with session.begin():
        await set_tenant(session, principal.organization_id)
        organization = await session.scalar(
            select(Organization).where(Organization.id == principal.organization_id)
        )

    return MeResponse(
        id=principal.user_id,
        name=principal.name,
        email=principal.email,
        role=principal.role,
        organization_id=principal.organization_id,
        organization_name=organization.name if organization else "",
    )
