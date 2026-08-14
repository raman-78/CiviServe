"""HTTP middleware: request-id correlation + access logging.

Assigns ``X-Request-Id`` (reusing the client's if provided), binds it to the
request state and the structlog context, and emits one structured access-log
event per request (docs/architecture/14).
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, set_request_id

logger = get_logger("access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Request-scoped requestId + access log."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        set_request_id(rid)
        request.state.request_id = rid

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-Id"] = rid
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response
