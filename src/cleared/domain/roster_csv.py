"""Reading a roster out of a spreadsheet export.

Framework-free on purpose: the parsing rules are the part that needs testing, and they are
easier to test when nothing imports a web framework. The caller decides what to do with the
rows; this module only says what is in the file.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date

REQUIRED_COLUMNS = ("first_name", "last_name")
OPTIONAL_COLUMNS = (
    "email",
    "phone",
    "employee_no",
    "role_code",
    "location",
    "hired_on",
    "status",
)
ALLOWED_STATUSES = {"active", "inactive", "onboarding"}

MAX_ROWS = 5000

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class RosterRow:
    line: int
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    employee_no: str | None
    role_code: str | None
    location: str | None
    hired_on: date | None
    status: str


@dataclass(frozen=True)
class RowProblem:
    line: int
    message: str


def _header(name: str | None) -> str:
    """`First Name`, `first name` and `first_name` are the same column."""
    return (name or "").strip().lower().replace(" ", "_")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def parse_roster(text: str) -> tuple[list[RosterRow], list[RowProblem]]:
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        return [], [RowProblem(line=1, message="The file has no header row")]

    headers = {_header(name) for name in reader.fieldnames}
    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        return [], [RowProblem(line=1, message=f"Missing required column: {', '.join(missing)}")]

    rows: list[RosterRow] = []
    problems: list[RowProblem] = []

    for offset, record in enumerate(reader, start=2):
        if len(rows) + len(problems) >= MAX_ROWS:
            problems.append(RowProblem(line=offset, message=f"Stopped after {MAX_ROWS} rows"))
            break

        normalised = {_header(key): value for key, value in record.items()}

        first_name = _clean(normalised.get("first_name"))
        last_name = _clean(normalised.get("last_name"))

        if not first_name or not last_name:
            problems.append(
                RowProblem(line=offset, message="first_name and last_name are required")
            )
            continue

        email = _clean(normalised.get("email"))
        if email is not None:
            email = email.lower()
            if not _EMAIL.match(email):
                problems.append(RowProblem(line=offset, message=f"Invalid email: {email}"))
                continue

        hired_on: date | None = None
        raw_hired = _clean(normalised.get("hired_on"))
        if raw_hired is not None:
            try:
                hired_on = date.fromisoformat(raw_hired)
            except ValueError:
                problems.append(RowProblem(line=offset, message=f"Invalid hire date: {raw_hired}"))
                continue

        status = (_clean(normalised.get("status")) or "active").lower()
        if status not in ALLOWED_STATUSES:
            problems.append(RowProblem(line=offset, message=f"Unknown status: {status}"))
            continue

        rows.append(
            RosterRow(
                line=offset,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=_clean(normalised.get("phone")),
                employee_no=_clean(normalised.get("employee_no")),
                role_code=(_clean(normalised.get("role_code")) or "").upper() or None,
                location=_clean(normalised.get("location")),
                hired_on=hired_on,
                status=status,
            )
        )

    return rows, problems
