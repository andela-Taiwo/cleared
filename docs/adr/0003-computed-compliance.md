# 3. Compliance is computed, not stored

- **Status:** accepted
- **Date:** 2025-07-27

## Context

"Can this person work today?" depends on four things: the credential's expiry date, whether
anyone checked the document, which credentials the person's role requires, and what today is.
Three of those change without anyone editing the employee record. A stored `status` column
would be wrong the moment the clock moved, and every read would need to trust that some job ran.

## Decision

Store the facts, compute the answer.

- Stored: credentials (dates, verification), the role requirement matrix, employees.
- Computed on read: `expired`, `unverified`, `expiring`, `valid`, `missing`, per requirement,
  and a rollup (`compliant`, `at_risk`, `non_compliant`) with a readiness percentage.
- The rules live in `domain/compliance.py` as pure functions with `today` as a parameter and
  no database access.

The vocabulary is deliberately precise:

| state | meaning | deployable? |
|---|---|---|
| `expired` | the date on the document has passed | no |
| `missing` | the role requires it and nothing is recorded | no |
| `unverified` | recorded, but nobody checked the document | no |
| `expiring` | still good, inside the horizon (60 days) | yes, but act |
| `valid` | good, and not urgent | yes |

`expired` outranks `unverified`: an out-of-date document is the more important fact.

## Consequences

- The dashboard is always correct for the agency's current date, with no background recompute.
- Reads cost more: the roster page loads requirements and credentials and computes in Python.
  At a few hundred employees this is faster than the queries it replaces; the shape is a single
  pass over data already in memory. If an agency reaches tens of thousands of staff, the
  rollup moves into a materialised view refreshed on write — a change inside one service.
- Every rule is testable without a database, which is why the timezone bug below was found by a
  unit test rather than by a customer.
