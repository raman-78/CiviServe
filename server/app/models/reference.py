"""Reference catalogs: ``languages`` and ``states``.

Mirror the shared domain contracts in ``shared/src/domain/language.ts`` and the
schema in ``docs/database/01`` §5.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Language(Base):
    """Supported languages catalog (code is the natural key)."""

    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    native_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    script: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    is_rtl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    indic_trans: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class State(Base):
    """Indian states/UTs catalog (code is the natural key)."""

    __tablename__ = "states"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_native: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    region: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    is_ut: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
