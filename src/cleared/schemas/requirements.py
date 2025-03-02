from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class RequirementOut(BaseModel):
    job_role_id: uuid.UUID
    credential_type_id: uuid.UUID


class RequirementSet(BaseModel):
    credential_type_ids: list[uuid.UUID] = Field(default_factory=list)


class RequirementMatrix(BaseModel):
    requirements: list[RequirementOut]
