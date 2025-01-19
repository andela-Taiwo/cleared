from __future__ import annotations

from httpx import AsyncClient
from tests.support.api import sign_in
from tests.support.seed import Agency


async def make_role(client: AsyncClient, code: str) -> dict:
    response = await client.post("/v1/roles", json={"code": code, "name": code})
    assert response.status_code == 201, response.text
    return response.json()


async def upload(client: AsyncClient, text: str) -> dict:
    response = await client.post(
        "/v1/employees/import",
        files={"file": ("roster.csv", text.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_import_creates_the_roster(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    await make_role(client, "CNA")

    report = await upload(
        client,
        "first_name,last_name,email,role_code,employee_no\n"
        "Marisol,Vega,marisol@example.com,CNA,NW-001\n"
        "Dennis,Okafor,dennis@example.com,CNA,NW-002\n",
    )

    assert report == {"created": 2, "updated": 0, "failed": 0, "errors": []}

    roster = await client.get("/v1/employees")
    assert roster.json()["total"] == 2
    assert roster.json()["items"][0]["job_role"]["code"] == "CNA"


async def test_import_updates_a_known_employee_number(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    await upload(client, "first_name,last_name,employee_no\nMarisol,Vega,NW-001\n")

    report = await upload(
        client, "first_name,last_name,employee_no,status\nMarisol,Vega-Reid,NW-001,inactive\n"
    )

    assert report["created"] == 0
    assert report["updated"] == 1

    roster = await client.get("/v1/employees")
    assert roster.json()["items"][0]["last_name"] == "Vega-Reid"
    assert roster.json()["items"][0]["status"] == "inactive"


async def test_bad_rows_are_reported_but_good_rows_land(
    client: AsyncClient, agency: Agency
) -> None:
    await sign_in(client, agency)

    report = await upload(
        client,
        "first_name,last_name,email,employee_no\n"
        "Marisol,Vega,marisol@example.com,NW-001\n"
        "Dennis,Okafor,not-an-email,NW-002\n"
        "Priya,Raman,priya@example.com,NW-003\n",
    )

    assert report["created"] == 2
    assert report["failed"] == 1
    assert report["errors"][0]["line"] == 3


async def test_an_unknown_role_code_is_a_row_error(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)

    report = await upload(
        client, "first_name,last_name,role_code,employee_no\nMarisol,Vega,SURGEON,NW-001\n"
    )

    assert report["created"] == 0
    assert report["failed"] == 1
    assert "SURGEON" in report["errors"][0]["message"]
