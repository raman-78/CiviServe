"""Document endpoints (Prompt 11).

Private, authenticated, owner-scoped:

- ``GET    /documents/catalog``          — canonical document-type catalog.
- ``GET    /documents``                 — list my documents (freshest first).
- ``GET    /documents/{id}``            — one document (metadata + extraction).
- ``GET    /documents/{id}/file``       — authenticated download of the file.
- ``POST   /documents/upload``          — multipart upload (validated, checksum).
- ``POST   /documents/{id}/ocr``        — ingest OCR text from the browser adapter.
- ``POST   /documents/{id}/confirm-type`` — manual confirmation of detected type.
- ``POST   /documents/{id}/review``     — user-reviewed extracted field values.
- ``POST   /documents/{id}/replace``    — re-upload a fresh copy.
- ``DELETE /documents/{id}``            — delete (file + metadata).
- ``GET    /documents/readiness/{code}`` — per-scheme document checklist pre-check.

Security: every read/write is scoped by the authenticated ``user_id``; the
private ``file_ref`` is never exposed. Guests are rejected — documents require a
real account.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db
from app.core.errors import AuthenticationError
from app.core.security import AuthPrincipal, get_current_user
from app.schemas.document import (
    DocumentReadinessOut,
    DocumentReviewIn,
    DocumentTypeConfirmIn,
    DocumentTypeOut,
    ExtractedFieldOut,
    OcrResultOut,
    OcrSubmitIn,
    UploadOut,
    UserDocumentListOut,
    UserDocumentOut,
)
from app.services.document.detect import DetectedDocument
from app.services.document.service import DocumentService
from app.services.user import UserService

router = APIRouter(prefix="/documents", tags=["documents"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
PrincipalDep = Annotated[AuthPrincipal, Depends(get_current_user)]


def _require_user(principal: AuthPrincipal) -> None:
    if principal.is_guest:
        raise AuthenticationError("Sign in to manage documents.")


async def _user_id_for(principal: AuthPrincipal, db: AsyncSession) -> str:
    """Map the auth principal to the persisted user's UUID (owner scope key)."""
    user = await UserService(db).get_or_create_by_firebase(principal.uid)
    return str(user.id)


def _ocr_out(detected: DetectedDocument, doc: UserDocumentOut) -> OcrResultOut:
    return OcrResultOut(
        document_id=doc.id,
        detected_type=detected.code or None,
        type_name=detected.code or "",
        confidence=detected.confidence,
        ocr_confidence=detected.ocr_confidence,
        detection_code=detected.verdict,
        extracted_fields=[ExtractedFieldOut(**f) for f in detected.extracted],
        needs_manual_selection=detected.verdict in ("unrecognised", "mismatch"),
    )


@router.get("/catalog", response_model=list[DocumentTypeOut])
async def document_catalog(
    principal: PrincipalDep,
    db: DbDep,
) -> list[DocumentTypeOut]:
    """Canonical document types (+ accepted formats) powering the upload UI."""
    _require_user(principal)
    service = DocumentService(db)
    catalog = await service.catalog()
    return [
        DocumentTypeOut(
            code=t.code,
            kind=t.kind,
            name_en=t.name_en,
            localized_names=t.localized_names or {},
            ocr_supported=t.ocr_supported,
            accepted_formats=t.accepted_formats or [],
            guidance=t.guidance or {},
        )
        for t in catalog
    ]


@router.get("", response_model=UserDocumentListOut)
async def list_documents(
    principal: PrincipalDep,
    db: DbDep,
    page: int = 1,
    page_size: int = 20,
) -> UserDocumentListOut:
    _require_user(principal)
    user_id = await _user_id_for(principal, db)
    service = DocumentService(db)
    items, total = await service.list_user(user_id, page=page, page_size=page_size)
    return UserDocumentListOut(items=items, total=total)


