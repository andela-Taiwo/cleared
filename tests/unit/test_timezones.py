from __future__ import annotations

from datetime import UTC, date, datetime

from cleared.domain.timezones import today_in

# 02:30 UTC on 1 March is still 28 February in New York.
LATE_UTC = datetime(2026, 3, 1, 2, 30, tzinfo=UTC)


def test_an_agency_behind_utc_is_still_on_yesterday() -> None:
    assert today_in("America/New_York", now=LATE_UTC) == date(2026, 2, 28)


def test_an_agency_ahead_of_utc_is_already_on_tomorrow() -> None:
    assert today_in("Asia/Tokyo", now=LATE_UTC) == date(2026, 3, 1)


def test_midday_is_the_same_day_everywhere() -> None:
    midday = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    assert today_in("America/Los_Angeles", now=midday) == date(2026, 3, 1)


def test_an_unknown_zone_falls_back_to_utc() -> None:
    assert today_in("Mars/Olympus_Mons", now=LATE_UTC) == date(2026, 3, 1)
