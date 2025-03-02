from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.support.api import sign_in
from tests.support.seed import Agency, add_user


async def make_role(client: AsyncClient) -> dict:
    response = await client.post("/v1/roles", json={"code": "CNA", "name": "Nursing Assistant"})
    return response.json()


async def make_type(client: AsyncClient, code: str) -> dict:
    response = await client.post(
        "/v1/credential-types", json={"name": code, "code": code, "category": "health"}
    )
    return response.json()


async def test_replace_and_read_a_role_matrix(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    role = await make_role(client)
    cpr = await make_type(client, "CPR")
    tb = await make_type(client, "TB")

    saved = await client.put(
        f"/v1/requirements/{role['id']}",
        json={"credential_type_ids": [cpr["id"], tb["id"]]},
    )
    assert saved.status_code == 200, saved.text
    assert len(saved.json()["requirements"]) == 2

    matrix = await client.get("/v1/requirements")
    assert {row["credential_type_id"] for row in matrix.json()["requirements"]} == {
        cpr["id"],
        tb["id"],
    }


async def test_replacing_drops_what_is_not_in_the_new_set(
    client: AsyncClient, agency: Agency
) -> None:
    await sign_in(client, agency)
    role = await make_role(client)
    cpr = await make_type(client, "CPR")
    tb = await make_type(client, "TB")
    await client.put(
        f"/v1/requirements/{role['id']}", json={"credential_type_ids": [cpr["id"], tb["id"]]}
    )

    await client.put(f"/v1/requirements/{role['id']}", json={"credential_type_ids": [cpr["id"]]})

    matrix = await client.get("/v1/requirements")
    assert [row["credential_type_id"] for row in matrix.json()["requirements"]] == [cpr["id"]]


async def test_an_unknown_credential_type_is_rejected(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)
    role = await make_role(client)

    response = await client.put(
        f"/v1/requirements/{role['id']}",
        json={"credential_type_ids": ["00000000-0000-0000-0000-000000000000"]},
    )

    assert response.status_code == 422


async def test_an_unknown_role_is_a_404(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)

    response = await client.put(
        "/v1/requirements/00000000-0000-0000-0000-000000000000",
        json={"credential_type_ids": []},
    )

    assert response.status_code == 404


async def test_a_coordinator_cannot_change_requirements(
    client: AsyncClient, agency: Agency, owner_session: AsyncSession
) -> None:
    coordinator = await add_user(owner_session, agency, role="coordinator")
    await sign_in(client, coordinator)
    response = await client.put(
        "/v1/requirements/00000000-0000-0000-0000-000000000000",
        json={"credential_type_ids": []},
    )

    assert response.status_code == 403
