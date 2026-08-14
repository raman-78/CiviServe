"""Document pipeline service (Prompt 11).

Owns the workflow: upload (store + persist metadata) → OCR text ingest →
type detection → confirm type → review/correct extracted fields → readiness
per scheme. Every method is owner-scoped via ``user_id``; the caller is the
authenticated principal.

Persistence: services write then commit. File ops are delegated to
:class:`~app.services.document.storage.DocumentStorage`; OCR text arrives from
the browser OCR adapter (tesseract) and is never stored — only extracted fields.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotFoundError, ValidationError_
from app.models.document import (
    DocumentExtraction,
    DocumentType,
    UserDocument,
)
from app.repositories.document_repo import DocumentRepository
from app.repositories.scheme_repo import SchemeRepository
from app.schemas.document import (
    ChecklistItemOut,
    DocumentReadinessOut,
    ExtractedFieldOut,
    UserDocumentOut,
    _extracted_to_out,
)
from app.services.document.detect import DetectedDocument, detect_document
from app.services.document.storage import DocumentStorage

_DISCLAIMER = (
    "This is a pre-application checklist only. It does not guarantee "
    "eligibility or approval. The final decision rests with the concerned "
    "government authority."
)


def _coerce_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:  # noqa: PERF203
        raise ValidationError_("Invalid identifier.", code="DOCUMENT_INVALID_ID") from exc


#: Processing statuses that count as "document available" for readiness.
_AVAILABLE_STATUSES = ("processed", "matches", "user_confirmed")
#: Statuses that flag "attention needed" (mismatch, low OCR, unsupported).
_ATTENTION_STATUSES = ("needs_review", "mismatch", "unsupported", "ocr_failed")


@dataclass(frozen=True)
class UploadResult:
    document: UserDocumentOut
    ocr_available: bool = True


class DocumentService:
    """Document workflow orchestration (no HTTP awareness)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DocumentRepository(session)
        self.schemes = SchemeRepository(session)
        self.storage = DocumentStorage()

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    def _doc_out(doc: UserDocument, *, with_extraction: bool = True) -> UserDocumentOut:
        fields: list[dict[str, Any]] = []
        extraction = getattr(doc, "_extraction", None)
        if with_extraction and extraction is not None:
            fields = extraction.extracted_fields or []
        return UserDocumentOut(
            id=str(doc.id),
            user_id=str(doc.user_id),
            scheme_code=doc.scheme_code,
            required_name=doc.required_name,
            file_name=doc.file_name,
            file_extension=doc.file_extension,
            file_size_bytes=doc.file_size_bytes,
            mime_type=doc.mime_type,
            status=doc.status,
            ocr_confidence=doc.ocr_confidence,
            detected_type=doc.detected_type,
            detection_confidence=(
                float(doc.detection_confidence) if doc.detection_confidence else None
            ),
            type_matches=doc.type_matches,
            detection_code=doc.detection_code,
            extracted_fields=_extracted_to_out(fields),
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            processed_at=doc.processed_at,
            reviewed_at=doc.reviewed_at,
        )

    async def _extraction_for(self, doc: UserDocument) -> DocumentExtraction | None:
        return await self.repo.extraction_for(doc.id)

    async def _load_owned(self, user_id: str, document_id: str) -> UserDocument:
        doc_id = _coerce_uuid(document_id)
        doc = await self.repo.owned(_coerce_uuid(user_id), doc_id)
        if doc is None:
            raise NotFoundError("Document not found.")
        return doc

    # -- Upload --------------------------------------------------------------

    async def upload(
        self,
        user_id: str,
        *,
        file_name: str,
        content_type: str,
        data: bytes,
        scheme_code: str | None = None,
        required_name: str | None = None,
    ) -> UploadResult:
        extension = self.storage.extension_from_name(file_name)
        file_ref, checksum = await self.storage.save(data, extension=extension)
        settings = get_settings()
        doc = UserDocument(
            user_id=_coerce_uuid(user_id),
            scheme_code=scheme_code,
            required_name=required_name,
            file_name=file_name,
            file_extension=extension,
            file_size_bytes=len(data),
            mime_type=content_type or "application/octet-stream",
            file_ref=file_ref,
            checksum=checksum if settings.document_store_checksum else None,
            status="uploaded",
        )
        await self.repo.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        ocr_available = bool(settings and extension in ("jpg", "jpeg", "png", "pdf"))
        return UploadResult(document=self._doc_out(doc), ocr_available=ocr_available)

    # -- OCR + detection -----------------------------------------------------

    async def submit_ocr(
        self, user_id: str, document_id: str, ocr_text: str, *, expected: str | None = None
    ) -> tuple[DetectedDocument, UserDocumentOut]:
        doc = await self._load_owned(user_id, document_id)
        if doc.status == "user_confirmed":
            raise ValidationError_("This document is already confirmed.", code="DOCUMENT_CONFIRMED")
        detected = detect_document(ocr_text, expected=expected)
        await self._apply_detection(doc, detected)
        extraction = await self._extraction_for(doc)
        doc._extraction = extraction  # type: ignore[attr-defined]
        return detected, self._doc_out(doc)

    async def _apply_detection(self, doc: UserDocument, detected: DetectedDocument) -> None:
        doc.status = "processed"
        doc.ocr_confidence = detected.ocr_confidence
        doc.detected_type = detected.code
        doc.detection_code = detected.verdict
        doc.detection_confidence = detected.confidence
        doc.type_matches = None
        doc.processed_at = datetime.now(UTC)
        if doc.required_name:
            doc.type_matches = _matches_required(detected.code, doc.required_name)
        extraction_status = (
            "processed" if detected.verdict in ("matched", "partial") else "needs_review"
        )
        extraction = DocumentExtraction(
            user_document_id=doc.id,
            detected_type=detected.code,
            detection_confidence=detected.confidence,
            extracted_fields=detected.extracted,
            extracted_status=extraction_status,
        )
        await self.repo.upsert_extraction(extraction)
        await self.session.commit()
        await self.session.refresh(doc)

    # -- Type confirmation ---------------------------------------------------

    async def confirm_type(
        self, user_id: str, document_id: str, document_type: str
    ) -> UserDocumentOut:
        doc = await self._load_owned(user_id, document_id)
        code = document_type.strip().upper()
        catalog = await self.repo.catalog_by_code(code)
        if catalog is None:
            raise ValidationError_(f"Unknown document type '{code}'.", code="DOCUMENT_UNKNOWN_TYPE")
        doc.detected_type = code
        doc.status = "processed"
        doc.detection_code = "matched"
        doc.type_matches = _matches_required(code, doc.required_name)
        if doc.required_name is None:
            doc.type_matches = None
        await self.session.commit()
        await self.session.refresh(doc)
        return self._doc_out(doc)

    # -- Review --------------------------------------------------------------

    async def review(
        self,
        user_id: str,
        document_id: str,
        *,
        fields: list[ExtractedFieldOut] | None,
        note: str | None,
    ) -> UserDocumentOut:
        doc = await self._load_owned(user_id, document_id)
        extraction = await self._extraction_for(doc)
        if extraction is None:
            raise ValidationError_(
                "This document has not been processed yet.", code="DOCUMENT_NOT_PROCESSED"
            )
        extraction.extracted_fields = [f.model_dump() for f in fields or []]
        extraction.extracted_status = "processed"
        doc.status = "user_confirmed"
        doc.reviewed_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(doc)
        return self._doc_out(doc)

    # -- Replace / delete / download -----------------------------------------

    async def replace(
        self,
        user_id: str,
        document_id: str,
        *,
        file_name: str,
        content_type: str,
        data: bytes,
    ) -> UserDocumentOut:
        doc = await self._load_owned(user_id, document_id)
        extension = self.storage.extension_from_name(file_name)
        file_ref, checksum = await self.storage.save(data, extension=extension)
        old_ref = doc.file_ref
        doc.file_ref = file_ref
        doc.checksum = checksum
        doc.file_name = file_name
        doc.file_extension = extension
        doc.file_size_bytes = len(data)
        doc.mime_type = content_type or "application/octet-stream"
        doc.status = "uploaded"
        doc.ocr_confidence = None
        doc.detected_type = None
        doc.detection_code = None
        doc.detection_confidence = None
        doc.type_matches = None
        doc.processed_at = None
        doc.reviewed_at = None
        if doc.required_name:
            doc.type_matches = None
        await self.session.commit()
        await self.session.refresh(doc)
        await self.storage.delete(old_ref)
        return self._doc_out(doc)

    async def delete(self, user_id: str, document_id: str) -> None:
        doc = await self._load_owned(user_id, document_id)
        await self.repo.delete_owned(doc)
        await self.session.commit()
        await self.storage.delete(doc.file_ref)

    async def read_file(self, user_id: str, document_id: str) -> bytes:
        doc = await self._load_owned(user_id, document_id)
        return await self.storage.read(doc.file_ref)

    # -- Listing -------------------------------------------------------------

    async def list_user(
        self, user_id: str, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[UserDocumentOut], int]:
        uid = _coerce_uuid(user_id)
        docs, total = await self.repo.list_for_user(uid, page=page, page_size=page_size)
        # bulk-load extractions so N+1 is avoided for a page of documents
        ids = [doc.id for doc in docs]
        extraction_map: dict[uuid.UUID, DocumentExtraction] = {}
        if ids:
            stmt = select(DocumentExtraction).where(DocumentExtraction.user_document_id.in_(ids))
            result = await self.session.execute(stmt)
            for row in result.scalars():
                extraction_map[row.user_document_id] = row
        for doc in docs:
            doc._extraction = extraction_map.get(doc.id)  # type: ignore[attr-defined]
        return [self._doc_out(doc) for doc in docs], total

    # -- Catalog -------------------------------------------------------------

    async def catalog(self) -> list[DocumentType]:
        return await self.repo.catalog_all()

    # -- Readiness -----------------------------------------------------------

    async def readiness(self, user_id: str, scheme_code: str) -> DocumentReadinessOut:
        scheme = await self.schemes.by_code(scheme_code)
        if scheme is None:
            raise NotFoundError("Scheme not found.")
        requirements = scheme.required_documents or []
        if not requirements:
            raise ValidationError_(
                "This scheme has no document checklist.", code="DOCUMENT_NO_REQUIREMENTS"
            )
        required_names = [r.get("name") for r in requirements if r.get("name")]
        uploaded = await self._documents_for_requirements(user_id, required_names)

        items: list[ChecklistItemOut] = []
        uploaded_count = needs_review_count = 0
        for requirement in requirements:
            name = requirement.get("name")
            user_doc = uploaded.get(name)
            status = _status_for(user_doc)
            is_missing = status == "missing" or status in _ATTENTION_STATUSES
            if user_doc is not None:
                uploaded_count += 1
                if status in _ATTENTION_STATUSES:
                    needs_review_count += 1
            items.append(
                ChecklistItemOut(
                    required=requirement,
                    status=status,
                    user_document=self._doc_out(user_doc) if user_doc else None,
                    is_missing=is_missing,
                    guidance=_guidance_for(status, requirement),
                    official_source_url=requirement.get("sourceUrl"),
                )
            )

        required_count = len(requirements)
        # "available" = uploaded and not flagged for attention
        available_count = sum(1 for i in items if i.status in _AVAILABLE_STATUSES)
        percent = round(available_count / required_count * 100) if required_count else 0
        missing_count = sum(1 for i in items if i.is_missing)
        return DocumentReadinessOut(
            scheme_code=scheme.code,
            required_count=required_count,
            uploaded_count=uploaded_count,
            missing_count=missing_count,
            needs_review_count=needs_review_count,
            percent=percent,
            items=items,
            disclaimer=_DISCLAIMER,
        )

    async def _documents_for_requirements(
        self, user_id: str, required_names: list[str]
    ) -> dict[str, UserDocument]:
        if not required_names:
            return {}
        stmt = select(UserDocument).where(
            UserDocument.user_id == _coerce_uuid(user_id),
            UserDocument.required_name.in_(required_names),
        )
        result = await self.session.execute(stmt)
        docs: dict[str, UserDocument] = {}
        for doc in result.scalars():
            if doc.required_name is not None:
                docs.setdefault(doc.required_name, doc)
        return docs


def _matches_required(detected_code: str, required_name: str | None) -> bool:
    return detected_code.upper() == (required_name or "").upper()


def _status_for(user_doc: UserDocument | None) -> str:
    if user_doc is None:
        return "missing"
    return user_doc.status


def _guidance_for(status: str, requirement: dict[str, Any]) -> str | None:
    if status in _ATTENTION_STATUSES:
        return (
            "This document needs your attention — please review or re-upload it."
            if status == "needs_review"
            else "This document could not be verified. Please re-upload a clear copy."
        )
    if status == "missing":
        hint = requirement.get("verificationHint")
        return hint or "Please upload this document."
    return None


__all__ = ["DocumentService", "UploadResult", "_DISCLAIMER"]
