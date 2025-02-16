"""Errors as RFC 9457 Problem Details.

Every error response has the same shape and the same content type, so the web app has one
error path rather than a guess per endpoint.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class Problem(Exception):
    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str | None = None,
        *,
        type_: str = "about:blank",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(title)
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type = type_
        self.headers = headers


def _response(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str | None,
    type_: str,
    extra: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status,
        "instance": request.url.path,
    }
    if detail is not None:
        body["detail"] = detail
    if extra:
        body.update(extra)
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
        headers=headers,
    )


async def problem_handler(request: Request, exc: Problem) -> JSONResponse:
    return _response(
        request,
        status=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        type_=exc.type,
        headers=exc.headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _response(
        request,
        status=exc.status_code,
        title=str(exc.detail),
        detail=None,
        type_="about:blank",
        headers=dict(exc.headers or {}),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _response(
        request,
        status=422,
        title="Request validation failed",
        detail="One or more fields are invalid.",
        type_="https://cleared.example/errors/validation",
        extra={
            "errors": [
                {
                    "loc": list(error.get("loc", ())),
                    "msg": str(error.get("msg", "")),
                    "type": str(error.get("type", "")),
                }
                for error in exc.errors()
            ]
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Problem, problem_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
