from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.support.api import sign_in
from tests.support.seed import Agency


async def test_mutations_are_recorded(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)

    created = await client.post(
        "/v1/employees", json={"first_name": "Ada", "last_name": "Lovelace"}
    )
    assert created.status_code == 201
    await client.patch(f"/v1/employees/{created.json()['id']}", json={"status": "inactive"})

    events = (await client.get("/v1/audit")).json()

    assert [event["action"] for event in events] == ["employee.updated", "employee.created"]
    assert events[0]["actor_name"] == "Admin User"


async def test_audit_events_cannot_be_changed(
    client: AsyncClient, agency: Agency, owner_session: AsyncSession
) -> None:
    await sign_in(client, agency)
    await client.post("/v1/employees", json={"first_name": "Ada", "last_name": "Lovelace"})

    with pytest.raises(DBAPIError):
        async with owner_session.begin():
            await owner_session.execute(text("update audit_events set action = 'nothing'"))

    with pytest.raises(DBAPIError):
        async with owner_session.begin():
            await owner_session.execute(text("delete from audit_events"))
