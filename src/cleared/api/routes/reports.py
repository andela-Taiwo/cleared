"""Reports an agency can hand to somebody else."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date

from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import select

from cleared.api.deps import PrincipalDep, SessionDep
from cleared.db.tenant import tenant_scope
from cleared.domain.models import Employee, Organization
from cleared.services import compliance as compliance_service

router = APIRouter(prefix="/reports", tags=["reports"])


@dataclass(frozen=True)
class ReportRow:
    employee_no: str
    last_name: str
    first_name: str
    role: str
    status: str
    state: str
    readiness: int
    expired: int
    expiring: int
    missing: int
    unverified: int


class ComplianceReportOut(BaseModel):
    generated_on: date
    organization_name: str
    total: int
    rows: list[dict[str, str | int]]


async def _rows(session: SessionDep) -> tuple[str, list[ReportRow]]:
    organization = await session.scalar(select(Organization))
    rules = await compliance_service.load_rules(session)
    employees = (
        await session.scalars(select(Employee).order_by(Employee.last_name, Employee.first_name))
    ).all()

    rows: list[ReportRow] = []
    for employee in employees:
        result = rules.for_employee(employee)
        rows.append(
            ReportRow(
                employee_no=employee.employee_no or "",
                last_name=employee.last_name,
                first_name=employee.first_name,
                role=employee.job_role.name if employee.job_role else "",
                status=employee.status,
                state=result.state.value,
                readiness=result.readiness,
                expired=result.count(  # type: ignore[arg-type]
                    compliance_service.CredentialState.expired
                ),
                expiring=result.count(  # type: ignore[arg-type]
                    compliance_service.CredentialState.expiring
                ),
                missing=result.count(  # type: ignore[arg-type]
                    compliance_service.CredentialState.missing
                ),
                unverified=result.count(  # type: ignore[arg-type]
                    compliance_service.CredentialState.unverified
                ),
            )
        )

    return organization.name if organization else "", rows


@router.get("/compliance", summary="The compliance report")
async def compliance_report(principal: PrincipalDep, session: SessionDep) -> ComplianceReportOut:
    async with tenant_scope(session, principal.organization_id):
        name, rows = await _rows(session)

    return ComplianceReportOut(
        generated_on=date.today(),
        organization_name=name,
        total=len(rows),
        rows=[row.__dict__ for row in rows],
    )


@router.get("/compliance.csv", summary="The compliance report as CSV")
async def compliance_report_csv(principal: PrincipalDep, session: SessionDep) -> Response:
    async with tenant_scope(session, principal.organization_id):
        _name, rows = await _rows(session)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "employee_no",
            "last_name",
            "first_name",
            "role",
            "status",
            "compliance",
            "readiness_pct",
            "expired",
            "expiring",
            "missing",
            "unverified",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.employee_no,
                row.last_name,
                row.first_name,
                row.role,
                row.status,
                row.state,
                row.readiness,
                row.expired,
                row.expiring,
                row.missing,
                row.unverified,
            ]
        )

    filename = f"compliance-{date.today().isoformat()}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
