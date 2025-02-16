"""employee credentials

Revision ID: 0006
Revises: 0005
Create Date: 2025-02-16 19:57:44+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_PREDICATE = "nullif(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "employee_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("credential_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier", sa.String(length=80), nullable=True),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            "expires_on is null or issued_on is null or expires_on >= issued_on",
            name=op.f("ck_employee_credentials_dates_ordered"),
        ),
        sa.ForeignKeyConstraint(
            ["credential_type_id"],
            ["credential_types.id"],
            name=op.f("fk_employee_credentials_credential_type_id_credential_types"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name=op.f("fk_employee_credentials_employee_id_employees"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_employee_credentials_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["verified_by"],
            ["users.id"],
            name=op.f("fk_employee_credentials_verified_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee_credentials")),
    )
    op.create_index(
        op.f("ix_employee_credentials_organization_id"), "employee_credentials", ["organization_id"]
    )
    op.create_index(
        op.f("ix_employee_credentials_employee_id"), "employee_credentials", ["employee_id"]
    )
    op.create_index(
        op.f("ix_employee_credentials_credential_type_id"),
        "employee_credentials",
        ["credential_type_id"],
    )
    # The dashboard asks "what expires between these dates" on every load.
    op.create_index(
        "ix_employee_credentials_organization_id_expires_on",
        "employee_credentials",
        ["organization_id", "expires_on"],
    )

    op.execute("alter table employee_credentials enable row level security")
    op.execute("alter table employee_credentials force row level security")
    op.execute(
        f"""
        create policy tenant_isolation on employee_credentials
        using (organization_id = {TENANT_PREDICATE})
        with check (organization_id = {TENANT_PREDICATE})
        """
    )
    op.execute(
        """
        create trigger employee_credentials_set_updated_at
        before update on employee_credentials
        for each row execute function set_updated_at()
        """
    )


def downgrade() -> None:
    op.drop_table("employee_credentials")
