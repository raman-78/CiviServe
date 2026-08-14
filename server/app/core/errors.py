"""Domain error hierarchy + global exception handlers (docs/architecture/13).

Services raise :class:`AppError` subclasses with machine-readable ``code`` and
a user-safe ``message``; routers/services never deal with HTTP directly. The
single global handler maps them to the ``{error:{code,message,details,requestId}}``
envelope.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, get_request_id

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for all domain errors."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "Something went wrong.",
        *,
        code: str | None = None,
        details: dict[str, Any] | list[Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class AuthenticationError(AppError):
    status_code = 401
    code = "AUTH_UNAUTHENTICATED"


class ForbiddenError(AppError):
    status_code = 403
    code = "AUTH_FORBIDDEN"


class ValidationError_(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class RateLimitError(AppError):
    status_code = 429
    code = "RATE_LIMITED"

    def __init__(
        self, message: str = "Too many requests.", *, retry_after: int = 60, **kw: Any
    ) -> None:
        super().__init__(message, **kw)
        self.retry_after = retry_after


class ExternalServiceError(AppError):
    status_code = 502
    code = "EXTERNAL_SERVICE"


class InternalError(AppError):
    status_code = 500
    code = "INTERNAL_ERROR"


def _envelope(
    request: Request,
    code: str,
    message: str,
    details: dict[str, Any] | list[Any] | None = None,
    status_code: int = 500,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    rid = get_request_id() or getattr(request.state, "request_id", "")
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "requestId": rid,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global handlers to the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        headers = None
        if isinstance(exc, RateLimitError):
            headers = {"Retry-After": str(exc.retry_after)}
        return _envelope(
            request,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            status_code=exc.status_code,
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError | ValidationError
    ) -> JSONResponse:
        if isinstance(exc, RequestValidationError):
            details = list(exc.errors())
        else:
            details = [
                {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()
            ]
        return _envelope(
            request,
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            details=details,
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # 401/403 from auth/HTTP use the AUTH_* namespace per docs/architecture/15.
        if exc.status_code == 401:
            code, message = "AUTH_UNAUTHENTICATED", "Authentication required."
        elif exc.status_code == 403:
            code, message = "AUTH_FORBIDDEN", "You do not have permission."
        elif exc.status_code == 404:
            code, message = "NOT_FOUND", "Resource not found."
        elif exc.status_code == 405:
            code, message = "METHOD_NOT_ALLOWED", "Method not allowed."
        else:
            code, message = "HTTP_ERROR", str(exc.detail or exc.status_code)
        return _envelope(request, code=code, message=message, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", exc_info=exc, path=request.url.path)
        return _envelope(
            request,
            code="INTERNAL_ERROR",
            message="Internal server error.",
            status_code=500,
        )
