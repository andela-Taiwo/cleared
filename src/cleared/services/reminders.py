"""Generating and delivering renewal reminders.

Two steps that are safe to repeat: `queue_due` writes rows the database will not duplicate,
and `deliver` moves queued rows to sent. A crash between them means the messages go out on the
next run, not twice.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from cleared.domain.models import (
    CredentialType,
    Employee,
    EmployeeCredential,
    ReminderEvent,
    ReminderRule,
    User,
)
from cleared.domain.reminders import ExpiringCredential, Rule, messages_for
from cleared.mail import Outgoing, Transport, get_transport

logger = logging.getLogger("cleared.reminders")


@dataclass(frozen=True)
class RunReport:
    generated: int
    sent: int


async def _coordinator_email(session: AsyncSession) -> str | None:
    """The longest-standing admin or coordinator receives the coordinator copy."""
    return await session.scalar(
        select(User.email)
        .where(User.role.in_(("admin", "coordinator")), User.is_active.is_(True))
        .order_by(User.created_at)
        .limit(1)
    )


async def queue_due(
    session: AsyncSession, *, organization_id: uuid.UUID, today: date, agency_name: str
) -> list[uuid.UUID]:
    rules = (
        await session.scalars(
            select(ReminderRule)
            .where(ReminderRule.is_active.is_(True))
            .order_by(ReminderRule.days_before.desc())
        )
    ).all()
    if not rules:
        return []

    coordinator = await _coordinator_email(session)
    type_names = {row.id: row.name for row in (await session.scalars(select(CredentialType))).all()}

    credentials = (
        await session.execute(
            select(
                EmployeeCredential.id,
                EmployeeCredential.expires_on,
                EmployeeCredential.credential_type_id,
                Employee.id,
                Employee.first_name,
                Employee.last_name,
                Employee.email,
            )
            .join(Employee, Employee.id == EmployeeCredential.employee_id)
            .where(
                Employee.status != "inactive",
                EmployeeCredential.expires_on.is_not(None),
            )
        )
    ).all()

    created: list[uuid.UUID] = []

    for credential in credentials:
        credential_id, expires_on, type_id, employee_id, first, last, email = credential
        if expires_on is None:
            continue

        item = ExpiringCredential(
            credential_id=credential_id,
            employee_id=employee_id,
            employee_name=f"{first} {last}",
            employee_email=email,
            coordinator_email=coordinator,
            credential_name=type_names.get(type_id, "credential"),
            expires_on=expires_on,
        )

        for rule in rules:
            for message in messages_for(
                item,
                Rule(
                    id=rule.id,
                    days_before=rule.days_before,
                    audience=rule.audience,
                    channel=rule.channel,
                ),
                today=today,
                agency_name=agency_name,
            ):
                statement = (
                    insert(ReminderEvent)
                    .values(
                        id=uuid7(),
                        organization_id=organization_id,
                        employee_credential_id=message.credential_id,
                        rule_id=message.rule_id,
                        employee_id=message.employee_id,
                        due_on=message.due_on,
                        channel=message.channel,
                        recipient=message.recipient,
                        subject=message.subject,
                        body=message.body,
                        status="queued",
                    )
                    .on_conflict_do_nothing(
                        index_elements=["employee_credential_id", "rule_id", "due_on", "recipient"]
                    )
                    .returning(ReminderEvent.id)
                )
                inserted = (await session.execute(statement)).scalar_one_or_none()
                if inserted is not None:
                    created.append(inserted)

    return created


async def deliver(session: AsyncSession, transport: Transport | None = None) -> int:
    sender = transport or get_transport()
    queued = (
        await session.scalars(
            select(ReminderEvent).where(ReminderEvent.status == "queued").limit(500)
        )
    ).all()

    sent = 0
    for event in queued:
        try:
            sender.send(Outgoing(recipient=event.recipient, subject=event.subject, body=event.body))
        except Exception:
            logger.exception("reminder delivery failed", extra={"event_id": str(event.id)})
            await session.execute(
                update(ReminderEvent).where(ReminderEvent.id == event.id).values(status="failed")
            )
            continue

        await session.execute(
            update(ReminderEvent)
            .where(ReminderEvent.id == event.id)
            .values(status="sent", sent_at=datetime.now(UTC))
        )
        sent += 1

    return sent


async def run(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    agency_name: str,
    today: date | None = None,
) -> RunReport:
    generated = await queue_due(
        session,
        organization_id=organization_id,
        today=today or date.today(),
        agency_name=agency_name,
    )
    sent = await deliver(session)
    return RunReport(generated=len(generated), sent=sent)
