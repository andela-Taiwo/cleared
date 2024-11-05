# Contributing

## The loop

1. Open an issue describing the change, or comment on an existing one. Small fixes can skip this.
2. Branch from `main`: `feat/…`, `fix/…`, `chore/…`, `docs/…`.
3. Keep the branch to one concern. If the diff needs a paragraph to explain two unrelated things,
   split it.
4. `make check` must be green before you push.
5. Open a pull request using the template. Describe what changed, what you decided, and how you
   verified it.

## Commits

Conventional Commits, lower case, imperative mood, scoped where it helps:

```
feat(compliance): count a credential as expiring inside the horizon
fix(reminders): generate one row per credential, rule and due date
docs: record why the app connects as a non-owner role
```

The body explains **why**, not what. The diff already says what.

## Tests

- Domain rules (expiry, compliance, reminder scheduling) get unit tests, no database.
- Endpoints get tests against a real PostgreSQL database named `cleared_test`. The harness
  refuses to run against anything else.
- Every endpoint that touches tenant data gets a test proving another tenant sees a 404.

## Migrations

Generate with `uv run alembic revision --autogenerate -m "…"`, then read the file before
committing it. Never edit a migration that has already been applied.
