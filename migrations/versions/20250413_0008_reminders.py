"""reminder rules and the outbox

Revision ID: 0008
Revises: 0007
Create Date: 2025-04-13 19:40:16+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_PREDICATE = "nullif(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "reminder_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("days_before", sa.Integer(), nullable=False),
        sa.Column(
            "channel", sa.String(length=20), server_default=sa.text("'email'"), nullable=False
        ),
        sa.Column("audience", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            "days_before >= 0 and days_before <= 365", name=op.f("ck_reminder_rules_days_in_range")
        ),
        sa.CheckConstraint(
            "audience in ('employee', 'coordinator', 'both')",
            name=op.f("ck_reminder_rules_audience_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_reminder_rules_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reminder_rules")),
        sa.UniqueConstraint(
            "organization_id",
            "days_before",
            "audience",
            name=op.f("uq_reminder_rules_organization_id_days_before_audience"),
        ),
    )
    op.create_index(
        op.f("ix_reminder_rules_organization_id"), "reminder_rules", ["organization_id"]
    )

    # Append-only outbox. A row is one message to one person about one credential on one day;
    # the unique constraint makes re-running the scheduler safe.
    op.create_table(
        "reminder_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_credential_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default=sa.text("'queued'"), nullable=False
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('queued', 'sent', 'failed', 'skipped')",
            name=op.f("ck_reminder_events_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["employee_credential_id"],
            ["employee_credentials.id"],
            name=op.f("fk_reminder_events_employee_credential_id_employee_credentials"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name=op.f("fk_reminder_events_employee_id_employees"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_reminder_events_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["reminder_rules.id"],
            name=op.f("fk_reminder_events_rule_id_reminder_rules"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reminder_events")),
        sa.UniqueConstraint(
            "employee_credential_id",
            "rule_id",
            "due_on",
            "recipient",
            name=op.f("uq_reminder_events_credential_rule_due_recipient"),
        ),
    )
    op.create_index(
        op.f("ix_reminder_events_organization_id"), "reminder_events", ["organization_id"]
    )
    op.create_index(
        "ix_reminder_events_status_created_at", "reminder_events", ["status", "created_at"]
    )

    for table in ("reminder_rules", "reminder_events"):
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
        """
        create trigger reminder_rules_set_updated_at
        before update on reminder_rules
        for each row execute function set_updated_at()
        """
    )
    # The outbox is append-only: a sent message is a record of something that happened.
    op.execute(
        """
        create function reminder_events_are_append_only() returns trigger
        language plpgsql as $$
        begin
            raise exception 'reminder_events is append-only';
        end;
        $$
        """
    )
    op.execute(
        """
        create trigger reminder_events_no_delete
        before delete on reminder_events
        for each row execute function reminder_events_are_append_only()
        """
    )


def downgrade() -> None:
    op.drop_table("reminder_events")
    op.drop_table("reminder_rules")
    op.execute("drop function reminder_events_are_append_only()")
