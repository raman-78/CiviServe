"""Generic CRUD base for repositories."""

from __future__ import annotations

from typing import Any, Generic, TypeVar, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Thin persistence wrapper over an async session."""

    model: type[ModelT]
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: Any) -> ModelT | None:
        return await self.session.get(self.model, id)

    async def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
        await self.session.flush()

    async def _scalar_one(self, stmt: Any) -> ModelT | None:
        result = await self.session.execute(stmt)
        return cast(ModelT | None, result.scalar_one_or_none())
