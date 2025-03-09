"""Compliance endpoints: one overview for the dashboard, one detail per person."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from cleared.api.deps import PrincipalDep, SessionDep
from cleared.api.errors import Problem
from cleared.db.tenant import tenant_scope
from cleared.domain.compliance import CredentialState
from cleared.domain.models import Employee
from cleared.schemas.compliance import (
    EmployeeComplianceOut,
    OverviewOut,
    RequirementStatusOut,
    RoleBreakdownOut,
    UpcomingOut,
)
from cleared.services import compliance as compliance_service

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/overview", summary="How the agency is doing today")
async def read_overview(principal: PrincipalDep, session: SessionDep) -> OverviewOut:
    async with tenant_scope(session, principal.organization_id):
        overview = await compliance_service.build_overview(session)

    return OverviewOut(
        total=overview.total,
        states=overview.states,
        expiring=overview.expiring,
        upcoming=[
            UpcomingOut(
                employee_id=item.employee_id,
                employee_name=item.employee_name,
                credential_type_name=item.credential_type_name,
                expires_on=item.expires_on,
                days_left=item.days_left,
                state=CredentialState(item.state),
            )
            for item in overview.upcoming
        ],
        roles=[
            RoleBreakdownOut(
                job_role_id=role.job_role_id,
                role_name=role.role_name,
                total=role.total,
                compliant=role.compliant,
                at_risk=role.at_risk,
                non_compliant=role.non_compliant,
            )
            for role in overview.roles
        ],
    )


@router.get("/employees/{employee_id}", summary="One person's requirements")
async def read_employee_compliance(
    employee_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> EmployeeComplianceOut:
    async with tenant_scope(session, principal.organization_id):
        employee = await session.scalar(select(Employee).where(Employee.id == employee_id))
        if employee is None:
            raise Problem(404, "Employee not found")

        rules = await compliance_service.load_rules(session)
        compliance = rules.for_employee(employee)

    return EmployeeComplianceOut(
        state=compliance.state,
        readiness=compliance.readiness,
        items=[RequirementStatusOut.model_validate(item) for item in compliance.items],
    )
