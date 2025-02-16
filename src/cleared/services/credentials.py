"""Credential records: what each person holds, and when it runs out."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from cleared.domain.models import Employee, EmployeeCredential
from cleared.schemas.credentials import EmployeeCredentialCreate, EmployeeCredentialUpdate


@dataclass(frozen=True)
class CredentialFilters:
    employee_id: uuid.UUID | None = None
    credential_type_id: uuid.UUID | None = None
    expires_before: date | None = None
    limit: int = 100


async def list_credentials(
    session: AsyncSession, filters: CredentialFilters
) -> list[EmployeeCredential]:
    statement = select(EmployeeCredential)

    if filters.employee_id:
        statement = statement.where(EmployeeCredential.employee_id == filters.employee_id)
    if filters.credential_type_id:
        statement = statement.where(
            EmployeeCredential.credential_type_id == filters.credential_type_id
        )
    if filters.expires_before:
        statement = statement.where(
            EmployeeCredential.expires_on.is_not(None),
            EmployeeCredential.expires_on <= filters.expires_before,
        )

    statement = statement.order_by(
        EmployeeCredential.expires_on.asc().nulls_last(), EmployeeCredential.created_at.desc()
    )
    return list((await session.scalars(statement.limit(filters.limit))).all())


async def get_credential(
    session: AsyncSession, credential_id: uuid.UUID
) -> EmployeeCredential | None:
    return await session.scalar(
        select(EmployeeCredential).where(EmployeeCredential.id == credential_id)
    )


async def employee_exists(session: AsyncSession, employee_id: uuid.UUID) -> bool:
    count = await session.scalar(
        select(func.count()).select_from(Employee).where(Employee.id == employee_id)
    )
    return bool(count)


async def create_credential(
    session: AsyncSession,
    organization_id: uuid.UUID,
    employee_id: uuid.UUID,
    payload: EmployeeCredentialCreate,
) -> EmployeeCredential:
    credential = EmployeeCredential(
        id=uuid7(),
        organization_id=organization_id,
        employee_id=employee_id,
        credential_type_id=payload.credential_type_id,
        identifier=payload.identifier,
        issued_on=payload.issued_on,
        expires_on=payload.expires_on,
        notes=payload.notes,
    )
    session.add(credential)
    await session.flush()
    return credential


async def update_credential(
    session: AsyncSession, credential: EmployeeCredential, payload: EmployeeCredentialUpdate
) -> EmployeeCredential:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(credential, field, value)

    if (
        credential.issued_on is not None
        and credential.expires_on is not None
        and credential.expires_on < credential.issued_on
    ):
        raise ValueError("expires_on cannot be before issued_on")

    await session.flush()
    return credential


async def verify_credential(
    session: AsyncSession, credential: EmployeeCredential, verified_by: uuid.UUID
) -> EmployeeCredential:
    credential.verified_at = func.now()
    credential.verified_by = verified_by
    await session.flush()
    return credential


async def delete_credential(session: AsyncSession, credential: EmployeeCredential) -> None:
    await session.delete(credential)
    await session.flush()
