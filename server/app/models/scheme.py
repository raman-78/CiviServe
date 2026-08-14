"""Government schemes + user scheme interactions.

Mirrors ``shared/src/domain/scheme.ts`` and the schema in ``docs/database/01``
§5-§7. Rich content is stored denormalised as JSON columns (the aggregate shape
the client and chat cards consume); the normalized child tables
(``scheme_category_links``, ``scheme_states``, ``eligibility_rules``, ...) will
be introduced with the eligibility engine prompt without breaking this surface.

Tables:
- ``schemes`` — the catalog (single source of truth for the AI assistant RAG).
- ``user_saved_schemes`` — bookmarks (composite PK user+scheme).
- ``user_saved_searches`` — saved search queries (unique per user/query).
- ``user_search_history`` — recent searches (pruned to the latest N).
- ``user_scheme_views`` — recently viewed schemes (upsert on view).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import json_type

#: Cap on retained per-user search-history rows (pruned periodically).
SEARCH_HISTORY_LIMIT = 10


class Scheme(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A government scheme. ``applicable_states=[]`` + ``scope=central`` = all India."""

    __tablename__ = "schemes"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('central','state')",
            name="ck_schemes_scope",
        ),
        CheckConstraint(
            "scheme_status IN ('draft','pending_review','verified','published',"
            "'temporarily_unavailable','archived','expired')",
            name="ck_schemes_scheme_status",
        ),
        CheckConstraint(
            "verification_status IN ('unverified','pending','verified','failed','stale')",
            name="ck_schemes_verification_status",
        ),
    )

    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_native: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    summary_en: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    summary_native: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    description_en: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    description_native: Mapped[str] = mapped_column(String(2000), nullable=False, default="")

    category: Mapped[str] = mapped_column(String(30), nullable=False)
    sub_category: Mapped[str | None] = mapped_column(String(60), nullable=True)

    ministry: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    scope: Mapped[str] = mapped_column(String(12), nullable=False, default="central")
    state_code: Mapped[str] = mapped_column(String(20), nullable=False, default="*", index=True)
    applicable_states: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)

    target_beneficiaries: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    benefits: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    eligibility_rules: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    required_documents: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    application_steps: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    faqs: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    renewal_process: Mapped[dict] = mapped_column(json_type(), nullable=True)

    application_links: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    official_website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    official_application_link: Mapped[str | None] = mapped_column(String(500), nullable=True)

    keywords: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    tags: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)

    scheme_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="published", index=True
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    #: Source provenance + verification, used by the admin content pipeline
    #: (Prompt 13). ``source_type`` is e.g. ``official_portal`` | ``gazette`` |
    #: ``state_scheme_portal`` | ``ministry_document``.
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unverified", index=True
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    #: Supporting numbers for ordering/trending/metadata.
    popularity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bookmark_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UserSavedScheme(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user's bookmarked scheme (docs/database/01 §7 `user_saved_schemes`)."""

    __tablename__ = "user_saved_schemes"
    __table_args__ = (
        UniqueConstraint("user_id", "scheme_id", name="uq_user_saved_schemes_user_scheme"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    notify_on_update: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    scheme: Mapped[Scheme] = relationship()


class UserSavedSearch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A search the user wants to revisit / get notified about."""

    __tablename__ = "user_saved_searches"
    __table_args__ = (
        UniqueConstraint("user_id", "query", name="uq_user_saved_searches_user_query"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    query: Mapped[str] = mapped_column(String(200), nullable=False)
    filters: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    notify_on_update: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class UserSearchHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Recent search entries; pruned to ``SEARCH_HISTORY_LIMIT`` per user."""

    __tablename__ = "user_search_history"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    query: Mapped[str] = mapped_column(String(200), nullable=False)
    filters: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)


class UserSchemeView(UUIDPrimaryKeyMixin, Base):
    """Tracks that a user viewed a scheme (upserted, powers "recently viewed")."""

    __tablename__ = "user_scheme_views"
    __table_args__ = (
        UniqueConstraint("user_id", "scheme_id", name="uq_user_scheme_views_user_scheme"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
