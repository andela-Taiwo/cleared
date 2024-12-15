"""Sign-in and session lifecycle."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from cleared.config import get_settings
from cleared.domain.models import AuthSession
from cleared.security.passwords import hash_password, verify_password
from cleared.security.sessions import hash_token, new_token

settings = get_settings()

# Verifying against a real hash when the account does not exist keeps the failure path roughly
# as expensive as the success path, so response time does not reveal which emails exist.
_DUMMY_HASH = hash_password("cleared-dummy-password-never-used")


class InvalidCredentials(Exception):
    pass


class AccountDisabled(Exception):
    pass


@dataclass(frozen=True)
class Account:
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: str


async def authenticate(session: AsyncSession, email: str, password: str) -> Account:
    async with session.begin():
        row = (
            (
                await session.execute(
                    text(
                        "select user_id, organization_id, password_hash, is_active, role "
                        "from cleared_auth_lookup(:email)"
                    ),
                    {"email": email.strip().lower()},
                )
            )
            .mappings()
            .first()
        )

    if row is None:
        verify_password(password, _DUMMY_HASH)
        raise InvalidCredentials

    if not verify_password(password, row["password_hash"]):
        raise InvalidCredentials

    if not row["is_active"]:
        raise AccountDisabled

    return Account(user_id=row["user_id"], organization_id=row["organization_id"], role=row["role"])


async def start_session(
    session: AsyncSession,
    *,
    account: Account,
    user_agent: str | None,
    ip: str | None,
) -> str:
    """Create a session row and return the token to put in the cookie."""
    token = new_token()
    expires_at = datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)

    async with session.begin():
        session.add(
            AuthSession(
                id=uuid7(),
                user_id=account.user_id,
                organization_id=account.organization_id,
                token_hash=hash_token(token),
                expires_at=expires_at,
                user_agent=(user_agent or "")[:400] or None,
                ip=ip,
            )
        )

    return token


async def end_session(session: AsyncSession, token: str) -> None:
    async with session.begin():
        await session.execute(
            delete(AuthSession).where(AuthSession.token_hash == hash_token(token))
        )
