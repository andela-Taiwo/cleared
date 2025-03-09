from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from cleared.domain.compliance import CredentialState, ReadinessState


class ComplianceSummary(BaseModel):
    state: ReadinessState
    readiness: int
    expired: int
    expiring: int
    missing: int
    unverified: int


class RequirementStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    credential_type_id: uuid.UUID
    credential_type_name: str
    state: CredentialState
    expires_on: date | None
    days_left: int | None


class EmployeeComplianceOut(BaseModel):
    state: ReadinessState
    readiness: int
    items: list[RequirementStatusOut]


class UpcomingOut(BaseModel):
    employee_id: uuid.UUID
    employee_name: str
    credential_type_name: str
    expires_on: date
    days_left: int
    state: CredentialState


class RoleBreakdownOut(BaseModel):
    job_role_id: uuid.UUID | None
    role_name: str
    total: int
    compliant: int
    at_risk: int
    non_compliant: int


class OverviewOut(BaseModel):
    total: int
    states: dict[str, int]
    expiring: dict[str, int]
    upcoming: list[UpcomingOut]
    roles: list[RoleBreakdownOut]
