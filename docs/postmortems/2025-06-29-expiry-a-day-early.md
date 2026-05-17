# Postmortem: credentials read as expired a day early

**Date:** 2025-06-29 · **Severity:** high (wrong compliance answers) · **Duration:** since the
first commit, noticed during a demo

## What happened

During a walkthrough for a home care coordinator, a CPR card that expires "today" showed as
**Expired**. The agency is in Boston. The server is on UTC. At 19:00 local, UTC has already
rolled over to tomorrow, so `date.today()` on the server disagreed with the calendar on the wall.

## Impact

- Every credential expiring today read as expired from 19:00 local onward (20:00 in winter).
- The nightly reminder job could fire a "your credential expires today" message a day late, or a
  "1 day left" message on the day of expiry.
- Nobody was harmed; no agency was running the software yet. The bug existed since the first
  compliance commit.

## Cause

The compliance engine took `today` as an implicit parameter: `date.today()` computed from the
server clock. The rules themselves were pure, but the *caller* supplied the wrong date. Nothing
in the type system said "this date must be in the agency's timezone", so every new call site
could repeat the mistake.

## Detection

Manual, in a demo. That is the uncomfortable part: the unit tests pinned dates but not
timezones, because the tests themselves were written from the same UTC assumption as the code.

## Fix

- `domain/timezones.py` with `today_in(organization.timezone, now=None)`.
- Every computation of "today" goes through it: dashboard, roster, employee page, reports, and
  the reminder job (which had its own `date.today()`).
- Tests pin the boundary either side of midnight UTC, for a zone behind and a zone ahead.

## What would have caught it earlier

1. A test that treats "today" as an input, from a zone that is not UTC. We had the first half.
2. A demo script that runs at an awkward hour. The bug is invisible between 05:00 and 19:00 UTC.
3. A type that distinguishes an instant from a calendar date. We have the convention now
   ([ADR 0005](../adr/0005-time-and-timezones.md)); the compiler still cannot enforce it.
