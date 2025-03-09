"""The API application factory.

Importing this module has no side effects beyond reading configuration; `create_app` builds
everything. That keeps tests able to construct an app with different settings.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cleared import __version__
from cleared.api.errors import register_error_handlers
from cleared.api.routes.auth import router as auth_router
from cleared.api.routes.compliance import router as compliance_router
from cleared.api.routes.credential_types import router as credential_types_router
from cleared.api.routes.credentials import router as credentials_router
from cleared.api.routes.employees import router as employees_router
from cleared.api.routes.job_roles import router as roles_router
from cleared.api.routes.requirements import router as requirements_router
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    register_error_handlers(app)
    app.include_router(auth_router, prefix="/v1")
    app.include_router(employees_router, prefix="/v1")
    app.include_router(credential_types_router, prefix="/v1")
    app.include_router(credentials_router, prefix="/v1")
    app.include_router(compliance_router, prefix="/v1")
    app.include_router(roles_router, prefix="/v1")
    app.include_router(requirements_router, prefix="/v1")

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        """Liveness. Deliberately does not touch the database."""
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
