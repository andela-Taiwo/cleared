# Domain model

```
organizations 1──* users
       │
       ├──* job_roles ──* role_requirements *── credential_types
       │                        │
       └──* employees ──────────┴──* employee_credentials ──* reminder_events
                    │
                    └──* sessions (global, tells a request its tenant)

audit_events — append-only, belongs to an organization
```

## Tenancy

Every table with an `organization_id` is protected by row-level security (see
[ADR 0002](adr/0002-row-level-security.md)). `sessions` and `alembic_version` are global by
design and listed in the isolation test.

## Entities

**Organization** — one agency. Carries the timezone that decides what "today" means.

**User** — someone who signs in: `admin` (everything, including configuration), `coordinator`
(roster and credentials), `viewer` (read and export only).

**JobRole** — a kind of worker the agency deploys: CNA, HHA, RN, LPN, PT. Roles are the unit of
requirement, not job titles.

**CredentialType** — a kind of evidence: licence, certification, clearance, health check,
training. An agency's catalogue is its own; two agencies disagree about what a CNA needs.

**RoleRequirement** — the row that says "an RN must hold this". Presence means required; there
is no `required = false` row to go stale.

**Employee** — a person on the roster, with a role, a status (`active`, `onboarding`,
`inactive`) and a location.

**EmployeeCredential** — one document, with its own dates. A renewal is a second row, not an
edit: the history of what was on file matters, and the compliance engine picks the best current
copy ([ADR 0003](adr/0003-computed-compliance.md)).

**ReminderRule / ReminderEvent** — the schedule, and the append-only record of what was sent
([ADR 0004](adr/0004-reminder-outbox.md)).

**AuditEvent** — who changed what, in the same transaction as the change.

## Lifecycle of a credential

```
recorded ──verify──▶ verified ──▶ expiring (inside 60 days) ──▶ expired
   │                     │
   └── no document ──────┘ (stays unverified, not deployable)
```

Renewing records a new row with a later `expires_on`; the older row stays as history and stops
determining the state as soon as the new one is verified and later.

## Invariants worth knowing

- A person's state is a function of their role's requirements and their credentials. Nothing
  caches it.
- Deleting a credential type is refused while any credential references it (`on delete restrict`).
- Deleting an employee cascades to their credentials; the audit log keeps the record.
- The outbox and the audit log cannot be deleted from the application role.
