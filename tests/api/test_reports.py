from __future__ import annotations

import csv
import io

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.support.api import sign_in
from tests.support.seed import Agency, add_user


async def seed_one(client: AsyncClient) -> None:
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
    await client.post(
        "/v1/employees",
        json={"first_name": "Marisol", "last_name": "Vega", "job_role_id": role["id"]},
    )


async def test_the_report_lists_everyone(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    await seed_one(client)

    response = await client.get("/v1/reports/compliance")

    body = response.json()
    assert body["total"] == 1
    assert body["rows"][0]["state"] == "non_compliant"
    assert body["rows"][0]["missing"] == 1


async def test_the_csv_download_has_a_header_and_a_row(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    await seed_one(client)

    response = await client.get("/v1/reports/compliance.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0][0] == "employee_no"
    assert rows[1][1] == "Vega"
    assert rows[1][5] == "non_compliant"


async def test_a_viewer_can_download_the_report(
    client: AsyncClient, agency: Agency, owner_session: AsyncSession
) -> None:
    await sign_in(client, agency)
    await seed_one(client)

    viewer = await add_user(owner_session, agency, role="viewer")
    await sign_in(client, viewer)

    response = await client.get("/v1/reports/compliance.csv")

    assert response.status_code == 200
