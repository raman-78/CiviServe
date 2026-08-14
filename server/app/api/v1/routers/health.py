"""Health + metrics endpoints (public, no auth)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.db.session import ping_database

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> Response:
    """Readiness probe — includes DB connectivity."""
    ok = await ping_database()
    body = json.dumps(
        {"status": "ready" if ok else "not_ready", "database": "ok" if ok else "error"}
    )
    return Response(content=body, media_type="application/json", status_code=200 if ok else 503)


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
