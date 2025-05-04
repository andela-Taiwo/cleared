from __future__ import annotations

from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tests.support.api import sign_in
from tests.support.seed import Agency


async def seed_expiring_credential(client: AsyncClient, days: int) -> None:
    role = (
        await client.post("/v1/roles", json={"code": "CNA", "name": "Nursing Assistant"})
    ).json()
    credential_type = (
        await client.post(
            "/v1/credential-types", json={"name": "CPR", "code": "CPR", "category": "certification"}
        )
    ).json()
    await client.put(
        f"/v1/requirements/{role['id']}", json={"credential_type_ids": [credential_type["id"]]}
    )
    employee = (
        await client.post(
            "/v1/employees",
            json={
                "first_name": "Marisol",
                "last_name": "Vega",
                "email": "marisol@example.com",
                "job_role_id": role["id"],
            },
        )
    ).json()
    credential = (
        await client.post(
            f"/v1/employees/{employee['id']}/credentials",
            json={
                "credential_type_id": credential_type["id"],
                "expires_on": (date.today() + timedelta(days=days)).isoformat(),
            },
        )
    ).json()
    await client.post(f"/v1/credentials/{credential['id']}/verify")


async def test_rules_can_be_created_and_listed(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)

    created = await client.post("/v1/reminder-rules", json={"days_before": 30, "audience": "both"})

    assert created.status_code == 201, created.text
    listed = await client.get("/v1/reminder-rules")
    assert [rule["days_before"] for rule in listed.json()] == [30]


async def test_a_rule_can_be_paused(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    rule = (
        await client.post("/v1/reminder-rules", json={"days_before": 7, "audience": "employee"})
    ).json()

    response = await client.patch(f"/v1/reminder-rules/{rule['id']}", json={"is_active": False})

    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_running_the_schedule_queues_and_sends(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    await client.post("/v1/reminder-rules", json={"days_before": 30, "audience": "both"})
    await seed_expiring_credential(client, days=30)

    run = await client.post("/v1/reminders/run")

    assert run.status_code == 200, run.text
    assert run.json() == {"generated": 2, "sent": 2}

    outbox = await client.get("/v1/reminders")
    assert {event["status"] for event in outbox.json()} == {"sent"}


async def test_running_twice_does_not_duplicate(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    await client.post("/v1/reminder-rules", json={"days_before": 30, "audience": "both"})
    await seed_expiring_credential(client, days=30)
    await client.post("/v1/reminders/run")

    second = await client.post("/v1/reminders/run")

    assert second.json() == {"generated": 0, "sent": 0}
    assert len((await client.get("/v1/reminders")).json()) == 2


async def test_a_credential_that_is_not_due_is_not_queued(
    client: AsyncClient, agency: Agency
) -> None:
    await sign_in(client, agency)
    await client.post("/v1/reminder-rules", json={"days_before": 30, "audience": "both"})
    await seed_expiring_credential(client, days=45)

    run = await client.post("/v1/reminders/run")

    assert run.json() == {"generated": 0, "sent": 0}


async def test_the_outbox_is_append_only(
    client: AsyncClient, agency: Agency, owner_session: AsyncSession
) -> None:
    await sign_in(client, agency)
    await client.post("/v1/reminder-rules", json={"days_before": 30, "audience": "both"})
    await seed_expiring_credential(client, days=30)
    await client.post("/v1/reminders/run")

    import pytest
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError):
        async with owner_session.begin():
            await owner_session.execute(text("delete from reminder_events"))
