"""Reminder rules, the outbox, and a manual run."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlalchemy import delete, select
from uuid6 import uuid7

from cleared.api.deps import AdminDep, PrincipalDep, SessionDep
from cleared.api.errors import Problem
from cleared.db.tenant import tenant_scope
from cleared.domain.models import Organization, ReminderEvent, ReminderRule
from cleared.schemas.reminders import (
    ReminderEventOut,
    ReminderRuleCreate,
    ReminderRuleOut,
    ReminderRuleUpdate,
    ReminderRunOut,
)
from cleared.services import reminders as reminders_service

router = APIRouter(tags=["reminders"])


@router.get("/reminder-rules", summary="List reminder rules")
async def list_rules(principal: PrincipalDep, session: SessionDep) -> list[ReminderRuleOut]:
    async with tenant_scope(session, principal.organization_id):
        rows = (
            await session.scalars(select(ReminderRule).order_by(ReminderRule.days_before.desc()))
        ).all()
        return [ReminderRuleOut.model_validate(row) for row in rows]


@router.post("/reminder-rules", status_code=201, summary="Add a reminder rule")
async def create_rule(
    payload: ReminderRuleCreate, principal: AdminDep, session: SessionDep
) -> ReminderRuleOut:
    async with tenant_scope(session, principal.organization_id):
        existing = await session.scalar(
            select(ReminderRule).where(
                ReminderRule.days_before == payload.days_before,
                ReminderRule.audience == payload.audience,
            )
        )
        if existing is not None:
            raise Problem(409, "A rule for that day and audience already exists")

        rule = ReminderRule(
            id=uuid7(),
            organization_id=principal.organization_id,
            days_before=payload.days_before,
            audience=payload.audience,
            channel=payload.channel,
        )
        session.add(rule)
        await session.flush()
        return ReminderRuleOut.model_validate(rule)


@router.patch("/reminder-rules/{rule_id}", summary="Change a reminder rule")
async def update_rule(
    rule_id: uuid.UUID, payload: ReminderRuleUpdate, principal: AdminDep, session: SessionDep
) -> ReminderRuleOut:
    async with tenant_scope(session, principal.organization_id):
        rule = await session.scalar(select(ReminderRule).where(ReminderRule.id == rule_id))
        if rule is None:
            raise Problem(404, "Reminder rule not found")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)

        await session.flush()
        return ReminderRuleOut.model_validate(rule)


@router.delete("/reminder-rules/{rule_id}", status_code=204, summary="Delete a reminder rule")
async def delete_rule(rule_id: uuid.UUID, principal: AdminDep, session: SessionDep) -> None:
    async with tenant_scope(session, principal.organization_id):
        rule = await session.scalar(select(ReminderRule).where(ReminderRule.id == rule_id))
        if rule is None:
            raise Problem(404, "Reminder rule not found")
        await session.execute(delete(ReminderRule).where(ReminderRule.id == rule_id))


@router.get("/reminders", summary="The reminder outbox")
async def list_events(
    principal: PrincipalDep,
    session: SessionDep,
    status: Literal["queued", "sent", "failed", "skipped"] | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ReminderEventOut]:
    async with tenant_scope(session, principal.organization_id):
        statement = select(ReminderEvent).order_by(ReminderEvent.created_at.desc()).limit(limit)
        if status:
            statement = statement.where(ReminderEvent.status == status)
        rows = (await session.scalars(statement)).all()
        return [ReminderEventOut.model_validate(row) for row in rows]


@router.post("/reminders/run", summary="Queue and send today's reminders")
async def run_reminders(principal: AdminDep, session: SessionDep) -> ReminderRunOut:
    async with tenant_scope(session, principal.organization_id):
        organization = await session.scalar(
            select(Organization).where(Organization.id == principal.organization_id)
        )
        report = await reminders_service.run(
            session,
            organization_id=principal.organization_id,
            agency_name=organization.name if organization else "Your agency",
        )
        return ReminderRunOut(generated=report.generated, sent=report.sent)
