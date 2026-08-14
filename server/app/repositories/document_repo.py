"""Document persistence (Prompt 11), owner-scoped only.

Every query filters by ``user_id`` first; there is no cross-user access path.
Raw OCR text is never stored — only structured extraction summaries.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, desc, func, select

from app.models.document import DocumentExtraction, DocumentType, UserDocument
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[UserDocument]):
    model = UserDocument

    # -- CRUD ---------------------------------------------------------------

    async def list_for_user(
        self, user_id: Any, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[UserDocument], int]:
        count_stmt = (
            select(func.count()).select_from(UserDocument).where(UserDocument.user_id == user_id)
        )
        total = int((await self.session.execute(count_stmt)).scalar_one())
        stmt = (
            select(UserDocument)
            .where(UserDocument.user_id == user_id)
            .order_by(desc(UserDocument.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def owned(self, user_id: Any, document_id: Any) -> UserDocument | None:
        stmt = select(UserDocument).where(
            UserDocument.id == document_id, UserDocument.user_id == user_id
        )
        return await self._scalar_one(stmt)

    async def delete_owned(self, document: UserDocument) -> None:
        # remove extraction + review rows (cascade covers FKs on compliant DBs,
        # but SQLite in tests needs explicit deletes)
        await self.session.execute(
            delete(DocumentExtraction).where(DocumentExtraction.user_document_id == document.id)
        )
        await self.delete(document)

    # -- Extractions ---------------------------------------------------------

    async def extraction_for(self, user_document_id: Any) -> DocumentExtraction | None:
        stmt = select(DocumentExtraction).where(
            DocumentExtraction.user_document_id == user_document_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_extraction(self, extraction: DocumentExtraction) -> DocumentExtraction:
        await self.session.merge(extraction)
        await self.session.flush()
        return extraction

    # -- Catalog -------------------------------------------------------------

    async def catalog_all(self) -> list[DocumentType]:
        stmt = select(DocumentType).order_by(DocumentType.code)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def catalog_by_code(self, code: str) -> DocumentType | None:
        stmt = select(DocumentType).where(DocumentType.code == code.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_catalog(self) -> int:
        stmt = select(func.count()).select_from(DocumentType)
        return int((await self.session.execute(stmt)).scalar_one())


__all__ = ["DocumentRepository"]
