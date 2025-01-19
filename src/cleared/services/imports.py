"""Importing a roster from a spreadsheet."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from cleared.domain.models import Employee, JobRole
from cleared.domain.roster_csv import RosterRow, RowProblem


@dataclass
class ImportReport:
    created: int = 0
    updated: int = 0
    failed: int = 0
    errors: list[RowProblem] = field(default_factory=list)


async def import_roster(
    session: AsyncSession, organization_id: uuid.UUID, rows: list[RosterRow]
) -> ImportReport:
    report = ImportReport()

    roles = (await session.scalars(select(JobRole))).all()
    roles_by_code = {role.code.upper(): role for role in roles}

    existing: dict[str, Employee] = {}
    numbers = [row.employee_no for row in rows if row.employee_no]
    if numbers:
        found = (
            await session.scalars(select(Employee).where(Employee.employee_no.in_(numbers)))
        ).all()
        existing = {employee.employee_no or "": employee for employee in found}

    for row in rows:
        if row.role_code is not None and row.role_code not in roles_by_code:
            report.failed += 1
            report.errors.append(
                RowProblem(line=row.line, message=f"Unknown role code: {row.role_code}")
            )
            continue

        role = roles_by_code.get(row.role_code or "")

        if row.employee_no and row.employee_no in existing:
            employee = existing[row.employee_no]
            employee.first_name = row.first_name
            employee.last_name = row.last_name
            employee.email = row.email
            employee.phone = row.phone
            employee.location = row.location
            employee.hired_on = row.hired_on
            employee.status = row.status
            if role is not None:
                employee.job_role_id = role.id
            report.updated += 1
            continue

        employee = Employee(
            id=uuid7(),
            organization_id=organization_id,
            employee_no=row.employee_no,
            first_name=row.first_name,
            last_name=row.last_name,
            email=row.email,
            phone=row.phone,
            job_role_id=role.id if role else None,
            location=row.location,
            hired_on=row.hired_on,
            status=row.status,
        )
        session.add(employee)
        report.created += 1
        if row.employee_no:
            existing[row.employee_no] = employee

    await session.flush()
    return report


async def count_employees(session: AsyncSession) -> int:
    total = await session.scalar(select(func.count()).select_from(Employee))
    return int(total or 0)
