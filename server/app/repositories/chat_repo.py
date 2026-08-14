"""Chat aggregate persistence (sessions + messages)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select

from app.models.chat import ChatMessage, ChatSession
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[ChatSession]):
    model = ChatSession

    async def list_for_user(
        self, user_id: Any, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[ChatSession], int]:
        base = select(ChatSession).where(ChatSession.user_id == user_id)
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = base.order_by(ChatSession.updated_at.desc()).offset(offset).limit(limit)
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows), total

    async def owned_by(self, session_id: Any, user_id: Any) -> ChatSession | None:
        stmt = select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        )
        return await self._scalar_one(stmt)

    async def search(self, user_id: Any, query: str, *, limit: int = 20) -> list[ChatSession]:
        """Find the caller's sessions whose title matches a normalized query."""
        needle = f"%{query.strip().lower()}%"
        stmt = (
            select(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.title.is_not(None),
                func.lower(ChatSession.title).like(needle),
            )
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)


class MessageRepository(BaseRepository[ChatMessage]):
    model = ChatMessage

    async def by_client_request_id(
        self, session_id: Any, client_request_id: uuid.UUID
    ) -> ChatMessage | None:
        stmt = select(ChatMessage).where(
            ChatMessage.session_id == session_id,
            ChatMessage.client_request_id == client_request_id,
        )
        return await self._scalar_one(stmt)

    async def find_reply(self, session_id: Any, after_id: Any) -> ChatMessage | None:
        """First assistant message that follows the given user message."""
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.role == "assistant",
                ChatMessage.id > after_id,
            )
            .order_by(ChatMessage.created_at)
            .limit(1)
        )
        return await self._scalar_one(stmt)

    async def history_window(self, session_id: Any, *, limit: int = 30) -> list[tuple[str, str]]:
        """Most recent turns (role, content) oldest→newest, bounded to `limit`."""
        stmt = (
            select(ChatMessage.role, ChatMessage.content)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(role, content) for role, content in reversed(rows)]

    async def list_for_session(
        self, session_id: Any, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[ChatMessage], int]:
        base = select(ChatMessage).where(ChatMessage.session_id == session_id)
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = base.order_by(ChatMessage.created_at).offset(offset).limit(limit)
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows), total
