"""Admin dashboard domain models (Prompt 15).

Supporting tables for the admin UI (docs/database/01 §20-§22): content
versioning, review/approval workflow, audit archive, bulk imports, feedback
management and system-health snapshots. Each is a thin append-only/CLI row that
backs a dashboard screen; heavy analytics stay in services, not the schema.

Tables:
- ``admin_audit_logs`` — who did what to which entity (append-only).
- ``scheme_versions`` — immutable snapshots of scheme content on each save.
- ``scheme_reviews`` — the approve/publish review queue entries.
- ``import_jobs`` — records of bulk scheme imports (file → parsed rows).
- ``feedback`` — user feedback about schemes/answers (chat-linked optional).
- ``system_health_checks`` — results of on-demand component probes.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import json_type

#: Canonical audit actions (kept tight so dashboards can group them).
AUDIT_ACTIONS = (
    "create",
    "update",
    "delete",
    "publish",
    "unpublish",
    "archive",
    "restore",
    "verify",
    "approve",
    "import",
    "bulk",
)


class AdminAuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Append-only audit trail for admin actions (docs/database §22 ``audit_logs``)."""

    __tablename__ = "admin_audit_logs"
    __table_args__ = (
        CheckConstraint(
            "action IN ('create','update','delete','publish','unpublish','archive',"
            "'restore','verify','approve','import','bulk')",
            name="ck_admin_audit_logs_action",
        ),
    )

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    action: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    entity_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    diff: Mapped[dict] = mapped_column(json_type(), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SchemeVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable snapshot of a scheme's content at save time (version history).

    ``version_number`` is 1-based per scheme; ``snapshot`` stores the scheme's
    full content dict, ``changes`` the field-level diff since the prior version.
    """

    __tablename__ = "scheme_versions"
    __table_args__ = (
        CheckConstraint("version_number >= 1", name="ck_scheme_versions_version_number"),
    )

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scheme_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(json_type(), nullable=False)
    changes: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    author: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class SchemeReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One submit-for-review / review / approval record of a scheme.

    ``status`` moves draft → pending → approved | rejected (or published),
    letting content editors submit and administrators approve (RBAC split).
    """

    __tablename__ = "scheme_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','rejected')",
            name="ck_scheme_reviews_status",
        ),
    )

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scheme_code: Mapped[str] = mapped_column(String(40), nullable=False)
    requester_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ImportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Record of one bulk-import attempt (schemes CSV/user CSV)."""

    __tablename__ = "import_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','processed','partial','failed')",
            name="ck_import_jobs_status",
        ),
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False, default="scheme")
    filename: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)


class Feedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User feedback on schemes / chat answers (docs/architecture §"feedback")."""

    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new','acknowledged','resolved','archived')",
            name="ck_feedback_status",
        ),
        CheckConstraint(
            "rating BETWEEN 1 AND 5",
            name="ck_feedback_rating",
        ),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    chat_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True
    )
    scheme_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("schemes.id", ondelete="SET NULL"), nullable=True
    )
    rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    category: Mapped[str | None] = mapped_column(String(24), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="new", index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SystemHealthCheck(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """On-demand system health probe snapshot (one row per component per run)."""

    __tablename__ = "system_health_checks"

    component: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # ok | degraded | down
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(String(300), nullable=True)
    checked_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
