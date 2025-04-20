from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReminderRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    days_before: int
    channel: str
    audience: Literal["employee", "coordinator", "both"]
    is_active: bool


class ReminderRuleCreate(BaseModel):
    days_before: int = Field(ge=0, le=365)
    audience: Literal["employee", "coordinator", "both"]
    channel: Literal["email"] = "email"


class ReminderRuleUpdate(BaseModel):
    days_before: int | None = Field(default=None, ge=0, le=365)
    audience: Literal["employee", "coordinator", "both"] | None = None
    is_active: bool | None = None


class ReminderEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    due_on: date
    channel: str
    recipient: str
    subject: str
    body: str
    status: str
    sent_at: datetime | None


class ReminderRunOut(BaseModel):
    generated: int
    sent: int
