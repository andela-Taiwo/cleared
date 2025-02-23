from __future__ import annotations

import uuid
from datetime import date

from cleared.domain.compliance import (
    CredentialState,
    CredentialView,
    ReadinessState,
    Requirement,
    days_until,
    evaluate_credential,
    evaluate_employee,
    expires_in,
)

TODAY = date(2026, 3, 1)
HORIZON = 60

CPR = uuid.UUID("11111111-1111-1111-1111-111111111111")
LICENCE = uuid.UUID("22222222-2222-2222-2222-222222222222")


def credential(
    credential_type_id: uuid.UUID = CPR, days: int | None = 365, verified: bool = True
) -> CredentialView:
    return CredentialView(
        credential_type_id=credential_type_id,
        expires_on=expires_in(days, TODAY) if days is not None else None,
        verified=verified,
    )


# Credential-level rules ---------------------------------------------------


def test_a_past_expiry_is_expired() -> None:
    assert evaluate_credential(credential(days=-1), today=TODAY) is CredentialState.expired


def test_today_is_still_usable_but_expiring() -> None:
    state = evaluate_credential(credential(days=0), today=TODAY)
    assert state is CredentialState.expiring


def test_the_horizon_boundary_is_inclusive() -> None:
    assert evaluate_credential(credential(days=HORIZON), today=TODAY) is CredentialState.expiring
    assert evaluate_credential(credential(days=HORIZON + 1), today=TODAY) is CredentialState.valid


def test_an_unverified_copy_is_not_usable() -> None:
    assert (
        evaluate_credential(credential(verified=False), today=TODAY) is CredentialState.unverified
    )


def test_an_expired_document_beats_an_unverified_one() -> None:
    state = evaluate_credential(credential(days=-3, verified=False), today=TODAY)
    assert state is CredentialState.expired


def test_a_credential_without_an_expiry_is_valid_once_verified() -> None:
    assert evaluate_credential(credential(days=None), today=TODAY) is CredentialState.valid


def test_an_unverified_credential_without_an_expiry_is_unverified() -> None:
    state = evaluate_credential(credential(days=None, verified=False), today=TODAY)
    assert state is CredentialState.unverified


def test_days_until_is_none_without_an_expiry() -> None:
    assert days_until(None, TODAY) is None
    assert days_until(expires_in(10, TODAY), TODAY) == 10


# Employee rollup ----------------------------------------------------------


def requirements(*types: uuid.UUID) -> list[Requirement]:
    return [
        Requirement(credential_type_id=type_id, credential_type_name=f"type-{index}")
        for index, type_id in enumerate(types)
    ]


def test_a_missing_requirement_blocks_deployment() -> None:
    result = evaluate_employee(requirements(CPR, LICENCE), [credential(LICENCE)], today=TODAY)

    assert result.state is ReadinessState.non_compliant
    assert result.readiness == 50
    assert result.items[0].state is CredentialState.missing


def test_an_expired_requirement_blocks_deployment() -> None:
    result = evaluate_employee(requirements(CPR), [credential(days=-2)], today=TODAY)

    assert result.state is ReadinessState.non_compliant


def test_expiring_soon_is_at_risk_not_blocked() -> None:
    result = evaluate_employee(requirements(CPR), [credential(days=10)], today=TODAY)

    assert result.state is ReadinessState.at_risk
    assert result.items[0].days_left == 10


def test_everything_current_is_compliant() -> None:
    result = evaluate_employee(
        requirements(CPR, LICENCE), [credential(CPR), credential(LICENCE, 900)], today=TODAY
    )

    assert result.state is ReadinessState.compliant
    assert result.readiness == 100


def test_a_renewal_supersedes_the_expired_copy() -> None:
    old = credential(days=-30)
    new = credential(days=700)

    result = evaluate_employee(requirements(CPR), [old, new], today=TODAY)

    assert result.items[0].state is CredentialState.valid
    assert result.state is ReadinessState.compliant


def test_the_longest_lasting_verified_copy_wins() -> None:
    unverified_but_longer = credential(days=900, verified=False)
    verified_but_shorter = credential(days=300, verified=True)

    result = evaluate_employee(
        requirements(CPR), [unverified_but_longer, verified_but_shorter], today=TODAY
    )

    assert result.items[0].state is CredentialState.valid


def test_no_requirements_is_trivially_compliant() -> None:
    result = evaluate_employee([], [], today=TODAY)

    assert result.state is ReadinessState.compliant
    assert result.readiness == 100
    assert result.items == ()


def test_a_role_with_two_problems_counts_both() -> None:
    result = evaluate_employee(
        requirements(CPR, LICENCE), [credential(CPR, -1), credential(LICENCE, -5)], today=TODAY
    )

    assert result.count(CredentialState.expired) == 2
    assert result.readiness == 0
