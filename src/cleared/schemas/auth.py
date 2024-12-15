from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class MeResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    role: str
    organization_id: uuid.UUID
    organization_name: str
