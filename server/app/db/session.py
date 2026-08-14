"""Database engine, session factory and FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.base import Base
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

logger = get_logger(__name__)


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        # SQLite (dev/tests) has no connection pool across threads; use NullPool.
        return {"poolclass": NullPool, "future": True}
    return {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "echo": False,
    }


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """Build an async engine from settings (overridable for tests)."""
    url = database_url or get_settings().database_url
    return create_async_engine(url, **(_engine_kwargs(url)))


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def configure_db(database_url: str | None = None) -> None:
    """Point the app at a specific engine/factory (used by tests)."""
    global _engine, _session_factory
    _engine = create_engine(database_url)
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


def set_session_factory(factory: async_sessionmaker[AsyncSession]) -> None:
    """Allow tests to install their own session factory (e.g. sqlite in-memory)."""
    global _session_factory
    _session_factory = factory


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory, _engine
    if _session_factory is None:
        engine = _engine or create_engine()
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Request-scoped database session (FastAPI dependency)."""
    async with get_session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_database(drop: bool = False) -> None:
    """Create schema (dev/tests bootstrap). Production uses Alembic (db/migrations)."""

    engine = get_engine()
    if drop:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ping_database(engine: AsyncEngine | None = None) -> bool:
    """Health probe: SELECT 1."""
    try:
        async with (engine or get_engine()).connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False
