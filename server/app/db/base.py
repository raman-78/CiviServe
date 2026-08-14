"""Base model, metadata and shared column mixins.

Prompt 3 implements only the core identity + conversation aggregates and the
reference catalogs. Scheme content, eligibility, RAG, centres, etc. are added by
later prompts as new models under ``app/models``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

#: PostgreSQL-friendly JSON type (JSONB on postgres, JSON elsewhere).
#: Declared in db.types via variant decoration; simple generic JSON is used here
#: for portability across sqlite (tests) and postgres (prod).


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class UUIDPrimaryKeyMixin:
    """UUID primary key, generated client-side for portability."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=_uuid,
    )


class TimestampMixin:
    """created_at / updated_at audit timestamps (UTC)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
