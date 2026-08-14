"""FastAPI dependencies: db session, auth, rate limiter."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import RateLimitError
from app.core.rate_limit import RateLimiter, get_rate_limiter
from app.db.session import get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async session (commit handled by services)."""
    async with get_session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_rate_limiter_dep() -> RateLimiter:
    return get_rate_limiter()


async def rate_limit_search(request: Request) -> None:
    """Per-IP token budget for the noisy search/suggestion endpoints."""
    limiter = get_rate_limiter()
    limit = get_settings().scheme_search_rate_limit_per_minute
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = (forwarded.split(",")[0].strip() if forwarded else None) or (
        request.client.host if request.client else "unknown"
    )
    if not await limiter.check(f"search:{client_ip}", limit, window_seconds=60):
        raise RateLimitError(
            "Too many search requests. Please try again in a minute.", retry_after=60
        )


async def rate_limit_chat(request: Request) -> None:
    """Per-user token budget for the (costly) AI generation endpoints."""
    limiter = get_rate_limiter()
    limit = get_settings().ai_endpoint_rate_limit_max_per_minute
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = (forwarded.split(",")[0].strip() if forwarded else None) or (
        request.client.host if request.client else "unknown"
    )
    if not await limiter.check(f"chat:{client_ip}", limit, window_seconds=60):
        raise RateLimitError(
            "Too many messages. Please wait a moment and try again.", retry_after=60
        )
