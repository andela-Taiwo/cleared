from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.support.api import sign_in
from tests.support.seed import Agency, add_user

CPR = {
    "name": "CPR / BLS",
    "code": "CPR",
    "category": "certification",
    "issuing_authority": "American Heart Association",
    "validity_months": 24,
}


async def test_create_and_list_credential_types(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)

    created = await client.post("/v1/credential-types", json=CPR)
    assert created.status_code == 201, created.text
    assert created.json()["code"] == "CPR"
    assert created.json()["validity_months"] == 24

    listed = await client.get("/v1/credential-types")
    assert [row["code"] for row in listed.json()] == ["CPR"]


async def test_codes_are_unique(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    await client.post("/v1/credential-types", json=CPR)

    duplicate = await client.post("/v1/credential-types", json={**CPR, "name": "CPR again"})

    assert duplicate.status_code == 409


async def test_an_unknown_category_is_rejected(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)

    response = await client.post("/v1/credential-types", json={**CPR, "category": "vibes"})

    assert response.status_code == 422


async def test_a_coordinator_cannot_change_the_catalogue(
    client: AsyncClient, agency: Agency, owner_session: AsyncSession
) -> None:
    coordinator = await add_user(owner_session, agency, role="coordinator")
    await sign_in(client, coordinator)

    response = await client.post("/v1/credential-types", json=CPR)

    assert response.status_code == 403


async def test_updating_a_type(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    created = (await client.post("/v1/credential-types", json=CPR)).json()

    response = await client.patch(
        f"/v1/credential-types/{created['id']}", json={"validity_months": 12}
    )

    assert response.status_code == 200
    assert response.json()["validity_months"] == 12
    assert response.json()["name"] == "CPR / BLS"
