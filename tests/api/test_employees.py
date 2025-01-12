from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.support.api import sign_in
from tests.support.seed import Agency, add_user, create_agency


async def make_role(
    client: AsyncClient, code: str = "CNA", name: str = "Certified Nursing Assistant"
) -> dict:
    response = await client.post("/v1/roles", json={"code": code, "name": name})
    assert response.status_code == 201, response.text
    return response.json()


async def add_employee(client: AsyncClient, **overrides: object) -> dict:
    payload = {
        "first_name": "Marisol",
        "last_name": "Vega",
        "email": "marisol.vega@northwind.example",
        "employee_no": "NW-001",
        "status": "active",
        **overrides,
    }
    response = await client.post("/v1/employees", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_create_and_read_an_employee(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    role = await make_role(client)

    created = await add_employee(client, job_role_id=role["id"])

    assert created["first_name"] == "Marisol"
    assert created["job_role"]["code"] == "CNA"

    response = await client.get(f"/v1/employees/{created['id']}")
    assert response.status_code == 200
    assert response.json()["employee_no"] == "NW-001"


async def test_update_an_employee(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    created = await add_employee(client)

    response = await client.patch(
        f"/v1/employees/{created['id']}", json={"status": "inactive", "phone": "+1 555 0100"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    assert response.json()["phone"] == "+1 555 0100"


async def test_the_roster_is_sorted_by_last_name(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    for last_name in ["Zimmer", "Alvarez", "Okafor"]:
        await add_employee(client, last_name=last_name, employee_no=f"NW-{last_name}", email=None)

    response = await client.get("/v1/employees")

    assert [row["last_name"] for row in response.json()["items"]] == [
        "Alvarez",
        "Okafor",
        "Zimmer",
    ]


async def test_the_roster_paginates(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    for index in range(5):
        await add_employee(
            client, last_name=f"Person{index}", employee_no=f"NW-{index:03d}", email=None
        )

    first = await client.get("/v1/employees", params={"limit": 2})
    body = first.json()
    assert len(body["items"]) == 2
    assert body["total"] == 5
    assert body["next_cursor"]

    second = await client.get("/v1/employees", params={"limit": 2, "cursor": body["next_cursor"]})
    second_body = second.json()
    assert len(second_body["items"]) == 2
    assert second_body["items"][0]["last_name"] != body["items"][0]["last_name"]


async def test_filters_by_status_and_role(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    nurse = await make_role(client, code="RN", name="Registered Nurse")
    await add_employee(client, last_name="Active", email=None, job_role_id=nurse["id"])
    await add_employee(
        client, last_name="Gone", employee_no="NW-002", status="inactive", email=None
    )

    by_status = await client.get("/v1/employees", params={"status": "inactive"})
    assert [row["last_name"] for row in by_status.json()["items"]] == ["Gone"]

    by_role = await client.get("/v1/employees", params={"role_id": nurse["id"]})
    assert [row["last_name"] for row in by_role.json()["items"]] == ["Active"]


async def test_an_invalid_cursor_is_a_400(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)

    response = await client.get("/v1/employees", params={"cursor": "not-a-cursor"})

    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"


async def test_a_viewer_cannot_change_the_roster(
    client: AsyncClient, agency: Agency, owner_session: AsyncSession
) -> None:
    viewer = await add_user(owner_session, agency, role="viewer")
    await sign_in(client, viewer)

    response = await client.post("/v1/employees", json={"first_name": "No", "last_name": "Chance"})

    assert response.status_code == 403


async def test_another_tenant_gets_a_404(
    client: AsyncClient, agency: Agency, owner_session: AsyncSession
) -> None:
    other = await create_agency(owner_session, name="beacon")
    await sign_in(client, agency)
    created = await add_employee(client)

    response = await client.get(f"/v1/employees/{created['id']}")

    assert response.status_code == 200

    await sign_in(client, other)
    response = await client.get(f"/v1/employees/{created['id']}")
    assert response.status_code == 404


async def test_a_duplicate_employee_number_is_a_409(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    await add_employee(client)

    response = await client.post(
        "/v1/employees",
        json={"first_name": "Other", "last_name": "Person", "employee_no": "NW-001"},
    )

    assert response.status_code == 409


async def test_an_unknown_job_role_is_rejected(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)

    response = await client.post(
        "/v1/employees",
        json={
            "first_name": "No",
            "last_name": "Role",
            "job_role_id": "00000000-0000-0000-0000-000000000000",
        },
    )

    assert response.status_code == 422


async def test_roles_are_unique_by_code(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    await make_role(client)

    response = await client.post("/v1/roles", json={"code": "CNA", "name": "Duplicate"})

    assert response.status_code == 409
