# 5. Timestamps from the database, dates in the agency's timezone

- **Status:** accepted
- **Date:** 2025-07-27

## Context

Two different kinds of time live in this system:

- **Instants** — when a row was created, when a message was sent, when a credential was verified.
- **Calendar dates** — when a licence expires, whether something is late.

Conflating them produces the classic bug: a credential that expires today reading as expired
from 19:00 in New York, because the server is on UTC and has already rolled over.

## Decision

- Instants are `timestamptz`, written by the database (`now()`), never by the application clock.
  `updated_at` is maintained by a `before update` trigger, so bulk updates and raw SQL move it
  too.
- Calendar dates are `date`. Nothing converts them to a timestamp, ever.
- "Today" is computed once per request from the agency's `organizations.timezone`:
  `today_in(organization.timezone)`. The reminder job uses the same helper.

## Consequences

- A test pins the boundary: at 02:30 UTC on 1 March, a New York agency is still on 28 February
  and a Tokyo agency is already on 1 March.
- Reports and dashboards agree with what a coordinator sees on the wall clock.
- The timezone is per agency, not per user. An agency operating across zones would need the
  field per location; the schema keeps that door open (`employees.location`).
- Equality comparisons against "today" are stable within a request because the date is computed
  once and passed down, not re-read per row.
