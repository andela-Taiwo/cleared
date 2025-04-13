"""Run the reminder schedule.

    uv run python -m cleared.jobs.reminders

Cron runs this once a day per deployment. It connects as the owner because it has to visit
every agency; inside each agency it sets the tenant before touching any data, so a bug in the
loop cannot read across agencies.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cleared.config import get_settings
from cleared.db.tenant import set_tenant
from cleared.domain.models import Organization
from cleared.services import reminders


async def run(target_slug: str | None, today: date | None) -> None:
    settings = get_settings()
    engine = create_async_engine(
        settings.migration_database_url or settings.database_url, pool_pre_ping=True
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with factory() as session:
            async with session.begin():
                statement = select(Organization).order_by(Organization.name)
                if target_slug:
                    statement = statement.where(Organization.slug == target_slug)
                organizations = list((await session.scalars(statement)).all())

            for organization in organizations:
                async with session.begin():
                    await set_tenant(session, organization.id)
                    report = await reminders.run(
                        session,
                        organization_id=organization.id,
                        agency_name=organization.name,
                        today=today,
                    )
                print(f"{organization.slug}: generated {report.generated}, sent {report.sent}")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Queue and send credential reminders.")
    parser.add_argument("--org", help="only this organisation slug")
    parser.add_argument("--date", help="pretend today is this date (YYYY-MM-DD)")
    arguments = parser.parse_args()

    as_of = date.fromisoformat(arguments.date) if arguments.date else None
    asyncio.run(run(arguments.org, as_of))


if __name__ == "__main__":
    main()
