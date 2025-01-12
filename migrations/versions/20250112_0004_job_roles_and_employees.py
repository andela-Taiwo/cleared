"""job roles and employees

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-12 20:18:02+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_PREDICATE = "nullif(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "job_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_job_roles_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_roles")),
        sa.UniqueConstraint(
            "organization_id", "code", name=op.f("uq_job_roles_organization_id_code")
        ),
    )
    op.create_index(op.f("ix_job_roles_organization_id"), "job_roles", ["organization_id"])

    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_no", sa.String(length=40), nullable=True),
        sa.Column("first_name", sa.String(length=80), nullable=False),
        sa.Column("last_name", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("job_role_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("hired_on", sa.Date(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), server_default=sa.text("'active'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('active', 'inactive', 'onboarding')",
            name=op.f("ck_employees_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["job_role_id"],
            ["job_roles.id"],
            name=op.f("fk_employees_job_role_id_job_roles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_employees_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employees")),
        sa.UniqueConstraint(
            "organization_id", "employee_no", name=op.f("uq_employees_organization_id_employee_no")
        ),
    )
    op.create_index(op.f("ix_employees_organization_id"), "employees", ["organization_id"])
    op.create_index(
        "ix_employees_organization_id_last_name", "employees", ["organization_id", "last_name"]
    )
    op.create_index(
        "ix_employees_organization_id_status", "employees", ["organization_id", "status"]
    )
    op.create_index(op.f("ix_employees_job_role_id"), "employees", ["job_role_id"])

    for table in ("job_roles", "employees"):
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"alter table {table} force row level security")
        op.execute(
            f"""
            create policy tenant_isolation on {table}
            using (organization_id = {TENANT_PREDICATE})
            with check (organization_id = {TENANT_PREDICATE})
            """
        )
        op.execute(
            f"""
            create trigger {table}_set_updated_at
            before update on {table}
            for each row execute function set_updated_at()
            """
        )


def downgrade() -> None:
    op.drop_table("employees")
    op.drop_table("job_roles")
