# 1. A modular monolith: one repo, two deployables

- **Status:** accepted
- **Date:** 2025-07-27

## Context

The product is a compliance system for home care agencies. The domain is small, the queries are
relational, and there is exactly one team. Splitting into services now would buy nothing and
cost a lot: distributed transactions for "record this credential and audit it", two deploy
pipelines, and a network hop on every roster page.

## Decision

One repository containing two deployables:

- `src/cleared` — the API. FastAPI, SQLAlchemy, Alembic. It owns the database and all rules.
- `web` — the browser client. Vite, React, TypeScript. It owns presentation and nothing else.

The API is the only thing that talks to PostgreSQL. The web app is served as static files and
calls `/v1` on the same origin.

Inside the API, the layering is enforced by convention and by review:

```
api (routes, dependencies)  →  services (transactions, orchestration)  →  domain (pure rules)
                                        ↘  db (models, session, tenant context)
```

`domain/` imports no web framework and no database driver. That is why the compliance rules have
fast tests and why the same functions run in the request path and in the nightly job.

## Consequences

- A single deployable pair, a single migration history, one transaction for a change and its
  audit row. Simple to reason about, simple to run.
- The web app cannot be scaled independently of the API. At this size that is a non-issue.
- If a worker ever needs to scale separately, `jobs/` is already a separate process entry point;
  extracting it is a deployment change, not a rewrite.
