"""sessions and the login lookup

Revision ID: 0003
Revises: 0002
Create Date: 2024-12-08 20:44:57+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Sessions are deliberately global: a session is how the application learns which tenant a
    # request belongs to, so it cannot itself be tenant-scoped. The token is unguessable and
    # only its hash is stored.
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=400), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_sessions_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"])
    op.create_index(op.f("ix_sessions_organization_id"), "sessions", ["organization_id"])
    op.create_index(op.f("ix_sessions_expires_at"), "sessions", ["expires_at"])

    # The only cross-tenant read path in the system. Login has to find a user before a tenant
    # is known, and `users` is protected by row-level security. The function is narrow — one
    # exact email, one row — and security definer so that it runs with the owner's rights.
    op.execute(
        """
        create function cleared_auth_lookup(p_email text)
        returns table (
            user_id uuid,
            organization_id uuid,
            password_hash text,
            is_active boolean,
            role text
        )
        language sql
        security definer
        set search_path = public, pg_temp
        as $$
            select u.id, u.organization_id, u.password_hash, u.is_active, u.role
            from users u
            where lower(u.email) = lower(p_email)
            limit 1
        $$
        """
    )
    op.execute("revoke all on function cleared_auth_lookup(text) from public")
    op.execute("grant execute on function cleared_auth_lookup(text) to cleared_app")


def downgrade() -> None:
    op.execute("drop function cleared_auth_lookup(text)")
    op.drop_table("sessions")
