"""Compliance rules.

Pure functions over dates. No database, no web framework, no clock of its own: "today" is a
parameter, because the answer depends on the agency's timezone and a test needs to pin it.

The vocabulary matters here. A credential is not simply "valid" or "expired":

- **expired** — the date on the document has passed. The person cannot be deployed.
- **unverified** — nobody at the agency has checked the document yet. Also not deployable.
- **expiring** — still good, but inside the horizon where a coordinator has to act.
- **valid** — good, and not yet urgent.
- **missing** — the role requires it and nothing has been recorded.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

DEFAULT_HORIZON_DAYS = 60


class CredentialState(StrEnum):
    expired = "expired"
    unverified = "unverified"
    expiring = "expiring"
    valid = "valid"
    missing = "missing"


class ReadinessState(StrEnum):
    non_compliant = "non_compliant"
    at_risk = "at_risk"
    compliant = "compliant"


@dataclass(frozen=True)
class CredentialView:
    """The only facts about a credential that the rules need."""

    credential_type_id: uuid.UUID
    expires_on: date | None
    verified: bool


@dataclass(frozen=True)
class Requirement:
    credential_type_id: uuid.UUID
    credential_type_name: str


@dataclass(frozen=True)
class RequirementStatus:
    credential_type_id: uuid.UUID
    credential_type_name: str
    state: CredentialState
    expires_on: date | None
    days_left: int | None


@dataclass(frozen=True)
class EmployeeCompliance:
    state: ReadinessState
    readiness: int
    items: tuple[RequirementStatus, ...]

    def count(self, *states: CredentialState) -> int:
        return sum(1 for item in self.items if item.state in states)


def days_until(expires_on: date | None, today: date) -> int | None:
    if expires_on is None:
        return None
    return (expires_on - today).days


def evaluate_credential(
    credential: CredentialView,
    *,
    today: date,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
) -> CredentialState:
    remaining = days_until(credential.expires_on, today)

    if remaining is not None and remaining < 0:
        return CredentialState.expired
    if not credential.verified:
        return CredentialState.unverified
    if remaining is not None and remaining <= horizon_days:
        return CredentialState.expiring
    return CredentialState.valid


def _best(candidates: list[CredentialView]) -> CredentialView | None:
    """A renewal supersedes the copy it replaces.

    Prefer a verified record, then the one that lasts longest. A credential without an expiry
    (a background check) outlasts one that expires.
    """
    if not candidates:
        return None

    return max(
        candidates,
        key=lambda credential: (
            credential.verified,
            credential.expires_on is None,
            credential.expires_on or date.min,
        ),
    )


def evaluate_employee(
    requirements: list[Requirement],
    credentials: list[CredentialView],
    *,
    today: date,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    grace_days: int = 0,
) -> EmployeeCompliance:
    """Roll the requirement set up into one deployability answer.

    `grace_days` lets an agency treat the last few days of a credential as still usable when
    scheduling. It affects the rollup, never the credential's own state.
    """
    by_type: dict[uuid.UUID, list[CredentialView]] = {}
    for credential in credentials:
        by_type.setdefault(credential.credential_type_id, []).append(credential)

    items: list[RequirementStatus] = []

    for requirement in requirements:
        candidate = _best(by_type.get(requirement.credential_type_id, []))
        if candidate is None:
            items.append(
                RequirementStatus(
                    credential_type_id=requirement.credential_type_id,
                    credential_type_name=requirement.credential_type_name,
                    state=CredentialState.missing,
                    expires_on=None,
                    days_left=None,
                )
            )
            continue

        items.append(
            RequirementStatus(
                credential_type_id=requirement.credential_type_id,
                credential_type_name=requirement.credential_type_name,
                state=evaluate_credential(candidate, today=today, horizon_days=horizon_days),
                expires_on=candidate.expires_on,
                days_left=days_until(candidate.expires_on, today),
            )
        )

    if not items:
        return EmployeeCompliance(state=ReadinessState.compliant, readiness=100, items=())

    blocking = {CredentialState.expired, CredentialState.missing}
    soft = {CredentialState.unverified, CredentialState.expiring}

    if any(item.state in blocking for item in items):
        state = ReadinessState.non_compliant
    elif any(item.state in soft for item in items):
        state = ReadinessState.at_risk
    else:
        state = ReadinessState.compliant

    usable = sum(
        1 for item in items if item.state in {CredentialState.valid, CredentialState.expiring}
    )
    return EmployeeCompliance(
        state=state, readiness=round(100 * usable / len(items)), items=tuple(items)
    )


def expires_in(days: int, today: date) -> date:
    return today + timedelta(days=days)
