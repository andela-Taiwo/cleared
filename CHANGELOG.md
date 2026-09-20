# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] — 2026-09-20

### Added
- Filter the roster by compliance state: "show me everyone who cannot work today".

### Changed
- Indexes for the three queries the screens actually run: the outbox, the audit page and an
  employee's credentials.

## [1.1.1] — 2026-07-12

### Fixed
- The seed now creates the credential catalogue and the requirement matrix on a fresh database,
  so a new clone shows a meaningful demo instead of forty empty files.

## [1.1.0] — 2026-01-18

### Fixed
- A session the server no longer recognises is cleared from the browser instead of being resent
  on every request.

### Added
- Postmortem for the June 2025 expiry bug, in `docs/postmortems/`.

## [1.0.0] — 2025-11-09

First version that a real agency could run for a week.

### Added
- Roster: employees, job roles, search, filters, CSV import, and readiness on every row.
- Credential catalogue and per-employee records, with verification and expiry dates.
- Requirements matrix per role; change it and the roster re-scores.
- Compliance engine: per-credential states, per-person rollup, readiness percentage.
- Dashboard: compliance rate, blocked and at-risk counts, a 60-day renewal timeline, per-role
  breakdown.
- Reminders: 60/30/14/7/1-day rules, an idempotent outbox, a delivery log, and a nightly job.
- Compliance report as a printable page and as CSV.
- Append-only audit log for every roster, credential, requirement and reminder change.
- Role-based access: admin, coordinator, viewer, enforced per endpoint and tested per role.

### Changed
- The reminder schedule runs on the agency's calendar day, not the server's.

### Fixed
- Expiry states no longer flip a day early for agencies west of UTC.
- A credential that had been renewed no longer reads as expired because an older copy is still
  on file.

### Security
- Row-level security on every tenant-owned table, forced for owners, with the API connecting as
  a role that cannot bypass it.
- Sessions are hashed at rest; cookies are `HttpOnly` and `SameSite=Lax`.
- gitleaks runs over the full history in CI.

## [0.4.0] — 2025-05-25

### Added
- Requirements matrix and the compliance overview.
- Reminder rules and the outbox.
- Compliance report and CSV export.

## [0.1.0] — 2025-03-30

### Added
- Sign-in, sessions, the roster, CSV import, and credential records.
- Row-level security and the demo seed.
