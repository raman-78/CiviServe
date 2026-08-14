"""Eligibility result persistence (docs/database/01 §333 `user_eligibility_results`).

Each row snapshots one person's evaluation of one scheme so the chat follow-up
can know what was already asked, and rule-semantics changes never corrupt history
(``engine_version`` is stamped on every row).
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import json_type
from app.services.recommendation.engine import ENGINE_VERSION

_RESULT_STATUSES = ("eligible", "likely", "needs_more_info", "not_eligible")


class UserEligibilityResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One scheme's structured evaluation for one user (docs §333)."""

    __tablename__ = "user_eligibility_results"
    __table_args__ = (
        CheckConstraint(
            "result_status IN ('eligible','likely','needs_more_info','not_eligible')",
            name="ck_user_eligibility_results_status",
        ),
        UniqueConstraint("user_id", "scheme_id", name="uq_user_eligibility_user_scheme"),
        Index("ix_user_eligibility_results_user", "user_id"),
        Index("ix_user_eligibility_results_scheme", "scheme_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False
    )
    #: profile attributes (flattened dict) the engine actually evaluated.
    profile_snapshot: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    result_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="needs_more_info"
    )
    match_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    matched_rules: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    broken_rules: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False, default=ENGINE_VERSION)


__all__ = ["UserEligibilityResult", "_RESULT_STATUSES"]
