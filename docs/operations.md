# Operations

## Roles and databases

| role | used by | RLS |
|---|---|---|
| `cleared_owner` | migrations, seed, the reminder job | bypasses |
| `cleared_app` | the API | enforced |

The API refuses to start without `CLEARED_DATABASE_URL` and `CLEARED_SECRET_KEY`. In production
it also disables `/docs` and `/openapi.json`.

## Migrations

```bash
make migrate                 # alembic upgrade head
make revision m="add x"      # autogenerate, then read the file before committing
```

Migrations run **before** the new process starts, never on boot. They are additive where
possible (expand → migrate → contract) so a rollback is a redeploy, not a data restore.

## The reminder job

```bash
uv run python -m cleared.jobs.reminders            # every agency
uv run python -m cleared.jobs.reminders --org northwind
uv run python -m cleared.jobs.reminders --date 2026-03-01   # rehearse a date
```

Run it daily from cron at 09:00 in the agency's morning — one deployment can serve agencies in
several zones, but the job is idempotent, so running it twice is safe:

```
0 9 * * *  cd /srv/cleared && uv run python -m cleared.jobs.reminders
```

The same work is available to an admin as `POST /v1/reminders/run`, which is useful when a
coordinator wants the schedule to run now rather than at nine.

Delivery goes through `cleared.mail.LogTransport` today. To send real mail, add a transport that
implements `send(Outgoing)` and swap `get_transport()`. Nothing else changes: the outbox is the
source of truth for what was queued, and the status column records what happened.

## Backups

- `pg_dump --format=custom` nightly, retained 30 days, plus the WAL if point-in-time recovery is
  required.
- Uploaded documents live under `CLEARED_UPLOAD_DIR`; back that up with the database, and keep
  the two consistent (dump the database after the files).
- A restore rehearsal is worth more than the backup policy. Do one before the first real agency
  onboards.

## Key rotation

`CLEARED_SECRET_KEY` signs session cookies. Rotating it invalidates every session — which is the
point. Announce it, or rotate during a maintenance window.

## Seeding

```bash
make seed
```

Creates Northwind Home Care (40 people, a credential catalogue, a requirement matrix, 40 days of
reminder history) and three users:

| email | role | password |
|---|---|---|
| `admin@northwind.example` | admin | `demo1234!` |
| `coordinator@northwind.example` | coordinator | `demo1234!` |
| `viewer@northwind.example` | viewer | `demo1234!` |

The seed is idempotent: running it twice adds nothing.

## Health

`GET /healthz` returns `200` without touching the database — it answers "is the process alive",
not "is the database reachable". A database-aware check belongs in the load balancer's
readiness probe, not in liveness; conflating them makes a database blip restart every process.
