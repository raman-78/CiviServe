"""Persistence for admin/dashboard entities (Prompt 15).

Covers version history, review queue, audit logs, import jobs, feedback and
system-health snapshots. Purely data access — the admin service owns the
business rules (RBAC split, publish gates, RAG/cache invalidation).
"""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import Select, desc, func, select

from app.models.admin import (
    AdminAuditLog,
    Feedback,
    ImportJob,
    SchemeReview,
    SchemeVersion,
    SystemHealthCheck,
)
from app.models.scheme import Scheme
from app.repositories.base import BaseRepository


class AdminAuditLogRepository(BaseRepository[AdminAuditLog]):
    model = AdminAuditLog

    async def add_log(
        self,
        *,
        actor_id: uuid.UUID | None,
        actor_role: str | None,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        entity_code: str | None = None,
        diff: dict[str, Any] | None = None,
        summary: str | None = None,
    ) -> AdminAuditLog:
        log = AdminAuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_code=entity_code,
            diff=diff,
            summary=summary,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> tuple[list[AdminAuditLog], int]:
        stmt = select(AdminAuditLog)
        if entity_type:
            stmt = stmt.where(AdminAuditLog.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AdminAuditLog.entity_id == entity_id)
        if action:
            stmt = stmt.where(AdminAuditLog.action == action)
        if actor_id:
            stmt = stmt.where(AdminAuditLog.actor_id == actor_id)
        total = await self._count(stmt)
        stmt = (
            stmt.order_by(desc(AdminAuditLog.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def _count(self, stmt: Select[Any]) -> int:
        count_stmt = select(func.count()).select_from(stmt.subquery())
        return int((await self.session.execute(count_stmt)).scalar_one())


class SchemeVersionRepository(BaseRepository[SchemeVersion]):
    model = SchemeVersion

    async def next_version(self, scheme_id: uuid.UUID) -> int:
        stmt = select(func.max(SchemeVersion.version_number)).where(
            SchemeVersion.scheme_id == scheme_id
        )
        value = (await self.session.execute(stmt)).scalar_one()
        return int(value or 0) + 1

    async def list_for_scheme(
        self, scheme_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[SchemeVersion], int]:
        stmt = (
            select(SchemeVersion)
            .where(SchemeVersion.scheme_id == scheme_id)
            .order_by(desc(SchemeVersion.version_number))
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def latest(self, scheme_id: uuid.UUID) -> SchemeVersion | None:
        stmt = (
            select(SchemeVersion)
            .where(SchemeVersion.scheme_id == scheme_id)
            .order_by(desc(SchemeVersion.version_number))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return cast("SchemeVersion | None", result.scalar_one_or_none())


class SchemeReviewRepository(BaseRepository[SchemeReview]):
    model = SchemeReview

    async def list_pending(
        self, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[SchemeReview], int]:
        return await self._list(status="pending", page=page, page_size=page_size)

    async def _list(
        self, *, status: str | None, page: int, page_size: int
    ) -> tuple[list[SchemeReview], int]:
        stmt = select(SchemeReview)
        if status is not None:
            stmt = stmt.where(SchemeReview.status == status)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        stmt = (
            stmt.order_by(desc(SchemeReview.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def by_scheme_latest(self, scheme_id: uuid.UUID) -> SchemeReview | None:
        stmt = (
            select(SchemeReview)
            .where(SchemeReview.scheme_id == scheme_id)
            .order_by(desc(SchemeReview.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return cast("SchemeReview | None", result.scalar_one_or_none())


class ImportJobRepository(BaseRepository[ImportJob]):
    model = ImportJob


class FeedbackRepository(BaseRepository[Feedback]):
    model = Feedback

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        category: str | None = None,
    ) -> tuple[list[Feedback], int]:
        stmt = select(Feedback)
        if status:
            stmt = stmt.where(Feedback.status == status)
        if category:
            stmt = stmt.where(Feedback.category == category)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        stmt = (
            stmt.order_by(desc(Feedback.created_at)).offset((page - 1) * page_size).limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def counts_by_status(self) -> dict[str, int]:
        stmt = select(Feedback.status, func.count()).group_by(Feedback.status)
        rows = (await self.session.execute(stmt)).all()
        return {status: count for status, count in rows}


class SystemHealthCheckRepository(BaseRepository[SystemHealthCheck]):
    model = SystemHealthCheck


class DuplicateSchemeProbe:
    """Shared duplicate-detection helpers for the SchemeRepository/admin flow."""

    @staticmethod
    def fingerprint(scheme: Scheme) -> str:
        name = (scheme.name_en or "").strip().lower().replace(" ", "")
        return f"{name}:{scheme.ministry or ''}".lower()


async def find_duplicates(
    session: Any, *, by_name: str, exclude_id: uuid.UUID | None = None
) -> list[Scheme]:
    """Scheme rows whose normalized name matches ``by_name``, for dup warnings.

    SQLite-safe: the comparison runs on loaded rows (the catalog is small and
    this is an on-save, rare path, never the hot read side).
    """
    needle = (by_name or "").strip().lower().replace(" ", "")
    if not needle:
        return []
    schemes = await session.execute(select(Scheme).order_by(desc(Scheme.created_at)))
    rows = list(schemes.scalars().all())
    return [
        s
        for s in rows
        if (s.name_en or "").strip().lower().replace(" ", "") == needle
        and (exclude_id is None or s.id != exclude_id)
    ]
