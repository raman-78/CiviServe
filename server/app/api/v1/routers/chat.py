"""Chat endpoints: sessions (CRUD/search) + messages (generate/stream/SSE).

Authenticated. POSTing a message runs the grounded AI pipeline and returns the
persisted assistant reply; ``.../messages/stream`` is the SSE transport of the
same turn (token events, then a ``reply`` event).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db, rate_limit_chat
from app.core.security import AuthPrincipal, get_current_user
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionOut,
    ChatSessionUpdate,
)
from app.schemas.common import Paginated
from app.services.chat import ChatService
from app.services.user import UserService

router = APIRouter(tags=["chat"], prefix="/chat")

DbDep = Annotated[AsyncSession, Depends(get_db)]
PrincipalDep = Annotated[AuthPrincipal, Depends(get_current_user)]


async def _user_with_profile(db: AsyncSession, principal: AuthPrincipal) -> tuple:
    user_service = UserService(db)
    user = await user_service.get_or_create_by_firebase(principal.uid)
    _user, profile = await user_service.get_profile(user)
    return user, profile


@router.post("/sessions", response_model=ChatSessionOut, status_code=201)
async def create_session(
    payload: ChatSessionCreate,
    principal: PrincipalDep,
    db: DbDep,
) -> ChatSessionOut:
    """Start a new conversation."""
    user, _ = await _user_with_profile(db, principal)
    session = await ChatService(db).create_session(user, payload)
    return ChatSessionOut.model_validate(session)


@router.get("/sessions", response_model=Paginated[ChatSessionOut])
async def list_sessions(
    principal: PrincipalDep,
    db: DbDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Paginated[ChatSessionOut]:
    """List the caller's sessions, most-recently-updated first."""
    user, _ = await _user_with_profile(db, principal)
    items, total = await ChatService(db).list_sessions(user, page=page, page_size=page_size)
    return Paginated(
        items=[ChatSessionOut.model_validate(s) for s in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/sessions/search", response_model=list[ChatSessionOut])
async def search_sessions(
    principal: PrincipalDep,
    db: DbDep,
    q: str = Query(..., min_length=1, max_length=120),
) -> list[ChatSessionOut]:
    """Find the caller's sessions whose title matches ``q``."""
    user, _ = await _user_with_profile(db, principal)
    items = await ChatService(db).search_sessions(user, q)
    return [ChatSessionOut.model_validate(s) for s in items]


@router.get("/sessions/{session_id}", response_model=ChatSessionOut)
async def get_session(
    session_id: str,
    principal: PrincipalDep,
    db: DbDep,
) -> ChatSessionOut:
    user, _ = await _user_with_profile(db, principal)
    session = await ChatService(db).get_session(user, session_id)
    return ChatSessionOut.model_validate(session)


@router.patch("/sessions/{session_id}", response_model=ChatSessionOut)
async def rename_session(
    session_id: str,
    payload: ChatSessionUpdate,
    principal: PrincipalDep,
    db: DbDep,
) -> ChatSessionOut:
    """Rename a conversation (history sidebar)."""
    user, _ = await _user_with_profile(db, principal)
    session = await ChatService(db).rename_session(user, session_id, payload.title)
    return ChatSessionOut.model_validate(session)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    principal: PrincipalDep,
    db: DbDep,
) -> None:
    """Archive (soft-delete) a conversation."""
    user, _ = await _user_with_profile(db, principal)
    await ChatService(db).delete_session(user, session_id)


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageOut, status_code=201)
async def send_message(
    session_id: str,
    payload: ChatMessageCreate,
    principal: PrincipalDep,
    db: DbDep,
    _rate: None = Depends(rate_limit_chat),
) -> ChatMessageOut:
    """Persist a user turn and return the generated assistant reply.

    Idempotent via ``clientRequestId``: re-posting the same request returns the
    existing reply instead of regenerating.
    """
    user, profile = await _user_with_profile(db, principal)
    message = await ChatService(db).generate_reply(user, profile, session_id, payload)
    return ChatMessageOut.model_validate(message)


@router.get("/sessions/{session_id}/messages", response_model=Paginated[ChatMessageOut])
async def list_messages(
    session_id: str,
    principal: PrincipalDep,
    db: DbDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> Paginated[ChatMessageOut]:
    """Chronological message list for a session."""
    user, _ = await _user_with_profile(db, principal)
    items, total = await ChatService(db).list_messages(
        user, session_id, page=page, page_size=page_size
    )
    return Paginated(
        items=[ChatMessageOut.model_validate(m) for m in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/sessions/{session_id}/messages/stream")
async def stream_message(
    session_id: str,
    payload: ChatMessageCreate,
    principal: PrincipalDep,
    db: DbDep,
    rate: None = Depends(rate_limit_chat),
) -> StreamingResponse:
    """SSE transport of the same generation as ``POST .../messages``.

    Events: ``token`` (raw chunk), ``reply`` (JSON ChatMessageOut) then close.
    """
    user, profile = await _user_with_profile(db, principal)
    service = ChatService(db)

    async def event_writer() -> AsyncIterator[str]:
        async for event, data in service.stream_reply(user, profile, session_id, payload):
            if event == "token":
                payload_piece = json.dumps({"type": "token", "text": data}, ensure_ascii=False)
                yield f"data: {payload_piece}\n\n"
            else:
                piece = json.dumps(
                    {"type": "reply", "message": json.loads(data)}, ensure_ascii=False
                )
                yield f"data: {piece}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_writer(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
