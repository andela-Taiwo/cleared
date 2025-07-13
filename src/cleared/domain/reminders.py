"""Who gets told what, and when.

The rule is deliberately dull: on the day a credential is exactly N days from expiry, the
people on the rule's audience get one message. Everything interesting — idempotency, delivery,
retries — belongs to the service around this, not to the rules.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Rule:
    id: uuid.UUID
    days_before: int
    audience: str  # employee | coordinator | both
    channel: str


@dataclass(frozen=True)
class ExpiringCredential:
    credential_id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    employee_email: str | None
    coordinator_email: str | None
    credential_name: str
    expires_on: date


@dataclass(frozen=True)
class Message:
    credential_id: uuid.UUID
    rule_id: uuid.UUID
    employee_id: uuid.UUID
    recipient: str
    subject: str
    body: str
    channel: str
    due_on: date


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def days_left(credential: ExpiringCredential, today: date) -> int:
    return (credential.expires_on - today).days


def _employee_message(
    credential: ExpiringCredential, rule: Rule, today: date, agency_name: str
) -> Message | None:
    if not credential.employee_email:
        return None

    remaining = days_left(credential, today)
    subject = f"Your {credential.credential_name} expires on {credential.expires_on:%d %b %Y}"
    body = (
        f"Hi {credential.employee_name.split(' ')[0]},\n\n"
        f"Our records show your {credential.credential_name} expires on "
        f"{credential.expires_on:%d %B %Y} — in {_plural(remaining, 'day')}.\n\n"
        "Please send a copy of the renewed document to your coordinator before then. "
        "If it has already been renewed, reply with the new expiry date and we will update "
        "your file.\n\n"
        f"Thank you,\n{agency_name}\n"
    )
    return Message(
        credential_id=credential.credential_id,
        rule_id=rule.id,
        employee_id=credential.employee_id,
        recipient=credential.employee_email,
        subject=subject,
        body=body,
        channel=rule.channel,
        due_on=today,
    )


def _coordinator_message(
    credential: ExpiringCredential, rule: Rule, today: date, agency_name: str
) -> Message | None:
    if not credential.coordinator_email:
        return None

    remaining = days_left(credential, today)
    subject = (
        f"{credential.employee_name} — {credential.credential_name} expires in {remaining} days"
    )
    body = (
        f"{credential.employee_name}'s {credential.credential_name} expires on "
        f"{credential.expires_on:%d %B %Y}.\n\n"
        "They stay on the compliance report as unrenewed until a new document is recorded "
        "and checked.\n\n"
        f"— {agency_name}\n"
    )
    return Message(
        credential_id=credential.credential_id,
        rule_id=rule.id,
        employee_id=credential.employee_id,
        recipient=credential.coordinator_email,
        subject=subject,
        body=body,
        channel=rule.channel,
        due_on=today,
    )


def messages_for(
    credential: ExpiringCredential,
    rule: Rule,
    *,
    today: date,
    agency_name: str,
) -> list[Message]:
    if days_left(credential, today) != rule.days_before:
        return []

    messages: list[Message] = []
    if rule.audience in ("employee", "both"):
        employee_message = _employee_message(credential, rule, today, agency_name)
        if employee_message:
            messages.append(employee_message)
    if rule.audience in ("coordinator", "both"):
        coordinator_message = _coordinator_message(credential, rule, today, agency_name)
        if coordinator_message:
            messages.append(coordinator_message)
    return messages
