"""credential types

Revision ID: 0005
Revises: 0004
Create Date: 2025-02-09 20:41:19+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_PREDICATE = "nullif(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "credential_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("issuing_authority", sa.String(length=160), nullable=True),
        # How long a fresh copy is good for, where the issuer fixes it (CPR: 24 months).
        sa.Column("validity_months", sa.Integer(), nullable=True),
        sa.Column(
            "requires_document",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
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
            "category in ('license', 'certification', 'clearance', 'health', 'training')",
            name=op.f("ck_credential_types_category_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_credential_types_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_credential_types")),
        sa.UniqueConstraint(
            "organization_id", "code", name=op.f("uq_credential_types_organization_id_code")
        ),
    )
    op.create_index(
        op.f("ix_credential_types_organization_id"), "credential_types", ["organization_id"]
    )

    op.execute("alter table credential_types enable row level security")
    op.execute("alter table credential_types force row level security")
    op.execute(
        f"""
        create policy tenant_isolation on credential_types
        using (organization_id = {TENANT_PREDICATE})
        with check (organization_id = {TENANT_PREDICATE})
        """
    )
    op.execute(
        """
        create trigger credential_types_set_updated_at
        before update on credential_types
        for each row execute function set_updated_at()
        """
    )


def downgrade() -> None:
    op.drop_table("credential_types")
