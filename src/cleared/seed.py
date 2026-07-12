"""Load a demo agency.

Run with `make seed`. This is a maintenance command, so it connects as the owner role: it has
to be able to look up the organisation before a tenant is known. The application never does
this.
"""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from uuid6 import uuid7

from cleared.config import get_settings
from cleared.db.tenant import set_tenant
from cleared.domain.models import (
    CredentialType,
    Employee,
    EmployeeCredential,
    JobRole,
    Organization,
    ReminderEvent,
    ReminderRule,
    RoleRequirement,
    User,
)
from cleared.security.passwords import hash_password
from cleared.services import reminders

SLUG = "northwind"
DEMO_PASSWORD = "demo1234!"

FIRST_NAMES = [
    "Marisol",
    "Dennis",
    "Priya",
    "Aaliyah",
    "Tomas",
    "Grace",
    "Emeka",
    "Hannah",
    "Rosa",
    "Kenji",
    "Fatima",
    "Liam",
    "Ingrid",
    "Mateo",
    "Nadia",
    "Owen",
    "Sofia",
    "Rahul",
    "Elena",
    "Marcus",
    "Yara",
    "Peter",
    "Amara",
    "Jonas",
    "Lucia",
    "Samuel",
    "Mei",
    "Diego",
    "Nora",
    "Kwame",
    "Isabel",
    "Adam",
    "Chiara",
    "Victor",
    "Leila",
    "Noah",
    "Beatriz",
    "Henry",
    "Anika",
    "Felix",
]

LAST_NAMES = [
    "Vega",
    "Okafor",
    "Raman",
    "Bennett",
    "Costa",
    "Adeyemi",
    "Nowak",
    "Hughes",
    "Delgado",
    "Tanaka",
    "Haddad",
    "O'Brien",
    "Larsen",
    "Alvarez",
    "Petrova",
    "Kelly",
    "Moretti",
    "Sharma",
    "Kowalski",
    "Reid",
    "Nasser",
    "Lindqvist",
    "Mensah",
    "Weber",
    "Ferreira",
    "Achebe",
    "Chen",
    "Silva",
    "Hansen",
    "Boateng",
    "Ortiz",
    "Levine",
    "Romano",
    "Eze",
    "Karim",
    "Fischer",
    "Duarte",
    "Whitfield",
    "Ivanova",
    "Meyer",
]

CREDENTIAL_TYPES = [
    ("Registered Nurse licence", "RN-LIC", "license", "Massachusetts Board of Nursing", 24),
    ("Practical Nurse licence", "LPN-LIC", "license", "Massachusetts Board of Nursing", 24),
    (
        "Nursing Assistant certification",
        "CNA-CERT",
        "certification",
        "Massachusetts Nurse Aide Registry",
        24,
    ),
    (
        "Home Health Aide certificate",
        "HHA-CERT",
        "certification",
        "Massachusetts Home Care Aide Council",
        24,
    ),
    ("Physical Therapist licence", "PT-LIC", "license", "Massachusetts Board of Allied Health", 24),
    ("CPR / BLS", "CPR", "certification", "American Heart Association", 24),
    ("TB test", "TB", "health", "Any licensed provider", 12),
    ("Background check (CORI)", "CORI", "clearance", "Massachusetts DCJIS", 12),
    ("Dementia care training", "DEMENTIA", "training", "Alzheimer's Association", 24),
]

# Which evidence each role requires, by credential code.
ROLE_REQUIREMENTS = {
    "RN": ["RN-LIC", "CPR", "TB", "CORI"],
    "LPN": ["LPN-LIC", "CPR", "TB", "CORI"],
    "CNA": ["CNA-CERT", "CPR", "TB", "CORI"],
    "HHA": ["HHA-CERT", "CPR", "TB"],
    "PT": ["PT-LIC", "CPR", "CORI"],
}

DEFAULT_RULES = [60, 30, 14, 7, 1]

ROLES = [
    ("Certified Nursing Assistant", "CNA"),
    ("Home Health Aide", "HHA"),
    ("Registered Nurse", "RN"),
    ("Licensed Practical Nurse", "LPN"),
    ("Physical Therapist", "PT"),
]

LOCATIONS = ["Boston", "Worcester", "Springfield", "Lowell"]


async def _seed(session: AsyncSession) -> tuple[Organization, int]:
    organization = await session.scalar(select(Organization).where(Organization.slug == SLUG))

    if organization is None:
        organization = Organization(
            id=uuid7(),
            name="Northwind Home Care",
            slug=SLUG,
            timezone="America/New_York",
        )
        session.add(organization)
        await session.flush()

    await set_tenant(session, organization.id)

    for email, name, role in [
        ("admin@northwind.example", "Dana Whitfield", "admin"),
        ("coordinator@northwind.example", "Rosa Delgado", "coordinator"),
        ("viewer@northwind.example", "Owen Kelly", "viewer"),
    ]:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is None:
            session.add(
                User(
                    id=uuid7(),
                    organization_id=organization.id,
                    email=email,
                    name=name,
                    role=role,
                    password_hash=hash_password(DEMO_PASSWORD),
                )
            )

    for name, code in ROLES:
        existing_role = await session.scalar(select(JobRole).where(JobRole.code == code))
        if existing_role is None:
            session.add(JobRole(id=uuid7(), organization_id=organization.id, name=name, code=code))
    await session.flush()

    roles = list((await session.scalars(select(JobRole).order_by(JobRole.code))).all())
    if roles == []:
        raise RuntimeError("no job roles were created")

    rng = random.Random(42)
    existing_count = len((await session.scalars(select(Employee))).all())
    if existing_count:
        await _seed_credentials(session, organization, roles)
        return organization, existing_count

    today = date.today()
    for index in range(40):
        role = roles[index % len(roles)]
        hired_on = today - timedelta(days=rng.randint(20, 2200))
        status = "active" if index % 11 else "onboarding"
        if index in (7, 23):
            status = "inactive"

        session.add(
            Employee(
                id=uuid7(),
                organization_id=organization.id,
                employee_no=f"NW-{index + 1:03d}",
                first_name=FIRST_NAMES[index % len(FIRST_NAMES)],
                last_name=LAST_NAMES[(index * 7) % len(LAST_NAMES)],
                email=f"employee{index + 1}@northwind.example",
                phone=f"+1 617 555 {1000 + index:04d}",
                job_role_id=role.id,
                location=LOCATIONS[index % len(LOCATIONS)],
                hired_on=hired_on,
                status=status,
            )
        )

    await session.flush()
    await _seed_credentials(session, organization, roles)
    return organization, 40


