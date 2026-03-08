"""Roster queries and mutations.

Every function expects the caller to have opened a tenant transaction: the database, not this
module, is what stops one agency reading another's roster.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from uuid6 import uuid7

from cleared.api.pagination import decode_cursor, encode_cursor
from cleared.domain.models import Employee, JobRole
from cleared.schemas.employees import EmployeeCreate, EmployeeUpdate

MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class EmployeeFilters:
    search: str | None = None
    compliance: str | None = None
    job_role_id: uuid.UUID | None = None
    status: str | None = None
    limit: int = 25
    cursor: str | None = None


def _conditions(filters: EmployeeFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []

    if filters.status:
        conditions.append(Employee.status == filters.status)
    if filters.job_role_id:
        conditions.append(Employee.job_role_id == filters.job_role_id)
    if filters.search:
        term = f"%{filters.search.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(Employee.first_name).like(term),
                func.lower(Employee.last_name).like(term),
                func.lower(func.coalesce(Employee.email, "")).like(term),
                func.lower(func.coalesce(Employee.employee_no, "")).like(term),
            )
        )

    return conditions


def _after_cursor(stmt: Select[Any], cursor: str) -> Select[Any]:
    last_name, first_name, raw_id = decode_cursor(cursor, length=3)
    employee_id = uuid.UUID(raw_id)

    # Lexicographic comparison of (last_name, first_name, id), written out because a row
    # comparison needs every column to have a type the driver can infer.
    return stmt.where(
        or_(
            func.lower(Employee.last_name) > last_name,
            (func.lower(Employee.last_name) == last_name)
            & (func.lower(Employee.first_name) > first_name),
            (func.lower(Employee.last_name) == last_name)
            & (func.lower(Employee.first_name) == first_name)
            & (Employee.id > employee_id),
        )
    )


async def list_employees(
    session: AsyncSession,
    filters: EmployeeFilters,
    *,
    matching_ids: list[uuid.UUID] | None = None,
) -> tuple[list[Employee], str | None, int]:
    limit = min(filters.limit, MAX_PAGE_SIZE)

    statement = select(Employee).order_by(
        func.lower(Employee.last_name), func.lower(Employee.first_name), Employee.id
    )
    count_statement = select(func.count()).select_from(Employee)

    conditions = _conditions(filters)
    if matching_ids is not None:
        conditions.append(Employee.id.in_(matching_ids))
    if conditions:
        statement = statement.where(*conditions)
        count_statement = count_statement.where(*conditions)

    if filters.cursor:
        statement = _after_cursor(statement, filters.cursor)

    rows = list((await session.scalars(statement.limit(limit + 1))).all())
    has_more = len(rows) > limit
    page = rows[:limit]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor([last.last_name.lower(), last.first_name.lower(), str(last.id)])

    total = await session.scalar(count_statement)
    return page, next_cursor, int(total or 0)


async def get_employee(session: AsyncSession, employee_id: uuid.UUID) -> Employee | None:
    return await session.scalar(select(Employee).where(Employee.id == employee_id))


async def get_job_role(session: AsyncSession, job_role_id: uuid.UUID) -> JobRole | None:
    return await session.scalar(select(JobRole).where(JobRole.id == job_role_id))


async def create_employee(
    session: AsyncSession, organization_id: uuid.UUID, payload: EmployeeCreate
) -> Employee:
    if payload.job_role_id is not None and await get_job_role(session, payload.job_role_id) is None:
        raise ValueError("unknown job role")

    employee = Employee(
        id=uuid7(),
        organization_id=organization_id,
        employee_no=payload.employee_no,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=str(payload.email).lower() if payload.email else None,
        phone=payload.phone,
        job_role_id=payload.job_role_id,
        location=payload.location,
        hired_on=payload.hired_on,
        status=payload.status,
    )
    session.add(employee)
    await session.flush()
    return employee


async def update_employee(
    session: AsyncSession, employee: Employee, payload: EmployeeUpdate
) -> Employee:
    changes = payload.model_dump(exclude_unset=True)

    job_role_id = changes.get("job_role_id")
    if job_role_id is not None and await get_job_role(session, job_role_id) is None:
        raise ValueError("unknown job role")

    if "email" in changes and changes["email"] is not None:
        changes["email"] = str(changes["email"]).lower()

    for field, value in changes.items():
        setattr(employee, field, value)

    await session.flush()
    return employee
