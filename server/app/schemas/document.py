"""Document pipeline DTOs (Prompt 11).

All responses use camelCase JSON via the shared ``APIModel`` alias generator.
Extracted fields are returned with muted display values where sensitive; the
server never returns the private ``file_ref`` or raw stored text.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel

_OcrConfidence = Literal["high", "needs_review", "low"]


class DocumentTypeOut(APIModel):
    """One catalog entry (also powers the accepted-format list for the UI)."""

    code: str
    kind: str
    name_en: str
    localized_names: dict = Field(default_factory=dict)
    ocr_supported: bool = True
    accepted_formats: list[str] = Field(default_factory=list)
    guidance: dict = Field(default_factory=dict)


class ExtractedFieldOut(APIModel):
    """One extracted field with its display-safe masked copy."""

    key: str
    label: str
    value: str
    masked: str | None = None
    reliable: bool | None = None


class UserDocumentOut(APIModel):
    """Public view of an uploaded document (owner may also fetch the file)."""

    id: str
    user_id: str
    scheme_code: str | None = None
    required_name: str | None = None
    file_name: str
    file_extension: str
    file_size_bytes: int
    mime_type: str
    status: str
    ocr_confidence: str | None = None
    detected_type: str | None = None
    detection_confidence: float | None = None
    type_matches: bool | None = None
    detection_code: str | None = None
    extracted_fields: list[ExtractedFieldOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None = None
    reviewed_at: datetime | None = None


class UserDocumentListOut(APIModel):
    items: list[UserDocumentOut] = Field(default_factory=list)
    total: int = 0


class OcrSubmitIn(APIModel):
    """OCR text pushed from the browser OCR adapter (tesseract)."""

    text: str = Field(min_length=1)


class OcrResultOut(APIModel):
    """Verdict of the OCR + type-detection pass."""

    document_id: str
    detected_type: str | None = None
    type_name: str = ""
    confidence: float = 0.0
    ocr_confidence: _OcrConfidence = "needs_review"
    detection_code: Literal["matched", "partial", "unrecognised", "mismatch"] = "unrecognised"
    extracted_fields: list[ExtractedFieldOut] = Field(default_factory=list)
    needs_manual_selection: bool = True


class DocumentTypeConfirmIn(APIModel):
    document_type: str


class DocumentReviewIn(APIModel):
    """User-confirmed field corrections (never silently applied)."""

    fields: list[ExtractedFieldOut] = Field(default_factory=list)
    note: str | None = None


class DocumentReplaceIn(APIModel):
    """Optional replacement payload for a document (client sends a new file)."""

    # Present for symmetry; upload routes use multipart bodies.
    pass


class ChecklistItemOut(APIModel):
    required: dict = Field(default_factory=dict)
    status: str
    user_document: UserDocumentOut | None = None
    is_missing: bool = True
    guidance: str | None = None
    official_source_url: str | None = None


class DocumentReadinessOut(APIModel):
    """Per-scheme pre-check summary. Never an official approval score."""

    scheme_code: str
    required_count: int = 0
    uploaded_count: int = 0
    missing_count: int = 0
    needs_review_count: int = 0
    percent: int = 0
    items: list[ChecklistItemOut] = Field(default_factory=list)
    disclaimer: str = ""


class OcrUnavailableOut(APIModel):
    ok: bool = False
    message: str = ""


class UploadOut(APIModel):
    """Multipart upload envelope."""

    document: UserDocumentOut
    ocr_available: bool


def _extracted_to_out(fields: list[dict]) -> list[ExtractedFieldOut]:
    out = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        out.append(
            ExtractedFieldOut(
                key=str(field.get("key", "")),
                label=str(field.get("label", "")),
                value=str(field.get("value", "")),
                masked=field.get("masked") if field.get("masked") else None,
                reliable=bool(field.get("reliable")),
            )
        )
    return out


__all__ = [
    "ChecklistItemOut",
    "DocumentReadinessOut",
    "DocumentReplaceIn",
    "DocumentReviewIn",
    "DocumentTypeConfirmIn",
    "DocumentTypeOut",
    "ExtractedFieldOut",
    "OcrResultOut",
    "OcrUnavailableOut",
    "UploadOut",
    "UserDocumentListOut",
    "UserDocumentOut",
    "_extracted_to_out",
]
