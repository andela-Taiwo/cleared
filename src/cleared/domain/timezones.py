"""Whose day is it?

An agency in Boston and a server in UTC disagree about today for five hours every evening. A
credential that expires today must not read as expired while the coordinator is still at her
desk, so every "today" in the product is the agency's today.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def today_in(timezone: str, *, now: datetime | None = None) -> date:
    moment = now or datetime.now(UTC)
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        zone = UTC
    return moment.astimezone(zone).date()
