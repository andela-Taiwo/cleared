from __future__ import annotations

import uuid
from datetime import date

from cleared.domain.reminders import ExpiringCredential, Rule, days_left, messages_for

TODAY = date(2026, 5, 1)
CREDENTIAL = ExpiringCredential(
    credential_id=uuid.uuid4(),
    employee_id=uuid.uuid4(),
    employee_name="Marisol Vega",
    employee_email="marisol@example.com",
    coordinator_email="coordinator@example.com",
    credential_name="CPR / BLS",
    expires_on=date(2026, 5, 31),
)


def rule(days_before: int, audience: str = "both") -> Rule:
    return Rule(id=uuid.uuid4(), days_before=days_before, audience=audience, channel="email")


def test_days_left_counts_calendar_days() -> None:
    assert days_left(CREDENTIAL, TODAY) == 30


def test_a_rule_fires_only_on_its_own_day() -> None:
    assert messages_for(CREDENTIAL, rule(31), today=TODAY, agency_name="Northwind") == []
    assert len(messages_for(CREDENTIAL, rule(30), today=TODAY, agency_name="Northwind")) == 2


def test_both_audiences_get_one_message_each() -> None:
    messages = messages_for(CREDENTIAL, rule(30), today=TODAY, agency_name="Northwind")

    assert {message.recipient for message in messages} == {
        "marisol@example.com",
        "coordinator@example.com",
    }
    assert all(
        "31 May 2026" in message.subject or "31 May 2026" in message.body for message in messages
    )


def test_the_employee_copy_is_written_to_the_employee() -> None:
    messages = messages_for(CREDENTIAL, rule(30, "employee"), today=TODAY, agency_name="Northwind")

    assert len(messages) == 1
    assert "Hi Marisol" in messages[0].body
    assert "CPR / BLS" in messages[0].subject


def test_the_coordinator_copy_names_the_person() -> None:
    messages = messages_for(
        CREDENTIAL, rule(30, "coordinator"), today=TODAY, agency_name="Northwind"
    )

    assert len(messages) == 1
    assert messages[0].subject.startswith("Marisol Vega —")


def test_no_address_means_no_message() -> None:
    credential = ExpiringCredential(
        credential_id=uuid.uuid4(),
        employee_id=uuid.uuid4(),
        employee_name="No Email",
        employee_email=None,
        coordinator_email=None,
        credential_name="TB test",
        expires_on=date(2026, 5, 31),
    )

    assert messages_for(credential, rule(30), today=TODAY, agency_name="Northwind") == []
