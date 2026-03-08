from __future__ import annotations

from datetime import date, timedelta

from httpx import AsyncClient
from tests.support.api import sign_in
from tests.support.seed import Agency


async def setup_agency(client: AsyncClient) -> dict[str, str]:
    """A CNA role that requires CPR and a TB test, and one employee holding neither."""
    role = (
        await client.post("/v1/roles", json={"code": "CNA", "name": "Nursing Assistant"})
    ).json()
    cpr = (
        await client.post(
            "/v1/credential-types", json={"name": "CPR", "code": "CPR", "category": "certification"}
        )
    ).json()
    tb = (
        await client.post(
            "/v1/credential-types", json={"name": "TB test", "code": "TB", "category": "health"}
        )
    ).json()
    await client.put(
        f"/v1/requirements/{role['id']}", json={"credential_type_ids": [cpr["id"], tb["id"]]}
    )
    employee = (
        await client.post(
            "/v1/employees",
            json={"first_name": "Marisol", "last_name": "Vega", "job_role_id": role["id"]},
        )
    ).json()
    return {"role": role["id"], "cpr": cpr["id"], "tb": tb["id"], "employee": employee["id"]}


async def test_missing_requirements_make_a_person_non_compliant(
    client: AsyncClient, agency: Agency
) -> None:
    await sign_in(client, agency)
    ids = await setup_agency(client)

    response = await client.get(f"/v1/compliance/employees/{ids['employee']}")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "non_compliant"
    assert body["readiness"] == 0
    assert {item["state"] for item in body["items"]} == {"missing"}


async def test_expiring_soon_is_at_risk(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    ids = await setup_agency(client)
    soon = (date.today() + timedelta(days=10)).isoformat()

    for credential_type in (ids["cpr"], ids["tb"]):
        created = (
            await client.post(
                f"/v1/employees/{ids['employee']}/credentials",
                json={"credential_type_id": credential_type, "expires_on": soon},
            )
        ).json()
        await client.post(f"/v1/credentials/{created['id']}/verify")

    body = (await client.get(f"/v1/compliance/employees/{ids['employee']}")).json()

    assert body["state"] == "at_risk"
    assert body["readiness"] == 100


async def test_the_overview_counts_states(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    await setup_agency(client)

    response = await client.get("/v1/compliance/overview")

    body = response.json()
    assert body["total"] == 1
    assert body["states"]["non_compliant"] == 1
    assert body["roles"][0]["role_name"] == "Nursing Assistant"


async def test_the_overview_lists_what_is_about_to_expire(
    client: AsyncClient, agency: Agency
) -> None:
    await sign_in(client, agency)
    ids = await setup_agency(client)
    soon = (date.today() + timedelta(days=5)).isoformat()

    for credential_type in (ids["cpr"], ids["tb"]):
        created = (
            await client.post(
                f"/v1/employees/{ids['employee']}/credentials",
                json={"credential_type_id": credential_type, "expires_on": soon},
            )
        ).json()
        await client.post(f"/v1/credentials/{created['id']}/verify")

    body = (await client.get("/v1/compliance/overview")).json()

    assert body["expiring"]["within_7"] == 2
    assert len(body["upcoming"]) == 2
    assert body["upcoming"][0]["days_left"] == 5


async def test_the_roster_carries_a_compliance_summary(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    await setup_agency(client)

    roster = (await client.get("/v1/employees")).json()

    assert roster["items"][0]["compliance"]["state"] == "non_compliant"
    assert roster["items"][0]["compliance"]["missing"] == 2


async def test_the_roster_can_be_filtered_to_blocked_people(
    client: AsyncClient, agency: Agency
) -> None:
    await sign_in(client, agency)
    await setup_agency(client)
    role = (await client.get("/v1/roles")).json()[0]
    await client.post(
        "/v1/employees",
        json={"first_name": "Ready", "last_name": "Person", "job_role_id": role["id"]},
    )

    blocked = await client.get("/v1/employees", params={"compliance": "non_compliant"})
    compliant = await client.get("/v1/employees", params={"compliance": "compliant"})

    assert [row["last_name"] for row in blocked.json()["items"]] == ["Person", "Vega"]
    assert blocked.json()["total"] == 2
    assert compliant.json()["total"] == 0
