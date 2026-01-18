from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tests.support.api import sign_in
from tests.support.seed import Agency
from uuid6 import uuid7

from cleared.domain.models import AuthSession
from cleared.security.sessions import hash_token


async def test_login_sets_an_http_only_cookie(client: AsyncClient, agency: Agency) -> None:
    response = await client.post(
        "/v1/auth/login", json={"email": agency.email, "password": agency.password}
    )

    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie.replace("samesite", "SameSite")


async def test_login_rejects_a_wrong_password(client: AsyncClient, agency: Agency) -> None:
    response = await client.post(
        "/v1/auth/login", json={"email": agency.email, "password": "not-the-password"}
    )

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Email or password is incorrect"


async def test_login_does_not_reveal_unknown_accounts(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )

    assert response.status_code == 401
    assert response.json()["title"] == "Email or password is incorrect"


async def test_login_is_case_insensitive_on_email(client: AsyncClient, agency: Agency) -> None:
    response = await client.post(
        "/v1/auth/login",
        json={"email": agency.email.upper(), "password": agency.password},
    )

    assert response.status_code == 200


async def test_me_requires_a_session(client: AsyncClient) -> None:
    response = await client.get("/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"


async def test_me_returns_the_signed_in_user(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)

    response = await client.get("/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == agency.email
    assert body["organization_id"] == str(agency.organization_id)
    assert body["organization_name"] == "Northwind"


async def test_logout_ends_the_session(client: AsyncClient, agency: Agency) -> None:
    await sign_in(client, agency)

    assert (await client.post("/v1/auth/logout")).status_code == 200
    assert (await client.get("/v1/auth/me")).status_code == 401


async def test_expired_sessions_are_rejected(
    client: AsyncClient, agency: Agency, owner_session: AsyncSession
) -> None:
    token = "expired-token-for-the-test"
    async with owner_session.begin():
        owner_session.add(
            AuthSession(
                id=uuid7(),
                user_id=agency.user_id,
                organization_id=agency.organization_id,
                token_hash=hash_token(token),
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            )
        )

    client.cookies.set("cleared_session", token, domain="test", path="/")
    response = await client.get("/v1/auth/me")

    assert response.status_code == 401


async def test_invalid_email_is_a_problem_document(client: AsyncClient) -> None:
    response = await client.post("/v1/auth/login", json={"email": "not-an-email", "password": "x"})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Request validation failed"


async def test_a_stale_cookie_is_cleared(
    client: AsyncClient, agency: Agency, owner_session: AsyncSession
) -> None:
    await sign_in(client, agency)
    await owner_session.execute(text("delete from sessions"))
    await owner_session.commit()

    response = await client.get("/v1/auth/me")

    assert response.status_code == 401
    assert "cleared_session=" in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]
