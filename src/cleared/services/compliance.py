"""Compliance for a whole agency.

Loads the three things the rules need — requirements, credentials, employees — in three
queries, then computes in Python. At agency scale (hundreds of people, a few thousand
credentials) this is faster than a per-employee query and far easier to reason about.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cleared.domain.compliance import (
    DEFAULT_HORIZON_DAYS,
    CredentialState,
    CredentialView,
    EmployeeCompliance,
    ReadinessState,
    Requirement,
    evaluate_employee,
)
from cleared.domain.models import (
    CredentialType,
    Employee,
    EmployeeCredential,
    Organization,
    RoleRequirement,
)
from cleared.domain.timezones import today_in


@dataclass(frozen=True)
class Rules:
    """Everything the engine needs that is not employee-specific."""

    requirements_by_role: dict[uuid.UUID, list[Requirement]]
    credentials_by_employee: dict[uuid.UUID, list[CredentialView]]
    today: date
    horizon_days: int = DEFAULT_HORIZON_DAYS

    def for_employee(self, employee: Employee) -> EmployeeCompliance:
        requirements = (
            self.requirements_by_role.get(employee.job_role_id, []) if employee.job_role_id else []
        )
        return evaluate_employee(
            requirements,
            self.credentials_by_employee.get(employee.id, []),
            today=self.today,
            horizon_days=self.horizon_days,
        )


async def agency_today(session: AsyncSession, *, now: datetime | None = None) -> date:
    """The date it is where the agency is, not where the server is."""
    timezone = await session.scalar(select(Organization.timezone))
    return today_in(timezone or "UTC", now=now)


async def load_rules(
    session: AsyncSession, *, today: date | None = None, now: datetime | None = None
) -> Rules:
    requirement_rows = (
        await session.execute(
            select(
                RoleRequirement.job_role_id,
                CredentialType.id,
                CredentialType.name,
            ).join(CredentialType, CredentialType.id == RoleRequirement.credential_type_id)
        )
    ).all()

    requirements_by_role: dict[uuid.UUID, list[Requirement]] = {}
    for job_role_id, credential_type_id, name in requirement_rows:
        requirements_by_role.setdefault(job_role_id, []).append(
            Requirement(credential_type_id=credential_type_id, credential_type_name=name)
        )

    credential_rows = (
        await session.execute(
            select(
                EmployeeCredential.employee_id,
                EmployeeCredential.credential_type_id,
                EmployeeCredential.expires_on,
                EmployeeCredential.verified_at,
            )
        )
    ).all()

    credentials_by_employee: dict[uuid.UUID, list[CredentialView]] = {}
    for employee_id, credential_type_id, expires_on, verified_at in credential_rows:
        credentials_by_employee.setdefault(employee_id, []).append(
            CredentialView(
                credential_type_id=credential_type_id,
                expires_on=expires_on,
                verified=verified_at is not None,
            )
        )

    return Rules(
        requirements_by_role=requirements_by_role,
        credentials_by_employee=credentials_by_employee,
        today=today or await agency_today(session, now=now),
    )


@dataclass(frozen=True)
class UpcomingItem:
    employee_id: uuid.UUID
    employee_name: str
    credential_type_name: str
    expires_on: date
    days_left: int
    state: str


@dataclass(frozen=True)
class RoleBreakdown:
    job_role_id: uuid.UUID | None
    role_name: str
    total: int
    compliant: int
    at_risk: int
    non_compliant: int


@dataclass(frozen=True)
class Overview:
    total: int
    states: dict[str, int]
    expiring: dict[str, int]
    upcoming: list[UpcomingItem]
    roles: list[RoleBreakdown]


async def build_overview(session: AsyncSession, *, today: date | None = None) -> Overview:
    rules = await load_rules(session, today=today)
    employees = (await session.scalars(select(Employee).where(Employee.status != "inactive"))).all()

    states = {state.value: 0 for state in ReadinessState}
    buckets = {"within_7": 0, "within_30": 0, "within_60": 0}
    upcoming: list[UpcomingItem] = []
    by_role: dict[uuid.UUID | None, RoleBreakdown] = {}

    for employee in employees:
        compliance = rules.for_employee(employee)
        states[compliance.state.value] += 1

        name = f"{employee.first_name} {employee.last_name}"
        for item in compliance.items:
            if item.days_left is None or item.state is CredentialState.missing:
                continue
            if item.days_left < 0:
                continue
            if item.days_left <= 7:
                buckets["within_7"] += 1
            if item.days_left <= 30:
                buckets["within_30"] += 1
            if item.days_left <= 60:
                buckets["within_60"] += 1
            if item.days_left <= 60 and item.expires_on is not None:
                upcoming.append(
                    UpcomingItem(
                        employee_id=employee.id,
                        employee_name=name,
                        credential_type_name=item.credential_type_name,
                        expires_on=item.expires_on,
                        days_left=item.days_left,
                        state=item.state.value,
                    )
                )

        role_key = employee.job_role_id
        existing = by_role.get(role_key)
        role_name = employee.job_role.name if employee.job_role else "Unassigned"
        breakdown = existing or RoleBreakdown(
            job_role_id=role_key,
            role_name=role_name,
            total=0,
            compliant=0,
            at_risk=0,
            non_compliant=0,
        )
        breakdown = RoleBreakdown(
            job_role_id=breakdown.job_role_id,
            role_name=breakdown.role_name,
            total=breakdown.total + 1,
            compliant=breakdown.compliant
            + (1 if compliance.state is ReadinessState.compliant else 0),
            at_risk=breakdown.at_risk + (1 if compliance.state is ReadinessState.at_risk else 0),
            non_compliant=breakdown.non_compliant
            + (1 if compliance.state is ReadinessState.non_compliant else 0),
        )
        by_role[role_key] = breakdown

    upcoming.sort(key=lambda item: item.days_left)

    return Overview(
        total=len(employees),
        states=states,
        expiring=buckets,
        upcoming=upcoming[:12],
        roles=sorted(by_role.values(), key=lambda row: row.role_name),
    )
