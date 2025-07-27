# 2. Tenant isolation is a row-level security policy, not a `where` clause

- **Status:** accepted
- **Date:** 2025-07-27

## Context

Every table holding customer data carries `organization_id`. The obvious approach is to filter
in the application: `select(...).where(Employee.organization_id == principal.organization_id)`.
It works until somebody adds an endpoint and forgets the clause, at which point one agency can
read another agency's staff records. That is the kind of bug that ends a company.

## Decision

The database enforces it.

- Every tenant-owned table has `organization_id`, `ENABLE ROW LEVEL SECURITY` and
  `FORCE ROW LEVEL SECURITY`, with the same policy:
  `organization_id = nullif(current_setting('app.tenant_id', true), '')::uuid`.
- The application connects as `cleared_app`, which is **not** the table owner and has no
  `BYPASSRLS`. Migrations connect as `cleared_owner`, which may bypass RLS — which is exactly
  why the application never uses that role.
- Each request runs in one transaction whose first statement is
  `set_config('app.tenant_id', <uuid>, true)`. Transaction-local, so a pooled connection cannot
  carry a tenant into the next request.
- No tenant set means no rows: the policy compares against `NULL`, which matches nothing. The
  failure mode is closed.

Two tables are deliberately global: `sessions` (a session is how a request learns its tenant)
and `alembic_version`. A test asserts that every table is either isolated by the standard policy
or on that reviewed list, so a new table cannot quietly skip isolation.

## Consequences

- Forgetting a `where` clause leaks nothing. The cost is that tests must set a tenant to see
  data, which is a useful forcing function.
- Login cannot read `users` before a tenant is known, so there is exactly one narrow
  `security definer` function, `cleared_auth_lookup(email)`, that returns one row by exact
  email. It is the only cross-tenant read path, and it is auditable in one place.
- Connection pooling is safe because the setting is transaction-local.
