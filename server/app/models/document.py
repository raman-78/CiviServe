"""Document pipeline persistence (Prompt 11).

Models:
- ``DocumentType`` — the canonical catalog of document types (AADHAAR, …). Each
  row carries the kind, OCR support and accepted formats so the UI never
  hardcodes formats, and the detector has one place to map codes → kinds.
- ``UserDocument`` — a citizen's uploaded file. ``doc_ref`` is the *private*
  storage key; there is deliberately **no public URL column**. ``status`` is the
  processing status pipeline: uploaded → processing → processed/needs_review →
  user_confirmed, or the failure states (unsupported / ocr_failed).
- ``DocumentExtraction`` — the OCR + type-detection result summary. Raw OCR
  text is never stored (privacy); only extracted fields + confidence land here.
- ``DocumentReview`` — the user's confirmation/correction of extracted data.

Security model: every row is owned by exactly one user and read/written only via
owner-scoped repository methods. Files live outside the DB under a private
storage root (``settings.document_storage_dir``), referenced by ``file_ref``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import json_type

PROCESSING_STATUSES = (
    "uploaded",
    "processing",
    "processed",
    "needs_review",
    "matches",
    "mismatch",
    "unsupported",
    "ocr_failed",
    "user_confirmed",
)

OCR_CONFIDENCES = ("high", "needs_review", "low")

ACCEPTED_FORMATS = ("pdf", "jpg", "jpeg", "png")


#: Codes the catalog is seeded with (mirrors ``DocumentCode`` in shared).
_seed_codes = (
    "AADHAAR",
    "PAN_CARD",
    "RATION_CARD",
    "BANK_PASSBOOK",
    "BANK_ACCOUNT",
    "INCOME_CERTIFICATE",
    "COMMUNITY_CERTIFICATE",
    "CASTE_CERTIFICATE",
    "RESIDENCE_CERTIFICATE",
    "DISABILITY_CERTIFICATE",
    "BIRTH_CERTIFICATE",
    "MARK_SHEET",
    "VOTER_ID",
    "PASSPORT",
    "LAND_RECORD",
    "PHOTOGRAPH",
    "MARRIAGE_CERTIFICATE",
    "APPLICATION_FORM",
    "OTHER",
)


class DocumentType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Canonical catalog entry for one recognisable document type."""

    __tablename__ = "document_types"
    __table_args__ = (UniqueConstraint("code", name="uq_document_types_code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="other")
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    localized_names: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    ocr_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    accepted_formats: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    guidance: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)


class UserDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A citizen's uploaded document (owner-scoped, no public URL)."""

    __tablename__ = "user_documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded','processing','processed','needs_review','matches',"
            "'mismatch','unsupported','ocr_failed','user_confirmed')",
            name="ck_user_documents_status",
        ),
        CheckConstraint(
            "ocr_confidence IN ('high','needs_review','low')",
            name="ck_user_documents_ocr_confidence",
        ),
        Index("ix_user_documents_user_updated", "user_id", "updated_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheme_code: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    #: Canonical requirement this upload targets (RequiredDocument.name).
    required_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    #: Private storage reference, never exposed as a URL.
    file_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    #: Integrity checksum recorded at upload (SHA-256 hex).
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    ocr_confidence: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None)
    detected_type: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    detection_confidence: Mapped[float | None] = mapped_column(
        Numeric(4, 3), nullable=True, default=None
    )
    type_matches: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    detection_code: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


class DocumentExtraction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-document OCR + type-detection summary (no raw OCR text stored)."""

    __tablename__ = "document_extractions"
    __table_args__ = (
        UniqueConstraint("user_document_id", name="uq_document_extractions_doc"),
        Index("ix_document_extractions_doc", "user_document_id"),
        CheckConstraint(
            "extracted_status IN ('processed','needs_review','ocr_failed')",
            name="ck_document_extractions_status",
        ),
    )

    user_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_documents.id", ondelete="CASCADE"), nullable=False
    )
    detected_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detection_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    extracted_fields: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    extracted_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="needs_review"
    )


class DocumentReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User confirmation/correction of an extraction (never silently edited)."""

    __tablename__ = "document_reviews"
    __table_args__ = (
        UniqueConstraint("user_document_id", name="uq_document_reviews_doc"),
        Index("ix_document_reviews_doc", "user_document_id"),
    )

    user_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_documents.id", ondelete="CASCADE"), nullable=False
    )
    corrected_fields: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)


__all__ = [
    "DocumentReview",
    "DocumentType",
    "UserDocument",
    "PROCESSING_STATUSES",
    "OCR_CONFIDENCES",
    "ACCEPTED_FORMATS",
]
