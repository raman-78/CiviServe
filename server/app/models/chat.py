"""Conversation aggregates: ``chat_sessions`` and ``chat_messages``.

Mirror ``shared/src/domain/chat.ts`` and ``docs/database/01`` §4. Stub-chat only
in Prompt 3 — no AI provider wired yet.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import json_type


class ChatSession(Base):
    """A conversation anchored to a user; the unit of history/context."""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('web','android','ios','whatsapp','telegram','ivr')",
            name="ck_chat_sessions_channel",
        ),
        CheckConstraint(
            "status IN ('active','closed','archived')",
            name="ck_chat_sessions_status",
        ),
        Index("ix_chat_sessions_user_updated", "user_id", "updated_at"),
        Index("ix_chat_sessions_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    language: Mapped[str] = mapped_column(
        String(8), ForeignKey("languages.code", ondelete="RESTRICT"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="web")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    """A single turn in the conversation. Hot, append-only table (BIGINT PK)."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user','assistant','system')",
            name="ck_chat_messages_role",
        ),
        CheckConstraint(
            "status IN ('queued','processing','complete','failed')",
            name="ck_chat_messages_status",
        ),
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
        Index("ix_chat_messages_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    client_request_id: Mapped[uuid.UUID | None] = mapped_column(
        index=True, unique=True, nullable=True
    )
    role: Mapped[str] = mapped_column(String(12), nullable=False)
    content_type: Mapped[str] = mapped_column(String(24), nullable=False, default="text")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_language: Mapped[str] = mapped_column(
        String(8), ForeignKey("languages.code", ondelete="RESTRICT"), nullable=False
    )
    rendered_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    intent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    payload: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="complete")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    session: Mapped[ChatSession] = relationship(back_populates="messages")
