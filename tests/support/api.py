"""Small helpers for API tests."""

from __future__ import annotations

from httpx import AsyncClient
from tests.support.seed import Agency


async def sign_in(client: AsyncClient, agency: Agency) -> None:
    response = await client.post(
        "/v1/auth/login", json={"email": agency.email, "password": agency.password}
    )
    assert response.status_code == 200, response.text


def auth_headers() -> dict[str, str]:
    return {"Content-Type": "application/json"}
