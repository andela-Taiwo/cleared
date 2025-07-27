# 4. Reminders go through an idempotent outbox

- **Status:** accepted
- **Date:** 2025-07-27

## Context

A coordinator who receives the same reminder four times stops reading them. A scheduler that
crashes halfway through a run must not resend what it already sent. And the product has to be
able to answer "what did we tell this person, and when" — which is a question agencies get asked
during a survey.

## Decision

Two steps, both safe to repeat:

1. **Queue.** For every credential whose expiry is exactly `days_before` away, write one row per
   (credential, rule, recipient, due date). A unique constraint on that tuple plus
   `on conflict do nothing` makes a re-run a no-op. The rule is dull on purpose: fire on the
   exact day, once.
2. **Deliver.** Read queued rows, hand them to a transport, mark `sent` (or `failed`). A crash
   between the two steps means the messages go out on the next run, not twice.

Rows are never deleted. Delivery status may change; the record of what was queued does not.

The transport is an interface with one implementation today: it logs. Swapping in a real
provider (Postmark, SES) is a class behind the same `send()` signature, and the outbox keeps
working unchanged.

## Consequences

- The scheduler is idempotent, so cron can run it twice, or a human can press "run now" without
  fear. This is tested: running the schedule twice in a row produces zero new rows.
- Reminders are tied to a credential, so renewing one starts a new cycle naturally.
- No retry/backoff yet: a failed send is marked `failed` and stays visible. That is honest for
  an MVP and better than silent loss.
