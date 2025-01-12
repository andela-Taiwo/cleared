from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

EmployeeStatus = Literal["active", "inactive", "onboarding"]


class JobRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str


class JobRoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    code: str = Field(min_length=1, max_length=20, pattern=r"^[A-Z0-9][A-Z0-9-]*$")


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_no: str | None
    first_name: str
    last_name: str
    email: EmailStr | None
    phone: str | None
    location: str | None
    hired_on: date | None
    status: EmployeeStatus
    job_role: JobRoleOut | None
    created_at: datetime
    updated_at: datetime


class EmployeeCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    employee_no: str | None = Field(default=None, max_length=40)
    job_role_id: uuid.UUID | None = None
    location: str | None = Field(default=None, max_length=120)
    hired_on: date | None = None
    status: EmployeeStatus = "active"


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    employee_no: str | None = Field(default=None, max_length=40)
    job_role_id: uuid.UUID | None = None
    location: str | None = Field(default=None, max_length=120)
    hired_on: date | None = None
    status: EmployeeStatus | None = None


class EmployeePage(BaseModel):
    items: list[EmployeeOut]
    next_cursor: str | None
    total: int
