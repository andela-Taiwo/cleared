from __future__ import annotations

from datetime import date, timedelta

from httpx import AsyncClient
from tests.support.api import sign_in
from tests.support.seed import Agency


async def make_type(client: AsyncClient, code: str = "CPR") -> dict:
    response = await client.post(
        "/v1/credential-types",
        json={"name": code, "code": code, "category": "certification", "validity_months": 24},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def make_employee(client: AsyncClient) -> dict:
    response = await client.post(
        "/v1/employees", json={"first_name": "Marisol", "last_name": "Vega"}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_record_a_credential(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    credential_type = await make_type(client)
    employee = await make_employee(client)

    response = await client.post(
        f"/v1/employees/{employee['id']}/credentials",
        json={
            "credential_type_id": credential_type["id"],
            "identifier": "AHA-99321",
            "issued_on": "2024-06-01",
            "expires_on": "2026-06-01",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["credential_type"]["code"] == "CPR"
    assert body["expires_on"] == "2026-06-01"
    assert body["verified_at"] is None


async def test_dates_must_be_ordered(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    credential_type = await make_type(client)
    employee = await make_employee(client)

    response = await client.post(
        f"/v1/employees/{employee['id']}/credentials",
        json={
            "credential_type_id": credential_type["id"],
            "issued_on": "2026-01-01",
            "expires_on": "2025-01-01",
        },
    )

    assert response.status_code == 422


async def test_verifying_a_credential(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    credential_type = await make_type(client)
    employee = await make_employee(client)
    created = (
        await client.post(
            f"/v1/employees/{employee['id']}/credentials",
            json={"credential_type_id": credential_type["id"]},
        )
    ).json()

    response = await client.post(f"/v1/credentials/{created['id']}/verify")

    assert response.status_code == 200
    assert response.json()["verified_at"] is not None


async def test_the_register_is_sorted_by_expiry(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    credential_type = await make_type(client)
    employee = await make_employee(client)
    today = date.today()

    for offset in [40, 5, 400]:
        await client.post(
            f"/v1/employees/{employee['id']}/credentials",
            json={
                "credential_type_id": credential_type["id"],
                "expires_on": (today + timedelta(days=offset)).isoformat(),
            },
        )

    response = await client.get("/v1/credentials")
    expiries = [row["expires_on"] for row in response.json()]

    assert expiries == sorted(expiries)


async def test_deleting_a_credential(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    credential_type = await make_type(client)
    employee = await make_employee(client)
    created = (
        await client.post(
            f"/v1/employees/{employee['id']}/credentials",
            json={"credential_type_id": credential_type["id"]},
        )
    ).json()

    assert (await client.delete(f"/v1/credentials/{created['id']}")).status_code == 204
    assert (await client.get(f"/v1/employees/{employee['id']}/credentials")).json() == []


async def test_an_unknown_employee_is_a_404(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    credential_type = await make_type(client)

    response = await client.post(
        "/v1/employees/00000000-0000-0000-0000-000000000000/credentials",
        json={"credential_type_id": credential_type["id"]},
    )

    assert response.status_code == 404
