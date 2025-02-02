"""Load a demo agency.

Run with `make seed`. This is a maintenance command, so it connects as the owner role: it has
to be able to look up the organisation before a tenant is known. The application never does
this.
"""

from __future__ import annotations

import asyncio
import random
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from uuid6 import uuid7

from cleared.config import get_settings
from cleared.db.tenant import set_tenant
from cleared.domain.models import Employee, JobRole, Organization, User
from cleared.security.passwords import hash_password

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

    roles = (await session.scalars(select(JobRole).order_by(JobRole.code))).all()
    if roles == []:
        raise RuntimeError("no job roles were created")

    rng = random.Random(42)
    existing_count = len((await session.scalars(select(Employee))).all())
    if existing_count:
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
    return organization, 40


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(
        settings.migration_database_url or settings.database_url, pool_pre_ping=True
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with factory() as session, session.begin():
            organization, count = await _seed(session)
    finally:
        await engine.dispose()

    print(f"Seeded {organization.name} with {count} employees.")
    print("Sign in as admin@northwind.example / " + DEMO_PASSWORD)


if __name__ == "__main__":
    asyncio.run(main())