async def _seed_credentials(
    session: AsyncSession, organization: Organization, roles: list[JobRole]
) -> None:
    """Give each role its requirements, and each employee a realistic mix of evidence."""
    types_by_code: dict[str, CredentialType] = {}
    for name, code, category, authority, months in CREDENTIAL_TYPES:
        credential_type = await session.scalar(
            select(CredentialType).where(CredentialType.code == code)
        )
        if credential_type is None:
            credential_type = CredentialType(
                id=uuid7(),
                organization_id=organization.id,
                name=name,
                code=code,
                category=category,
                issuing_authority=authority,
                validity_months=months,
                requires_document=True,
            )
            session.add(credential_type)
            await session.flush()
        types_by_code[code] = credential_type

    roles_by_code = {role.code: role for role in roles}
    for role_code, required in ROLE_REQUIREMENTS.items():
        role = roles_by_code.get(role_code)
        if role is None:
            continue
        existing = await session.scalar(
            select(RoleRequirement).where(RoleRequirement.job_role_id == role.id).limit(1)
        )
        if existing is not None:
            continue
        for code in required:
            session.add(
                RoleRequirement(
                    id=uuid7(),
                    organization_id=organization.id,
                    job_role_id=role.id,
                    credential_type_id=types_by_code[code].id,
                )
            )
    await session.flush()

    existing_credentials = (await session.scalars(select(EmployeeCredential).limit(1))).first()
    if existing_credentials is not None:
        return

    employees = (await session.scalars(select(Employee).order_by(Employee.employee_no))).all()
    today = date.today()

    for index, employee in enumerate(employees):
        if employee.job_role is None:
            continue
        for code in ROLE_REQUIREMENTS.get(employee.job_role.code, []):
            if index % 13 == 0:
                continue  # nothing recorded at all

            # Each credential gets its own date, so a person's file does not look like one
            # bulk entry with the same day copied down the column.
            spread = len(code) * 11 + index * 7

            if index % 9 == 0:
                expires_on = today - timedelta(days=3 + spread % 18)
                verified = True
            elif index % 7 == 0:
                expires_on = today + timedelta(days=4 + spread % 34)
                verified = True
            elif index % 5 == 0:
                expires_on = today + timedelta(days=90 + spread % 300)
                verified = False
            else:
                expires_on = today + timedelta(days=70 + (index * 13 + spread) % 600)
                verified = True

            issued_on = expires_on - timedelta(days=365)
            session.add(
                EmployeeCredential(
                    id=uuid7(),
                    organization_id=organization.id,
                    employee_id=employee.id,
                    credential_type_id=types_by_code[code].id,
                    identifier=f"{code}-{1000 + index * 7 % 9000}",
                    issued_on=issued_on,
                    expires_on=expires_on,
                    verified_at=datetime.now(UTC) if verified else None,
                    notes=None,
                )
            )

    await session.flush()


async def _seed_reminders(session: AsyncSession, organization: Organization) -> None:
    """Default rules, plus 40 days of outbox history so the screen is not empty."""
    existing = await session.scalar(select(ReminderRule).limit(1))
    if existing is None:
        for days in DEFAULT_RULES:
            session.add(
                ReminderRule(
                    id=uuid7(),
                    organization_id=organization.id,
                    days_before=days,
                    audience="both",
                    channel="email",
                )
            )
        await session.flush()

    sent = await session.scalar(select(ReminderEvent).limit(1))
    if sent is not None:
        return

    today = date.today()
    for offset in range(40, -1, -1):
        await reminders.queue_due(
            session,
            organization_id=organization.id,
            today=today - timedelta(days=offset),
            agency_name=organization.name,
        )

    # The history is written, not sent: mark it as delivered at 09:00 on the day it was due.
    await session.execute(
        sql_text(
            "update reminder_events set status = 'sent', "
            "sent_at = (due_on + time '09:00') at time zone 'UTC' where status = 'queued'"
        )
    )


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(
        settings.migration_database_url or settings.database_url, pool_pre_ping=True
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with factory() as session, session.begin():
            organization, count = await _seed(session)
            await _seed_reminders(session, organization)
    finally:
        await engine.dispose()

    print(f"Seeded {organization.name} with {count} employees.")
    print("Sign in as admin@northwind.example / " + DEMO_PASSWORD)


if __name__ == "__main__":
    asyncio.run(main())
