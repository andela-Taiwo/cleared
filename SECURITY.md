# Security

## Reporting a vulnerability

Email the maintainer directly rather than opening a public issue. Include the version, what you
did, and what happened. You will get an acknowledgement within 72 hours.

## What is already in place

- **Tenant isolation in the database.** Every tenant-owned table has row-level security, forced
  for the table owner as well, and the application connects as a role without `BYPASSRLS`
  ([ADR 0002](docs/adr/0002-row-level-security.md)).
- **Passwords** are hashed with argon2id; sessions are random 256-bit tokens stored only as
  SHA-256 hashes, in `HttpOnly`, `SameSite=Lax` cookies, `Secure` in production.
- **Authorisation** is explicit: `admin`, `coordinator`, `viewer`, enforced in dependencies and
  covered by tests that assert the 403 and the cross-tenant 404.
- **Audit log** is append-only, enforced by a database trigger, and written in the same
  transaction as the change it describes.
- **Secrets** come from the environment only; `.env` is ignored and `.env.example` contains no
  real values. CI runs gitleaks over the full history.

## Not in scope yet

- MFA and SSO. Buy these rather than build them when the first enterprise buyer asks.
- Per-field encryption at rest. Disk-level encryption plus backups is the current answer.
- Rate limiting on the login endpoint. It is the next thing to add if this is exposed publicly.
