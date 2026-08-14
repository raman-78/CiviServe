"""System-health probes for the admin dashboard (Prompt 15).

Checks each subsystem the dashboard depends on and persists a snapshot per
component. All probes are non-destructive; external providers that are not
configured report ``down`` (config missing) rather than lying about availability.
"""

from __future__ import annotations

import time
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_engine
from app.models.admin import SystemHealthCheck
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


async def _probe(name: str, check: Any, checked_by: Any, session: AsyncSession) -> dict[str, Any]:
    start = time.monotonic()
    status = "ok"
    message: str | None = None
    try:
        await check()
    except Exception as exc:  # noqa: BLE001 — health probes swallow everything
        status = "down"
        message = str(exc)[:280]
        logger.warning("health.probe_failed", component=name, error=str(exc))
    latency_ms = int((time.monotonic() - start) * 1000)
    session.add(
        SystemHealthCheck(
            component=name,
            status=status,
            latency_ms=latency_ms,
            message=message,
            checked_by=checked_by,
        )
    )
    return {
        "component": name,
        "status": status,
        "latencyMs": latency_ms,
        "message": message,
    }


async def _database_ok() -> None:
    async with (get_engine()).connect() as conn:
        await conn.execute(text("SELECT 1"))


async def _settings_ok() -> None:
    get_settings()


async def _llm_ok() -> None:
    from app.services.ai.providers import get_llm_provider

    provider = get_llm_provider()
    if provider is None:
        raise RuntimeError("AI provider not configured (Gemini key missing).")


async def _translation_ok() -> None:
    settings = get_settings()
    if settings.translation_provider == "identity" and not settings.google_translate_api_key:
        raise RuntimeError("Translation provider not configured.")


async def _search_ok(session: AsyncSession) -> None:
    from app.services.scheme import SchemeService

    count = SchemeService(session)
    # Cheap bounded call to confirm the catalog rail works end-to-end.
    _ = await count.repo.published_count()


async def _docs_ok() -> None:
    settings = get_settings()
    if not settings.document_storage_dir:
        raise RuntimeError("Document storage not configured.")


async def _speech_ok() -> None:
    settings = get_settings()
    if not settings.google_speech_language_hint:
        raise RuntimeError("Speech not configured.")


async def run_health_probe(session: AsyncSession, *, checked_by: Any) -> dict[str, Any]:
    """Probe every component and return the report + persist snapshots."""
    checks = [
        ("database", _database_ok),
        ("config", _settings_ok),
        ("ai", _llm_ok),
        ("translation", _translation_ok),
        ("search", lambda: _search_ok(session)),
        ("documents", _docs_ok),
        ("speech", _speech_ok),
    ]
    results: list[dict[str, Any]] = []
    for name, fn in checks:
        results.append(await _probe(name, fn, checked_by, session))
    await session.commit()
    return {"checks": results, "overall": _overall(results)}


def _overall(results: list[dict[str, Any]]) -> str:
    if any(r["status"] == "down" for r in results):
        return "degraded"
    return "ok"
