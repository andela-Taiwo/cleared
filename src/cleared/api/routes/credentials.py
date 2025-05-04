"""Credential endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from cleared.api.deps import EditorDep, PrincipalDep, SessionDep
from cleared.api.errors import Problem
from cleared.db.tenant import tenant_scope
from cleared.schemas.credentials import (
    EmployeeCredentialCreate,
    EmployeeCredentialOut,
    EmployeeCredentialUpdate,
)
from cleared.services import audit
from cleared.services import credentials as credentials_service
from cleared.services.credentials import CredentialFilters

router = APIRouter(tags=["credentials"])


@router.get("/credentials", summary="The credential register")
async def list_credentials(
    principal: PrincipalDep,
    session: SessionDep,
    employee_id: uuid.UUID | None = None,
    credential_type_id: uuid.UUID | None = None,
    expires_before: date | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[EmployeeCredentialOut]:
    filters = CredentialFilters(
        employee_id=employee_id,
        credential_type_id=credential_type_id,
        expires_before=expires_before,
        limit=limit,
    )

    async with tenant_scope(session, principal.organization_id):
        rows = await credentials_service.list_credentials(session, filters)
        return [EmployeeCredentialOut.model_validate(row) for row in rows]


@router.get("/employees/{employee_id}/credentials", summary="One person's credentials")
async def list_employee_credentials(
    employee_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> list[EmployeeCredentialOut]:
    async with tenant_scope(session, principal.organization_id):
        if not await credentials_service.employee_exists(session, employee_id):
            raise Problem(404, "Employee not found")
        rows = await credentials_service.list_credentials(
            session, CredentialFilters(employee_id=employee_id)
        )
        return [EmployeeCredentialOut.model_validate(row) for row in rows]


@router.post(
    "/employees/{employee_id}/credentials",
    status_code=201,
    summary="Record a credential",
)
async def create_credential(
    employee_id: uuid.UUID,
    payload: EmployeeCredentialCreate,
    principal: EditorDep,
    session: SessionDep,
) -> EmployeeCredentialOut:
    async with tenant_scope(session, principal.organization_id):
        if not await credentials_service.employee_exists(session, employee_id):
            raise Problem(404, "Employee not found")

        credential = await credentials_service.create_credential(
            session, principal.organization_id, employee_id, payload
        )
        credential = await credentials_service.get_credential(session, credential.id)
        assert credential is not None
        audit.record_for(
            session,
            principal,
            action="credential.recorded",
            entity="employee_credential",
            entity_id=credential.id,
            data={
                "employee_id": str(employee_id),
                "type": credential.credential_type.code,
                "expires_on": credential.expires_on.isoformat() if credential.expires_on else None,
            },
        )
        return EmployeeCredentialOut.model_validate(credential)


@router.patch("/credentials/{credential_id}", summary="Change a credential")
async def update_credential(
    credential_id: uuid.UUID,
    payload: EmployeeCredentialUpdate,
    principal: EditorDep,
    session: SessionDep,
) -> EmployeeCredentialOut:
    async with tenant_scope(session, principal.organization_id):
        credential = await credentials_service.get_credential(session, credential_id)
        if credential is None:
            raise Problem(404, "Credential not found")

        try:
            await credentials_service.update_credential(session, credential, payload)
        except ValueError as exc:
            raise Problem(422, str(exc)) from None

        return EmployeeCredentialOut.model_validate(credential)


@router.post("/credentials/{credential_id}/verify", summary="Mark a credential checked")
async def verify_credential(
    credential_id: uuid.UUID, principal: EditorDep, session: SessionDep
) -> EmployeeCredentialOut:
    async with tenant_scope(session, principal.organization_id):
        credential = await credentials_service.get_credential(session, credential_id)
        if credential is None:
            raise Problem(404, "Credential not found")

        await credentials_service.verify_credential(session, credential, principal.user_id)
        await session.flush()
        audit.record_for(
            session,
            principal,
            action="credential.verified",
            entity="employee_credential",
            entity_id=credential_id,
        )
        credential = await credentials_service.get_credential(session, credential_id)
        assert credential is not None
        return EmployeeCredentialOut.model_validate(credential)


@router.delete("/credentials/{credential_id}", status_code=204, summary="Delete a credential")
async def delete_credential(
    credential_id: uuid.UUID, principal: EditorDep, session: SessionDep
) -> None:
    async with tenant_scope(session, principal.organization_id):
        credential = await credentials_service.get_credential(session, credential_id)
        if credential is None:
            raise Problem(404, "Credential not found")
        audit.record_for(
            session,
            principal,
            action="credential.deleted",
            entity="employee_credential",
            entity_id=credential_id,
        )
        await credentials_service.delete_credential(session, credential)
