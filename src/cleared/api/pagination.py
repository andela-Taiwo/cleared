"""Opaque cursors for keyset pagination.

A cursor is base64url(JSON list of the sort key values of the last row seen). It is opaque to
clients, so the sort key can change without breaking them — but it is not a security boundary,
so the server validates it rather than trusting it.
"""

from __future__ import annotations

import base64
import json


def encode_cursor(values: list[str]) -> str:
    raw = json.dumps(values, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(token: str, *, length: int) -> list[str]:
    padded = token + "=" * (-len(token) % 4)
    try:
        values = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid cursor") from exc

    if not isinstance(values, list) or len(values) != length:
        raise ValueError("invalid cursor")
    if not all(isinstance(value, str) for value in values):
        raise ValueError("invalid cursor")
    return values
