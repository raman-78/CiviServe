"""Chat schemas, mirroring ``shared/src/domain/chat.ts``.

Fields are declared snake_case (matching ORM attributes for ``from_attributes``);
the APIModel alias generator emits camelCase JSON. ``language`` needs an explicit
``validation_alias`` because the ORM column is ``content_language``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel


class ChatSessionCreate(APIModel):
    language: str = Field(default="en", max_length=8)
    channel: str = Field(default="web", max_length=16)
    title: str | None = Field(default=None, max_length=160)


class ChatSessionUpdate(APIModel):
    """Rename payload for ``PATCH /sessions/{id}``."""

    title: str = Field(..., min_length=1, max_length=160)


class ChatSessionOut(APIModel):
    id: uuid.UUID
    user_id: uuid.UUID
    language: str
    channel: str = "web"
    status: str = "active"
    title: str | None = None
    message_count: int = 0
    last_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ChatMessageCreate(APIModel):
    """Request body for POST .../messages. text-only for Prompt 3."""

    text: str = Field(..., max_length=4000)
    language: str = Field(default="en", max_length=8)
    content_type: str = Field(default="text", max_length=24)
    client_request_id: uuid.UUID | None = None


class ChatMessageOut(APIModel):
    id: int
    session_id: uuid.UUID
    role: str
    content_type: str = "text"
    content: str
    language: str = Field(validation_alias="content_language")
    rendered_text: str | None = None
    intent: str | None = None
    payload: dict = Field(default_factory=dict)
    status: str = "complete"
    created_at: datetime
