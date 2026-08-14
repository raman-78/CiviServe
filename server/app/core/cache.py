"""Application cache (docs/database/08, docs/architecture/16).

Future-ready: production swaps the in-process store for Redis (same ``get/set``
interface). The scheme service uses this for cheap, read-heavy rails
(trending / popular categories) so the request path never recomputes them.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Generic, TypeVar

from app.core.config import get_settings

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Simple thread-safe-ish TTL cache with LRU eviction (single process).

    Keyed by ``key``; entries expire after ``ttl_seconds``. Used as the MVP
    fallback when no Redis client is configured.
    """

    def __init__(self, *, ttl_seconds: int = 300, max_entries: int = 256) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._store: OrderedDict[str, tuple[float, T]] = OrderedDict()

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: T, *, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
        self._store[key] = (time.monotonic() + ttl, value)
        self._store.move_to_end(key)
        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        """Remove every entry whose key starts with ``prefix`` (cache sweep)."""
        for key in [k for k in self._store if k.startswith(prefix)]:
            self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


_cache: TTLCache[Any] | None = None


def get_cache() -> TTLCache[Any]:
    """Application cache singleton (5-minute TTL, 512 entries by default)."""
    global _cache
    if _cache is None:
        settings = get_settings()
        _cache = TTLCache[Any](
            ttl_seconds=settings.scheme_cache_ttl_seconds,
            max_entries=settings.scheme_cache_max_entries,
        )
    return _cache


def invalidate_cache(key: str) -> None:
    get_cache().delete(key)


def invalidate_cache_prefix(prefix: str) -> None:
    """Sweep all keys under a namespace (e.g. ``scheme:`` after an admin save)."""
    get_cache().delete_prefix(prefix)
