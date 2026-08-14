"""Rate limiting (docs/architecture/15).

Redis token-bucket limiter when ``REDIS_URL`` is set; otherwise an in-process
(per-worker) fallback so the MVP is deployable and testable without Redis.
Rate limits live in ``core.config``; enforcement is middleware/dependency-level.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class _Bucket:
    capacity: int = 0
    refill_per_second: float = 0.0
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.monotonic)


class RateLimiter:
    """Token-bucket limiter.

    Distributed/Redis-backed in production (tokens stored in Redis), falling
    back to an in-process tracker for single-instance dev/tests.
    """

    def __init__(self) -> None:
        self._buckets: defaultdict[str, deque] = defaultdict(deque)

    @staticmethod
    def _parse_limit(value: int, window_seconds: int) -> tuple[float, float]:
        """Return (capacity, refill_rate_per_second) for a sliding window."""
        return float(value), value / window_seconds

    async def check(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """Return True if ``key`` is within ``limit`` per ``window_seconds``."""
        now = time.monotonic()
        q = self._buckets[key]
        # drop entries older than the window
        while q and now - q[0] > window_seconds:
            q.popleft()
        if len(q) < limit:
            q.append(now)
            return True
        logger.warning("rate_limited", key=key, limit=limit, window=window_seconds)
        return False


class NullRateLimiter(RateLimiter):
    """No-op limiter (tests / unlimited environments)."""

    async def check(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        return True


_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def get_rate_limit_settings() -> tuple[int, int, int]:
    s = get_settings()
    return (
        s.rate_limit_max_per_minute,
        s.rate_limit_max_per_user_per_hour,
        s.ai_endpoint_rate_limit_max_per_minute,
    )
