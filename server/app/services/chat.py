"""Chat domain service — conversation lifecycle + AI generation pipeline.

Prompt 3 persisted turns; Prompt 7 wires the AI: POSTing a message persists the
user turn (idempotent via ``clientRequestId``), runs retrieval → prompt → LLM →
format, and persists the assistant reply. The stream endpoint yields SSE token
chunks plus a final ``reply`` event carrying the persisted assistant message.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User, UserProfile
from app.repositories.chat_repo import MessageRepository, SessionRepository
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageOut,
    ChatSessionCreate,
)
from app.services.ai.assistant import AIAssistantService
from app.services.translation.service import TranslationService


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.sessions = SessionRepository(session)
        self.messages = MessageRepository(session)
        self.session = session

    async def create_session(self, user: User, payload: ChatSessionCreate) -> ChatSession:
        session = ChatSession(
            user_id=user.id,
            language=payload.language or "en",
            channel=payload.channel or "web",
            title=payload.title,
        )
        await self.sessions.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def list_sessions(
        self, user: User, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[ChatSession], int]:
        offset = (page - 1) * page_size
        items, total = await self.sessions.list_for_user(user.id, offset=offset, limit=page_size)
        return items, total

    async def search_sessions(self, user: User, q: str, *, limit: int = 20) -> list[ChatSession]:
        return await self.sessions.search(user.id, q, limit=limit)

    async def get_session(self, user: User, session_id: str) -> ChatSession:
        session = await self.sessions.owned_by(uuid.UUID(session_id), user.id)
        if session is None:
            raise NotFoundError("Chat session not found.")
        return session

    async def rename_session(self, user: User, session_id: str, title: str) -> ChatSession:
        session = await self.get_session(user, session_id)
        session.title = (title or "").strip()[:160]
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def close_session(self, user: User, session_id: str) -> ChatSession:
        session = await self.get_session(user, session_id)
        session.status = "closed"
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def delete_session(self, user: User, session_id: str) -> None:
        """Archive (soft-delete) a session so the sidebar stops showing it."""
        session = await self.get_session(user, session_id)
        session.status = "archived"
        await self.session.commit()

    async def add_user_message(
        self, user: User, session_id: str, payload: ChatMessageCreate
    ) -> ChatMessage:
        session = await self.get_session(user, session_id)
        if session.status != "active":
            raise NotFoundError("Chat session is not active.")

        client_rid = payload.client_request_id
        if client_rid:
            existing = await self.messages.by_client_request_id(session.id, client_rid)
            if existing:
                return existing

        if session.message_count == 0 and not session.title:
            session.title = self.auto_title(payload.text)

        message = ChatMessage(
            session_id=session.id,
            role="user",
            content_type=payload.content_type or "text",
            content=payload.text,
            content_language=self._detect_language(payload.text, payload.language),
            rendered_text=payload.text,
            client_request_id=client_rid,
            status="complete",
        )
        await self.messages.add(message)

        session.message_count += 1
        session.last_message_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    def auto_title(self, text: str) -> str:
        settings = get_settings()
        max_chars = settings.chat_auto_title_max_chars
        cleaned = " ".join(text.split())
        return cleaned if len(cleaned) <= max_chars else cleaned[:max_chars].rstrip() + "…"

    async def history_messages(self, session_id: Any, *, limit: int = 30) -> list[tuple[str, str]]:
        return await self.messages.history_window(session_id, limit=limit)

    async def list_messages(
        self, user: User, session_id: str, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[ChatMessage], int]:
        session = await self.get_session(user, session_id)
        offset = (page - 1) * page_size
        return await self.messages.list_for_session(session.id, offset=offset, limit=page_size)

    # ------------------------------------------------------------ AI generation --

    async def generate_reply(
        self,
        user: User,
        profile: UserProfile | None,
        session_id: str,
        payload: ChatMessageCreate,
    ) -> ChatMessage:
        """Persist a user turn, run the pipeline, persist + return the reply."""
        session = await self.get_session(user, session_id)
        user_message = await self.add_user_message(user, session_id, payload)
        existing = await self.messages.find_reply(session.id, user_message.id)
        if existing is not None:
            return existing

        assistant = AIAssistantService(self.session)
        request = await self._build_request(assistant, user, profile, session.id, payload)
        await self._sync_session_language(session, request.language)
        result = await self._resolve(assistant, request, payload)
        return await self._persist_assistant(session, request, result)

    def stream_reply(
        self,
        user: User,
        profile: UserProfile | None,
        session_id: str,
        payload: ChatMessageCreate,
    ) -> AsyncIterator[tuple[str, str]]:
        """Async generator of ``(event, data)`` pairs for the SSE endpoint."""
        return self._stream_reply(user, profile, session_id, payload)

    async def _stream_reply(
        self,
        user: User,
        profile: UserProfile | None,
        session_id: str,
        payload: ChatMessageCreate,
    ) -> AsyncIterator[tuple[str, str]]:
        session = await self.get_session(user, session_id)
        await self.add_user_message(user, session_id, payload)
        assistant = AIAssistantService(self.session)
        request = await self._build_request(assistant, user, profile, session.id, payload)
        await self._sync_session_language(session, request.language)

        buffer: list[str] = []
        async for chunk in assistant.stream_answer(request):
            if chunk == "__end__":
                break
            buffer.append(chunk)
            yield "token", chunk

        raw = "".join(buffer)
        result = await self._resolve(assistant, request, payload, raw=raw)
        reply = await self._persist_assistant(session, request, result)
        yield "reply", ChatMessageOut.model_validate(reply).model_dump_json(by_alias=True)

    async def _build_request(
        self,
        assistant: AIAssistantService,
        user: User,
        profile: UserProfile | None,
        session_id: Any,
        payload: ChatMessageCreate,
    ) -> Any:
        history = await self.history_messages(session_id)
        return await assistant.build_request(
            query=payload.text,
            user=user,
            profile=profile,
            history=history,
            language=payload.language,
        )

    async def _sync_session_language(self, session: ChatSession, language: str) -> None:
        """Track the effective language on the session so the UI reflects it.

        Explicitly does *not* recreate the conversation: switching languages
        keeps the same session and history, only the metadata column is updated.
        """
        if session.language != language:
            session.language = language

    def _detect_language(self, text: str, declared: str) -> str:
        """The stored ``content_language`` reflects script detection, not just
        the client-declared code (so a Tamil message typed in an "en" session is
        still tagged ``ta``)."""
        return TranslationService().detect(text, preferred=declared).language

    async def _resolve(
        self,
        assistant: AIAssistantService,
        request: Any,
        payload: ChatMessageCreate,
        *,
        raw: str | None = None,
    ) -> dict[str, Any]:
        """Run the pipeline to a client-ready result (reused by both paths)."""
        if raw is None:
            raw = await assistant.provider.complete(request)
        return await assistant.resolve(raw, request)

    async def _persist_assistant(
        self,
        session: ChatSession,
        request: Any,
        result: dict[str, Any],
    ) -> ChatMessage:
        content = result["answer"] or "I couldn't find a suitable answer just now."
        message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content_type="text",
            content=content,
            content_language=request.language,
            rendered_text=content,
            intent=result["intent"],
            payload=result["payload"],
            status="complete",
        )
        await self.messages.add(message)
        session.message_count += 1
        session.last_message_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(message)
        return message
