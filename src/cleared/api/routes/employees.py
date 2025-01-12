"""Roster endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlalchemy.exc import IntegrityError

from cleared.api.deps import EditorDep, PrincipalDep, SessionDep
from cleared.api.errors import Problem
from cleared.db.tenant import tenant_scope
from cleared.domain.models import Employee
from cleared.schemas.employees import EmployeeCreate, EmployeeOut, EmployeePage, EmployeeUpdate
from cleared.services import employees as employees_service
from cleared.services.employees import EmployeeFilters

router = APIRouter(prefix="/employees", tags=["employees"])


async def _reload(session: SessionDep, employee_id: uuid.UUID) -> Employee:
    employee = await employees_service.get_employee(session, employee_id)
    if employee is None:
        raise Problem(404, "Employee not found")
    return employee


@router.get("", summary="List the roster")
async def list_employees(
    principal: PrincipalDep,
    session: SessionDep,
    search: Annotated[str | None, Query(max_length=120)] = None,
    role_id: uuid.UUID | None = None,
    status: Literal["active", "inactive", "onboarding"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
) -> EmployeePage:
    filters = EmployeeFilters(
        search=search, job_role_id=role_id, status=status, limit=limit, cursor=cursor
    )

    async with tenant_scope(session, principal.organization_id):
        try:
            page, next_cursor, total = await employees_service.list_employees(session, filters)
        except ValueError:
            raise Problem(400, "Invalid cursor") from None

    return EmployeePage(
        items=[EmployeeOut.model_validate(employee) for employee in page],
        next_cursor=next_cursor,
        total=total,
    )


@router.post("", status_code=201, summary="Add someone to the roster")
async def create_employee(
    payload: EmployeeCreate, principal: EditorDep, session: SessionDep
) -> EmployeeOut:
    async with tenant_scope(session, principal.organization_id):
        try:
            employee = await employees_service.create_employee(
                session, principal.organization_id, payload
            )
            await session.flush()
        except ValueError:
            raise Problem(422, "Unknown job role") from None
        except IntegrityError:
            raise Problem(409, "That employee number is already in use") from None
        employee = await _reload(session, employee.id)
        return EmployeeOut.model_validate(employee)


@router.get("/{employee_id}", summary="One employee")
async def read_employee(
    employee_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> EmployeeOut:
    async with tenant_scope(session, principal.organization_id):
        employee = await _reload(session, employee_id)
        return EmployeeOut.model_validate(employee)


@router.patch("/{employee_id}", summary="Change an employee")
async def update_employee(
    employee_id: uuid.UUID, payload: EmployeeUpdate, principal: EditorDep, session: SessionDep
) -> EmployeeOut:
    async with tenant_scope(session, principal.organization_id):
        employee = await _reload(session, employee_id)
        try:
            await employees_service.update_employee(session, employee, payload)
        except ValueError:
            raise Problem(422, "Unknown job role") from None
        await session.flush()
        employee = await _reload(session, employee_id)
        return EmployeeOut.model_validate(employee)
