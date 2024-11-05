# Cleared

Credential compliance for home care and medical staffing agencies.

A home care agency cannot send a caregiver to a client without a current state licence, a CPR
card, a negative TB test and a cleared background check. Most agencies track those four things
in a spreadsheet, a paper binder and a coordinator's memory. When someone lapses, the agency
finds out at the worst possible moment: a client complaint, a state survey, or a shift nobody
can staff.

Cleared keeps the roster, the requirements and the expiry dates in one place, tells a
coordinator **who cannot be deployed today**, and chases renewals before they lapse.

## Status

Early. The repository is public while it is being built, so expect the shape of things to move.

- [x] Foundation: configuration, migrations, sessions, CI
- [ ] Roster and CSV import
- [ ] Credentials and expiry tracking
- [ ] Compliance view and dashboard
- [ ] Renewal reminders
- [ ] Compliance reports for payers

## How it is built

| | |
|---|---|
| API | FastAPI, SQLAlchemy 2 (async), Alembic |
| Database | PostgreSQL, row-level security for tenant isolation |
| Web | Vite, React, TypeScript, TanStack Query |
| Checks | Ruff, Pyright, Pytest, Biome, Vitest |

The API and the web app are separate deployables in one repository. The domain rules for
expiry and compliance are framework-free so they can be tested without a database.

## Getting started

Requires Python 3.12, Node 22+, and Docker.

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up -d
uv sync
uv run alembic upgrade head
uv run uvicorn cleared.main:app --reload
```

The web app:

```bash
cd web
npm install
npm run dev
```

`make check` runs everything CI runs.

## Licence

MIT. See [LICENSE](LICENSE).
