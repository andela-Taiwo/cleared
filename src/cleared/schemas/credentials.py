from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CredentialCategory = Literal["license", "certification", "clearance", "health", "training"]


class CredentialTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    category: CredentialCategory
    issuing_authority: str | None
    validity_months: int | None
    requires_document: bool


class CredentialTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=30, pattern=r"^[A-Z0-9][A-Z0-9-]*$")
    category: CredentialCategory
    issuing_authority: str | None = Field(default=None, max_length=160)
    validity_months: int | None = Field(default=None, ge=1, le=240)
    requires_document: bool = True


class CredentialTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    issuing_authority: str | None = Field(default=None, max_length=160)
    validity_months: int | None = Field(default=None, ge=1, le=240)
    requires_document: bool | None = None


class EmployeeCredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    credential_type: CredentialTypeOut
    identifier: str | None
    issued_on: date | None
    expires_on: date | None
    verified_at: datetime | None
    notes: str | None


class EmployeeCredentialCreate(BaseModel):
    credential_type_id: uuid.UUID
    identifier: str | None = Field(default=None, max_length=80)
    issued_on: date | None = None
    expires_on: date | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def check_dates(self) -> EmployeeCredentialCreate:
        if self.issued_on and self.expires_on and self.expires_on < self.issued_on:
            raise ValueError("expires_on cannot be before issued_on")
        return self


class EmployeeCredentialUpdate(BaseModel):
    identifier: str | None = Field(default=None, max_length=80)
    issued_on: date | None = None
    expires_on: date | None = None
    notes: str | None = Field(default=None, max_length=1000)
