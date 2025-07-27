# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] — 2025-05-25

### Added
- Requirements matrix: which credentials each job role must hold, editable per role.
- Compliance overview with counts by state, a 60-day renewal timeline, and a per-role breakdown.
- Readiness on the roster and on the employee page.
- Reminder rules, an idempotent outbox, and a manual run.
- Compliance report as JSON and CSV.
- Append-only audit log for roster, credential, requirement and reminder changes.

### Fixed
- Expiry dates now use the agency's timezone rather than the server's.

## [0.1.0] — 2025-03-30

### Added
- Sign-in with server-side sessions and argon2 password hashes.
- Roster: employees, job roles, search, filters and CSV import.
- Credential catalogue and per-employee credential records, with verification.
- Row-level security on every tenant-owned table.
- Demo agency seed.

### Security
- The application connects as a non-owner role that cannot bypass row-level security.
