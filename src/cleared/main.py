"""The API application factory.

Importing this module has no side effects beyond reading configuration; `create_app` builds
everything. That keeps tests able to construct an app with different settings.
"""

from __future__ import annotations

from fastapi import FastAPI

from cleared import __version__
from cleared.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Cleared",
        version=__version__,
        description="Credential compliance for home care and medical staffing agencies.",
        docs_url=None if settings.is_prod else "/docs",
        openapi_url=None if settings.is_prod else "/openapi.json",
    )

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        """Liveness. Deliberately does not touch the database."""
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
