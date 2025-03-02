"""role requirements

Revision ID: 0007
Revises: 0006
Create Date: 2025-03-02 19:22:51+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_PREDICATE = "nullif(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    # Which piece of evidence a job role requires. A row means "required"; the absence of a
    # row means "not required for this role".
    op.create_table(
        "role_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("credential_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["credential_type_id"],
            ["credential_types.id"],
            name=op.f("fk_role_requirements_credential_type_id_credential_types"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_role_id"],
            ["job_roles.id"],
            name=op.f("fk_role_requirements_job_role_id_job_roles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_role_requirements_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_requirements")),
        sa.UniqueConstraint(
            "organization_id",
            "job_role_id",
            "credential_type_id",
            name=op.f("uq_role_requirements_organization_id_job_role_id_credential_type_id"),
        ),
    )
    op.create_index(
        op.f("ix_role_requirements_organization_id"), "role_requirements", ["organization_id"]
    )
    op.create_index(op.f("ix_role_requirements_job_role_id"), "role_requirements", ["job_role_id"])

    op.execute("alter table role_requirements enable row level security")
    op.execute("alter table role_requirements force row level security")
    op.execute(
        f"""
        create policy tenant_isolation on role_requirements
        using (organization_id = {TENANT_PREDICATE})
        with check (organization_id = {TENANT_PREDICATE})
        """
    )


def downgrade() -> None:
    op.drop_table("role_requirements")
