"""audit events

Revision ID: 0009
Revises: 0008
Create Date: 2025-05-04 19:16:38+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_PREDICATE = "nullif(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_name", sa.String(length=200), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("entity", sa.String(length=40), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_audit_events_actor_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_audit_events_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(op.f("ix_audit_events_organization_id"), "audit_events", ["organization_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    op.execute("alter table audit_events enable row level security")
    op.execute("alter table audit_events force row level security")
    op.execute(
        f"""
        create policy tenant_isolation on audit_events
        using (organization_id = {TENANT_PREDICATE})
        with check (organization_id = {TENANT_PREDICATE})
        """
    )

    # Append-only, enforced in the database so an ORM bug cannot rewrite history.
    op.execute(
        """
        create function audit_events_are_append_only() returns trigger
        language plpgsql as $$
        begin
            raise exception 'audit_events is append-only';
        end;
        $$
        """
    )
    for event in ("update", "delete"):
        op.execute(
            f"""
            create trigger audit_events_no_{event}
            before {event} on audit_events
            for each row execute function audit_events_are_append_only()
            """
        )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.execute("drop function audit_events_are_append_only()")
