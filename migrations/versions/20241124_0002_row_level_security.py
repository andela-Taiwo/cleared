"""row level security

Revision ID: 0002
Revises: 0001
Create Date: 2024-11-24 19:08:31+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# `nullif(..., '')` matters: a pooled connection that has already served a request carries an
# empty setting rather than no setting, and `''::uuid` would raise instead of hiding the rows.
TENANT_PREDICATE = "nullif(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    # The row *is* the tenant, so a tenant may only see and change its own row. There is no
    # delete policy: offboarding an organisation is an operator action, not a tenant action.
    op.execute("alter table organizations enable row level security")
    op.execute("alter table organizations force row level security")
    op.execute(
        f"""
        create policy tenant_isolation on organizations
        using (id = {TENANT_PREDICATE})
        with check (id = {TENANT_PREDICATE})
        """
    )

    op.execute("alter table users enable row level security")
    op.execute("alter table users force row level security")
    op.execute(
        f"""
        create policy tenant_isolation on users
        using (organization_id = {TENANT_PREDICATE})
        with check (organization_id = {TENANT_PREDICATE})
        """
    )


def downgrade() -> None:
    for table in ("users", "organizations"):
        op.execute(f"drop policy tenant_isolation on {table}")
        op.execute(f"alter table {table} disable row level security")
