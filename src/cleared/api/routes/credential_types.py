"""The catalogue of credential types an agency recognises."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select
from uuid6 import uuid7

from cleared.api.deps import AdminDep, PrincipalDep, SessionDep
from cleared.api.errors import Problem
from cleared.db.tenant import tenant_scope
from cleared.domain.models import CredentialType
from cleared.schemas.credentials import (
    CredentialTypeCreate,
    CredentialTypeOut,
    CredentialTypeUpdate,
)

router = APIRouter(prefix="/credential-types", tags=["credential-types"])


@router.get("", summary="List credential types")
async def list_credential_types(
    principal: PrincipalDep, session: SessionDep
) -> list[CredentialTypeOut]:
    async with tenant_scope(session, principal.organization_id):
        rows = (
            await session.scalars(
                select(CredentialType).order_by(CredentialType.category, CredentialType.name)
            )
        ).all()
        return [CredentialTypeOut.model_validate(row) for row in rows]


@router.post("", status_code=201, summary="Add a credential type")
async def create_credential_type(
    payload: CredentialTypeCreate, principal: AdminDep, session: SessionDep
) -> CredentialTypeOut:
    async with tenant_scope(session, principal.organization_id):
        existing = await session.scalar(
            select(CredentialType).where(CredentialType.code == payload.code)
        )
        if existing is not None:
            raise Problem(409, f"A credential type with code {payload.code} already exists")

        credential_type = CredentialType(
            id=uuid7(),
            organization_id=principal.organization_id,
            name=payload.name.strip(),
            code=payload.code,
            category=payload.category,
            issuing_authority=payload.issuing_authority,
            validity_months=payload.validity_months,
            requires_document=payload.requires_document,
        )
        session.add(credential_type)
        await session.flush()
        return CredentialTypeOut.model_validate(credential_type)


@router.patch("/{credential_type_id}", summary="Change a credential type")
async def update_credential_type(
    credential_type_id: uuid.UUID,
    payload: CredentialTypeUpdate,
    principal: AdminDep,
    session: SessionDep,
) -> CredentialTypeOut:
    async with tenant_scope(session, principal.organization_id):
        credential_type = await session.scalar(
            select(CredentialType).where(CredentialType.id == credential_type_id)
        )
        if credential_type is None:
            raise Problem(404, "Credential type not found")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(credential_type, field, value)

        await session.flush()
        return CredentialTypeOut.model_validate(credential_type)
