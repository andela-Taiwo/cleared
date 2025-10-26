"""indexes for the screens that matter

Revision ID: 0010
Revises: 0009
Create Date: 2025-10-26 19:04:12+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The outbox page and the delivery loop both filter on status inside one tenant.
    op.create_index(
        "ix_reminder_events_organization_id_status_created_at",
        "reminder_events",
        ["organization_id", "status", "created_at"],
    )
    # The audit page is "newest first, one tenant".
    op.create_index(
        "ix_audit_events_organization_id_created_at",
        "audit_events",
        ["organization_id", sa.text("created_at desc")],
    )
    # Employee pages load one person's credentials; RLS already pins the tenant.
    op.create_index(
        "ix_employee_credentials_organization_id_employee_id",
        "employee_credentials",
        ["organization_id", "employee_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_employee_credentials_organization_id_employee_id")
    op.drop_index("ix_audit_events_organization_id_created_at")
    op.drop_index("ix_reminder_events_organization_id_status_created_at")
