"""Which credentials each job role must hold."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import delete, select
from uuid6 import uuid7

from cleared.api.deps import AdminDep, PrincipalDep, SessionDep
from cleared.api.errors import Problem
from cleared.db.tenant import tenant_scope
from cleared.domain.models import CredentialType, JobRole, RoleRequirement
from cleared.schemas.requirements import RequirementMatrix, RequirementOut, RequirementSet
from cleared.services import audit

router = APIRouter(prefix="/requirements", tags=["requirements"])


@router.get("", summary="The role and credential matrix")
async def read_matrix(principal: PrincipalDep, session: SessionDep) -> RequirementMatrix:
    async with tenant_scope(session, principal.organization_id):
        rows = (await session.scalars(select(RoleRequirement))).all()
        return RequirementMatrix(
            requirements=[
                RequirementOut(
                    job_role_id=row.job_role_id, credential_type_id=row.credential_type_id
                )
                for row in rows
            ]
        )


@router.put("/{job_role_id}", summary="Replace a role's requirement set")
async def replace_role_requirements(
    job_role_id: uuid.UUID,
    payload: RequirementSet,
    principal: AdminDep,
    session: SessionDep,
) -> RequirementMatrix:
    async with tenant_scope(session, principal.organization_id):
        role = await session.scalar(select(JobRole).where(JobRole.id == job_role_id))
        if role is None:
            raise Problem(404, "Job role not found")

        wanted = set(payload.credential_type_ids)
        if wanted:
            known = set(
                (
                    await session.scalars(
                        select(CredentialType.id).where(CredentialType.id.in_(wanted))
                    )
                ).all()
            )
            unknown = wanted - known
            if unknown:
                raise Problem(422, f"Unknown credential type: {sorted(map(str, unknown))[0]}")

        await session.execute(
            delete(RoleRequirement).where(RoleRequirement.job_role_id == job_role_id)
        )
        for credential_type_id in sorted(wanted):
            session.add(
                RoleRequirement(
                    id=uuid7(),
                    organization_id=principal.organization_id,
                    job_role_id=job_role_id,
                    credential_type_id=credential_type_id,
                )
            )
        await session.flush()
        audit.record_for(
            session,
            principal,
            action="requirements.replaced",
            entity="job_role",
            entity_id=job_role_id,
            data={"credential_type_ids": sorted(str(value) for value in wanted)},
        )

        rows = (
            await session.scalars(
                select(RoleRequirement).where(RoleRequirement.job_role_id == job_role_id)
            )
        ).all()
        return RequirementMatrix(
            requirements=[
                RequirementOut(
                    job_role_id=row.job_role_id, credential_type_id=row.credential_type_id
                )
                for row in rows
            ]
        )
