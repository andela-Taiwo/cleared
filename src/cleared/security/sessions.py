"""Session tokens.

The cookie carries a random token; the database stores only its SHA-256. A leaked database
therefore does not hand out working sessions, and lookup stays an index hit on an exact hash.
"""

from __future__ import annotations

import hashlib
import secrets

TOKEN_BYTES = 32


def new_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