@router.post("/upload", response_model=UploadOut)
async def upload_document(
    principal: PrincipalDep,
    db: DbDep,
    file: Annotated[UploadFile, File()],
    scheme_code: Annotated[str | None, Form()] = None,
    required_name: Annotated[str | None, Form()] = None,
) -> UploadOut:
    _require_user(principal)
    data = await file.read()
    user_id = await _user_id_for(principal, db)
    service = DocumentService(db)
    result = await service.upload(
        user_id,
        file_name=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        scheme_code=scheme_code,
        required_name=required_name,
    )
    return UploadOut(document=result.document, ocr_available=result.ocr_available)


@router.get("/{document_id}", response_model=UserDocumentOut)
async def get_document(
    principal: PrincipalDep,
    document_id: str,
    db: DbDep,
) -> UserDocumentOut:
    _require_user(principal)
    user_id = await _user_id_for(principal, db)
    service = DocumentService(db)
    doc = await service._load_owned(user_id, document_id)
    return service._doc_out(doc)


@router.get("/{document_id}/file")
async def download_file(
    principal: PrincipalDep,
    document_id: str,
    db: DbDep,
) -> Response:
    """Authenticated, owner-scoped binary download of the stored document."""
    _require_user(principal)
    user_id = await _user_id_for(principal, db)
    service = DocumentService(db)
    data = await service.read_file(user_id, document_id)
    return Response(content=data, media_type="application/octet-stream")


@router.post("/{document_id}/ocr", response_model=OcrResultOut)
async def submit_ocr(
    principal: PrincipalDep,
    document_id: str,
    payload: OcrSubmitIn,
    db: DbDep,
) -> OcrResultOut:
    """Ingest OCR text produced in the browser (tesseract.js)."""
    _require_user(principal)
    user_id = await _user_id_for(principal, db)
    service = DocumentService(db)
    detected, doc = await service.submit_ocr(user_id, document_id, payload.text)
    return _ocr_out(detected, doc)


@router.post("/{document_id}/confirm-type", response_model=UserDocumentOut)
async def confirm_type(
    principal: PrincipalDep,
    document_id: str,
    payload: DocumentTypeConfirmIn,
    db: DbDep,
) -> UserDocumentOut:
    _require_user(principal)
    user_id = await _user_id_for(principal, db)
    service = DocumentService(db)
    return await service.confirm_type(user_id, document_id, payload.document_type)


@router.post("/{document_id}/review", response_model=UserDocumentOut)
async def review_document(
    principal: PrincipalDep,
    document_id: str,
    payload: DocumentReviewIn,
    db: DbDep,
) -> UserDocumentOut:
    _require_user(principal)
    user_id = await _user_id_for(principal, db)
    service = DocumentService(db)
    return await service.review(user_id, document_id, fields=payload.fields, note=payload.note)


@router.post("/{document_id}/replace", response_model=UserDocumentOut)
async def replace_document(
    principal: PrincipalDep,
    document_id: str,
    db: DbDep,
    new_file: Annotated[UploadFile, File()],
) -> UserDocumentOut:
    _require_user(principal)
    data = await new_file.read()
    user_id = await _user_id_for(principal, db)
    service = DocumentService(db)
    return await service.replace(
        user_id,
        document_id,
        file_name=new_file.filename or "document",
        content_type=new_file.content_type or "application/octet-stream",
        data=data,
    )


@router.delete("/{document_id}")
async def delete_document(
    principal: PrincipalDep,
    document_id: str,
    db: DbDep,
) -> dict[str, bool]:
    _require_user(principal)
    user_id = await _user_id_for(principal, db)
    service = DocumentService(db)
    await service.delete(user_id, document_id)
    return {"ok": True}


@router.get("/readiness/{scheme_code}", response_model=DocumentReadinessOut)
async def scheme_readiness(
    principal: PrincipalDep,
    scheme_code: str,
    db: DbDep,
) -> DocumentReadinessOut:
    _require_user(principal)
    user_id = await _user_id_for(principal, db)
    service = DocumentService(db)
    return await service.readiness(user_id, scheme_code)


__all__ = ["router"]
