"""Job roles: what kinds of worker the agency deploys."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select
from uuid6 import uuid7

from cleared.api.deps import EditorDep, PrincipalDep, SessionDep
from cleared.api.errors import Problem
from cleared.db.tenant import tenant_scope
from cleared.domain.models import JobRole
from cleared.schemas.employees import JobRoleCreate, JobRoleOut

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", summary="List job roles")
async def list_roles(principal: PrincipalDep, session: SessionDep) -> list[JobRoleOut]:
    async with tenant_scope(session, principal.organization_id):
        roles = (await session.scalars(select(JobRole).order_by(JobRole.name))).all()
        return [JobRoleOut.model_validate(role) for role in roles]


@router.post("", status_code=201, summary="Add a job role")
async def create_role(
    payload: JobRoleCreate, principal: EditorDep, session: SessionDep
) -> JobRoleOut:
    async with tenant_scope(session, principal.organization_id):
        existing = await session.scalar(select(JobRole).where(JobRole.code == payload.code))
        if existing is not None:
            raise Problem(409, f"A role with code {payload.code} already exists")

        role = JobRole(
            id=uuid7(),
            organization_id=principal.organization_id,
            name=payload.name.strip(),
            code=payload.code,
        )
        session.add(role)
        await session.flush()
        return JobRoleOut.model_validate(role)
