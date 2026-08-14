"""Admin dashboard service (Prompt 15).

Owns the business rules for the scheme knowledge pipeline:

- **Publication lifecycle** — create → submit for review → admin approve/publish →
  maintain (temporarily unavailable / archive / expire). Only ``published`` is
  visible to citizens (the search/browse/RAG rails all filter on it).
- **Versioning** — every save writes an immutable ``SchemeVersion`` snapshot.
- **Auditing** — every mutation writes an ``AdminAuditLog`` row.
- **Review queue** — content editors submit; only **admins** approve/publish
  (server-side, not just hidden UI buttons).
- **Publish gate** — a scheme may only be published when its eligibility rules
  pass strict validation and required fields are present.
- **Duplicate detection** — normalized-name collisions are reported on create.
- **RAG + cache sync** — every mutation sweeps the ``scheme:*`` cache namespace so
  the public rails (trending/popular/categories/suggestions) and RAG (which
  re-reads the DB per request) see fresh data immediately.

Multi-step mutations ride one session unit of work; callers commit once.
"""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.cache import invalidate_cache_prefix
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError_
from app.models.admin import (
    AdminAuditLog,
    ImportJob,
    SchemeReview,
    SchemeVersion,
)
from app.models.scheme import Scheme
from app.models.user import User
from app.repositories.admin_repo import (
    AdminAuditLogRepository,
    FeedbackRepository,
    ImportJobRepository,
    SchemeReviewRepository,
    SchemeVersionRepository,
    find_duplicates,
)
from app.repositories.scheme_repo import SchemeRepository
from app.repositories.user_repo import UserRepository
from app.schemas.admin import AdminSchemeOut
from app.schemas.scheme import LocalizedText, SchemeCreate, SchemeUpdate
from app.services.admin.rules_validator import validate_rules, validate_rules_for_publish
from app.services.scheme import SchemeService
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

#: Cache namespaces to sweep whenever the catalog mutates.
CACHE_NAMESPACES = ("scheme:",)

#: Content fields that enter version snapshots and diffs.
_SCHEME_COPY_FIELDS = (
    "name_en",
    "name_native",
    "summary_en",
    "summary_native",
    "description_en",
    "description_native",
    "category",
    "sub_category",
    "ministry",
    "department",
    "scope",
    "state_code",
    "applicable_states",
    "target_beneficiaries",
    "benefits",
    "eligibility_rules",
    "required_documents",
    "application_steps",
    "renewal_process",
    "application_links",
    "official_website",
    "official_application_link",
    "faqs",
    "keywords",
    "tags",
    "source_name",
    "source_url",
    "source_type",
    "verification_status",
    "review_note",
)

#: Restrictive status state machine.
_ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"draft", "pending_review", "archived", "expired", "temporarily_unavailable"},
    "pending_review": {
        "pending_review",
        "verified",
        "published",
        "archived",
        "expired",
        "draft",
    },
    "verified": {
        "verified",
        "published",
        "temporarily_unavailable",
        "archived",
        "expired",
        "draft",
    },
    "published": {"published", "temporarily_unavailable", "archived", "expired"},
    "temporarily_unavailable": {
        "temporarily_unavailable",
        "published",
        "archived",
        "expired",
        "draft",
    },
    "archived": {"archived", "draft", "expired"},
    "expired": {"expired", "archived", "draft"},
}


def _snapshot_of(scheme: Scheme) -> dict[str, Any]:
    """Serialize a scheme's content into a JSON-safe dict for the version row."""
    return {field: getattr(scheme, field) for field in _SCHEME_COPY_FIELDS}


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _diff(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """Field-level change list comparing two snapshots."""
    changes: list[dict[str, Any]] = []
    b = before or {}
    a = after or {}
    for field in sorted(set(b) | set(a)):
        before_value = _json_safe(b.get(field))
        after_value = _json_safe(a.get(field))
        if before_value != after_value:
            changes.append({"field": field, "before": before_value, "after": after_value})
    return changes


class AdminService:
    """Knowledge-base administration. Callers pass a fully-authorized principal."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SchemeRepository(session)
        self.users = UserRepository(session)
        self.audit = AdminAuditLogRepository(session)
        self.versions = SchemeVersionRepository(session)
        self.reviews = SchemeReviewRepository(session)
        self.feedback = FeedbackRepository(session)
        self.imports = ImportJobRepository(session)
        self.schemes = SchemeService(session)

    # ------------------------------------------------------------------ dto --

    def to_admin_out(self, scheme: Scheme, *, version: int | None = None) -> AdminSchemeOut:
        fields: dict[str, Any] = {
            "id": str(scheme.id),
            "code": scheme.code,
            "short_name": scheme.short_name,
            "name_en": scheme.name_en,
            "name_native": scheme.name_native,
            "category": scheme.category,
            "sub_category": scheme.sub_category,
            "ministry": scheme.ministry,
            "department": scheme.department,
            "scope": scheme.scope,
            "state_code": scheme.state_code,
            "scheme_status": scheme.scheme_status,
            "verification_status": scheme.verification_status,
            "source_name": scheme.source_name,
            "source_url": scheme.source_url,
            "source_type": scheme.source_type,
            "review_note": scheme.review_note,
            "last_verified_at": scheme.last_verified_at,
            "created_at": scheme.created_at,
            "updated_at": scheme.updated_at,
            "popularity": scheme.popularity,
            "view_count": scheme.view_count,
            "bookmark_count": scheme.bookmark_count,
            "version_number": version,
        }
        return AdminSchemeOut(**fields)

    async def audit_log(
        self,
        user: User,
        action: str,
        entity_type: str,
        *,
        entity_id: str | None = None,
        entity_code: str | None = None,
        summary: str | None = None,
        diff: dict[str, Any] | None = None,
    ) -> AdminAuditLog:
        return await self.audit.add_log(
            actor_id=user.id,
            actor_role=user.role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_code=entity_code,
            summary=summary,
            diff=diff,
        )

    # ------------------------------------------------------------ overview --

    async def overview(self) -> dict[str, Any]:
        """Dashboard summary: counts by status + users + feedback + latest verify."""
        by_status = await self.repo.count_by_status()
        total = sum(by_status.values())
        published = by_status.get("published", 0)
        feedback_counts = await self.feedback.counts_by_status()
        pending_reviews, pending_total = await self.reviews.list_pending(page=1, page_size=1)
        latest_verified = await self._latest_verified_scheme()
        published_categories = await self.repo.count_by_category()
        return {
            "stats": {
                "schemeTotal": total,
                "schemePublished": published,
                "schemeDraft": by_status.get("draft", 0),
                "schemePendingReview": by_status.get("pending_review", 0),
                "schemeVerified": by_status.get("verified", 0),
                "schemeArchived": by_status.get("archived", 0),
                "expired": by_status.get("expired", 0),
                "temporarilyUnavailable": by_status.get("temporarily_unavailable", 0),
                "userTotal": await self.users.count_all(),
                "usersLast30d": await self.users.count_recent(),
                "publishedPercent": round(100 * published / total) if total else 0.0,
                "pendingApprovals": pending_total,
                "newFeedback": feedback_counts.get("new", 0),
                "schemeVersionsCount": await self._version_count(),
                "lastVerifiedAt": latest_verified.last_verified_at if latest_verified else None,
            },
            "byStatus": [
                {"status": key, "count": value} for key, value in sorted(by_status.items())
            ],
            "pendingReview": (
                {
                    "id": str(pending_reviews[0].id),
                    "schemeCode": pending_reviews[0].scheme_code,
                    "requesterId": (
                        str(pending_reviews[0].requester_id)
                        if pending_reviews[0].requester_id
                        else None
                    ),
                    "createdAt": pending_reviews[0].created_at,
                }
                if pending_reviews
                else None
            ),
            "publishedCategories": [
                {"category": key, "count": value}
                for key, value in sorted(
                    published_categories.items(), key=lambda kv: kv[1], reverse=True
                )
            ],
        }

    async def _latest_verified_scheme(self) -> Scheme | None:
        stmt = (
            select(Scheme)
            .where(Scheme.last_verified_at.isnot(None))
            .order_by(desc(Scheme.last_verified_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _version_count(self) -> int:
        stmt = select(func.count()).select_from(SchemeVersion)
        return int((await self.session.execute(stmt)).scalar_one())

    # ---------------------------------------------------------------- list --

    async def list_schemes(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        q: str | None = None,
        status: str | None = None,
        category: str | None = None,
        verification_status: str | None = None,
        ministry: str | None = None,
        scope: str | None = None,
        sort: str = "updated",
    ) -> tuple[list[Scheme], int]:
        return await self.repo.list_admin(
            page=page,
            page_size=page_size,
            q=q,
            status=status,
            category=category,
            verification_status=verification_status,
            ministry=ministry,
            scope=scope,
            sort=sort,
        )

    # -------------------------------------------------------------- create --

    async def create_scheme(self, user: User, payload: SchemeCreate) -> Scheme:
        if await self.repo.by_code(payload.code) is not None:
            raise ConflictError(f"Scheme code '{payload.code}' already exists.")
        validate_rules(payload.eligibility_rules or [])
        scheme = await self.schemes.create_scheme(payload)
        await self.session.flush()
        await self._record_version(scheme, author=user.id, reason="Initial import", changes=[])
        await self.audit_log(
            user,
            "create",
            "scheme",
            entity_id=str(scheme.id),
            entity_code=scheme.code,
        )
        await self.session.commit()
        await self.session.refresh(scheme)
        await self._sync_caches()
        return scheme

    # ------------------------------------------------------------ retrieval --

    async def get_scheme(self, code: str) -> tuple[Scheme, SchemeVersion | None]:
        scheme = await self.repo.by_code(code)
        if scheme is None:
            raise NotFoundError("Scheme not found.")
        latest = await self.versions.latest(scheme.id)
        return scheme, latest

    async def get_scheme_detail(self, code: str) -> tuple[Scheme, int | None, list[dict[str, Any]]]:
        scheme, latest = await self.get_scheme(code)
        dup = await find_duplicates(self.session, by_name=scheme.name_en, exclude_id=scheme.id)
        dup_ids = [{"id": str(d.id), "code": d.code, "name": d.name_en} for d in dup]
        return scheme, latest.version_number if latest else None, dup_ids

    async def list_versions(self, code: str) -> list[dict[str, Any]]:
        scheme = await self.repo.by_code(code)
        if scheme is None:
            raise NotFoundError("Scheme not found.")
        rows, _ = await self.versions.list_for_scheme(scheme.id)
        return [
            {
                "id": str(row.id),
                "schemeId": str(row.scheme_id),
                "schemeCode": row.scheme_code,
                "versionNumber": row.version_number,
                "changes": row.changes or [],
                "reason": row.reason,
                "author": str(row.author) if row.author else None,
                "createdAt": row.created_at,
                "updatedAt": row.updated_at,
            }
            for row in rows
        ]

    # -------------------------------------------------------------- update --

    async def update_scheme(self, user: User, code: str, payload: SchemeUpdate) -> Scheme:
        scheme = await self.repo.by_code(code)
        if scheme is None:
            raise NotFoundError("Scheme not found.")
        before = _snapshot_of(scheme)
        if payload.eligibility_rules is not None:
            validate_rules(payload.eligibility_rules or [])
        updated = await self.schemes.update_scheme(code, payload)
        await self.session.flush()
        after = _snapshot_of(updated)
        changes = _diff(before, after)
        await self._record_version(
            updated,
            author=user.id,
            reason=getattr(payload, "_reason", None),
            changes=changes,
        )
        await self.audit_log(
            user,
            "update",
            "scheme",
            entity_id=str(updated.id),
            entity_code=updated.code,
            summary=f"{len(changes)} field(s) updated",
            diff={"changes": changes[:40]},
        )
        await self.session.commit()
        await self.session.refresh(updated)
        await self._sync_caches()
        return updated

    async def _record_version(
        self,
        scheme: Scheme,
        *,
        author: uuid.UUID | None,
        reason: str | None,
        changes: list[dict[str, Any]],
    ) -> SchemeVersion:
        version = SchemeVersion(
            scheme_id=scheme.id,
            scheme_code=scheme.code,
            version_number=await self.versions.next_version(scheme.id),
            snapshot=_snapshot_of(scheme),
            changes=changes,
            reason=reason,
            author=author,
        )
        self.session.add(version)
        return version

    # ---------------------------------------------------------- status flow --

    async def change_status(
        self,
        user: User,
        code: str,
        *,
        status: str,
        note: str | None = None,
    ) -> Scheme:
        """Admin status transition (publish / temporarily-unavailable / archive)."""
        scheme = await self.repo.by_code(code)
        if scheme is None:
            raise NotFoundError("Scheme not found.")
        allowed = _ALLOWED_STATUS_TRANSITIONS.get(scheme.scheme_status, set())
        if status not in allowed:
            raise ForbiddenError(f"Scheme cannot move from '{scheme.scheme_status}' to '{status}'.")
        if status == "published":
            await self._publish_gate(scheme)
            action = "publish"
        elif status == "archived":
            action = "archive"
        elif status == "temporarily_unavailable":
            action = "unpublish"
        else:
            action = "update"
        scheme.scheme_status = status
        scheme.review_note = note or scheme.review_note
        await self.audit_log(
            user,
            action,
            "scheme",
            entity_id=str(scheme.id),
            entity_code=scheme.code,
            summary=f"Status → {status}" + (f": {note}" if note else ""),
        )
        await self.session.commit()
        await self.session.refresh(scheme)
        await self._sync_caches()
        return scheme

    async def _publish_gate(self, scheme: Scheme) -> None:
        """Structural gate enforced on publish (rules valid + required fields)."""
        validate_rules_for_publish(scheme.eligibility_rules or [])
        missing = []
        if not (scheme.name_en or "").strip():
            missing.append("name_en")
        if not (scheme.summary_en or "").strip():
            missing.append("summary_en")
        if not (scheme.category or "").strip():
            missing.append("category")
        if missing:
            raise ValidationError_(
                f"Cannot publish scheme; missing required fields ({', '.join(missing)})."
            )

    async def submit_for_review(
        self, user: User, code: str, *, note: str | None = None
    ) -> dict[str, Any]:
        """Editor action: mark a scheme pending_review + open a review ticket."""
        scheme = await self.repo.by_code(code)
        if scheme is None:
            raise NotFoundError("Scheme not found.")
        if scheme.scheme_status not in {"draft", "pending_review", "verified"}:
            raise ValidationError_("Only draft/pending schemes can be submitted for review.")
        validate_rules(scheme.eligibility_rules or [])
        review = SchemeReview(
            scheme_id=scheme.id,
            scheme_code=scheme.code,
            requester_id=user.id,
            status="pending",
            from_status=scheme.scheme_status,
            request_note=note,
        )
        self.session.add(review)
        scheme.scheme_status = "pending_review"
        await self.audit_log(
            user,
            "update",
            "scheme",
            entity_id=str(scheme.id),
            entity_code=scheme.code,
            summary=f"Submitted for review{': ' + note if note else ''}",
        )
        await self.session.commit()
        return {
            "id": str(review.id),
            "schemeCode": scheme.code,
            "status": "pending",
            "createdAt": review.created_at,
        }

    async def list_review_queue(
        self, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[SchemeReview], int]:
        return await self.reviews.list_pending(page=page, page_size=page_size)

    async def decide_review(
        self,
        admin: User,
        review_id: str,
        *,
        approve: bool,
        note: str | None = None,
        publish: bool = False,
    ) -> Scheme:
        """Admin action: approve (→ verified/published) or reject a review ticket."""
        review = await self.reviews.get(uuid.UUID(review_id))
        if review is None or review.status != "pending":
            raise NotFoundError("Review ticket not found or already decided.")
        scheme = await self.repo.get(review.scheme_id)
        if scheme is None:
            raise NotFoundError("Scheme not found.")

        review.reviewer_id = admin.id
        review.reviewed_at = datetime.now(UTC)
        review.note = note
        if approve:
            if publish:
                await self._publish_gate(scheme)
                scheme.scheme_status = "published"
                action = "publish"
            else:
                scheme.scheme_status = "verified"
                action = "approve"
            review.status = "approved"
        else:
            review.status = "rejected"
            scheme.scheme_status = review.from_status or "draft"
            action = "update"
        await self.audit_log(
            admin,
            action,
            "scheme",
            entity_id=str(scheme.id),
            entity_code=scheme.code,
            summary=f"Review {review.status}{': ' + note if note else ''}",
        )
        await self.session.commit()
        await self.session.refresh(scheme)
        await self._sync_caches()
        return scheme

    # ------------------------------------------------------------- archive --

    async def delete_scheme(self, user: User, code: str) -> None:
        scheme = await self.repo.by_code(code)
        if scheme is None:
            raise NotFoundError("Scheme not found.")
        if scheme.scheme_status == "published":
            raise ConflictError("Published schemes cannot be deleted; archive first.")
        await self.audit_log(
            user,
            "delete",
            "scheme",
            entity_id=str(scheme.id),
            entity_code=scheme.code,
        )
        await self.repo.delete_scheme_rows(scheme)
        await self.session.commit()
        await self._sync_caches()

    # --------------------------------------------------------------- users --

    async def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        q: str | None = None,
        role: str | None = None,
        status: str | None = None,
    ) -> tuple[list[User], int]:
        return await self.users.list_admin(
            page=page, page_size=page_size, q=q, role=role, status=status
        )

    async def set_user_role(self, admin: User, user_id: str, role: str) -> User:
        user = await self.users.by_id(uuid.UUID(user_id))
        if user is None:
            raise NotFoundError("User not found.")
        if user.id == admin.id and role != "admin":
            raise ConflictError("You cannot demote yourself.")
        previous = user.role
        user.role = role
        await self.audit_log(
            admin,
            "update",
            "user",
            entity_id=str(user.id),
            entity_code=user.email or str(user.id),
            summary=f"Role: {previous} → {role}",
        )
        await self.session.commit()
        return user

    async def set_user_status(self, admin: User, user_id: str, status: str) -> User:
        user = await self.users.by_id(uuid.UUID(user_id))
        if user is None:
            raise NotFoundError("User not found.")
        if user.id == admin.id and status == "suspended":
            raise ConflictError("You cannot suspend yourself.")
        previous = user.status
        user.status = status
        await self.audit_log(
            admin,
            "update",
            "user",
            entity_id=str(user.id),
            entity_code=user.email or str(user.id),
            summary=f"Status: {previous} → {status}",
        )
        await self.session.commit()
        return user

    # ------------------------------------------------------------- audits / feedback --

    async def list_audit_logs(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        entity_type: str | None = None,
        action: str | None = None,
    ) -> tuple[list[AdminAuditLog], int]:
        return await self.audit.list(
            page=page,
            page_size=page_size,
            entity_type=entity_type,
            action=action,
        )

    async def list_feedback(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
    ) -> tuple[list[Any], int]:
        return await self.feedback.list(page=page, page_size=page_size, status=status)

    async def feedback_counts(self) -> dict[str, int]:
        return await self.feedback.counts_by_status()

    async def update_feedback(
        self, admin: User, feedback_id: str, *, status: str, note: str | None = None
    ) -> Any:
        fb = await self.feedback.get(uuid.UUID(feedback_id))
        if fb is None:
            raise NotFoundError("Feedback not found.")
        previous = fb.status
        fb.status = status
        if status == "resolved":
            fb.resolved_at = datetime.now(UTC)
        await self.audit_log(
            admin,
            "update",
            "feedback",
            entity_id=str(fb.id),
            summary=f"Feedback {previous} → {status}" + (f": {note}" if note else ""),
        )
        await self.session.commit()
        return fb

    # --------------------------------------------------------------- imports --

    async def preview_import(self, rows: list[dict[str, Any]], *, kind: str) -> dict[str, Any]:
        """Validate rows without writing; flag create-vs-update per code."""
        preview: list[dict[str, Any]] = []
        valid = invalid = 0
        for index, row in enumerate(rows, start=1):
            entry: dict[str, Any] = {"row": index}
            code = str(row.get("code") or "").strip().upper()
            entry["code"] = code or None
            entry["name"] = str(row.get("name") or row.get("name_en") or "").strip() or None
            error = _validate_import_row(row, code=code)
            if error:
                invalid += 1
                entry["error"] = error
            else:
                valid += 1
                existing = await self.repo.by_code(code) if code else None
                entry["willCreate"] = existing is None
                entry["willUpdate"] = existing is not None
            preview.append(entry)
        return {
            "kind": kind,
            "totalRows": len(rows),
            "validRows": valid,
            "invalidRows": invalid,
            "rows": preview,
        }

    async def apply_import(
        self, user: User, rows: list[dict[str, Any]], *, kind: str = "scheme"
    ) -> dict[str, Any]:
        """Commit an import: creates/updates schemes, records an ImportJob."""
        job = ImportJob(
            created_by=user.id,
            kind=kind,
            status="pending",
            total_rows=len(rows),
            errors=[],
        )
        job = await self.imports.add(job)
        imported = failed = 0
        errors: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            code = str(row.get("code") or "").strip().upper()
            error = _validate_import_row(row, code=code)
            if error:
                failed += 1
                errors.append({"row": index, "error": error})
                continue
            try:
                existing = await self.repo.by_code(code)
                if existing is not None:
                    await self.schemes.update_scheme(code, _row_update_payload(row))
                else:
                    await self.schemes.create_scheme(_row_create_payload(row, code=code))
                imported += 1
            except Exception as exc:  # noqa: BLE001 — per-row isolation
                failed += 1
                errors.append({"row": index, "error": str(exc)})
        job.imported_rows = imported
        job.failed_rows = failed
        job.status = "failed" if failed and not imported else "partial" if failed else "processed"
        job.errors = errors
        await self.audit_log(
            user,
            "import",
            "import_job",
            entity_id=str(job.id),
            summary=f"Imported {imported}/{len(rows)} rows",
        )
        await self.session.commit()
        await self._sync_caches()
        return {
            "jobId": str(job.id),
            "kind": kind,
            "importedRows": imported,
            "failedRows": failed,
            "errors": errors,
        }

    async def list_import_jobs(
        self, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[ImportJob], int]:
        stmt = select(ImportJob).order_by(desc(ImportJob.created_at))
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    # ----------------------------------------------------------- health + sync --

    async def run_health_check(self, admin: User) -> dict[str, Any]:
        from app.services.admin.health_monitor import run_health_probe

        return await run_health_probe(self.session, checked_by=admin.id)

    async def _sync_caches(self) -> None:
        for namespace in CACHE_NAMESPACES:
            invalidate_cache_prefix(namespace)


def _validate_import_row(row: dict[str, Any], *, code: str) -> str | None:
    if not _code_ok(code):
        return "Invalid or missing 'code' (2-32 chars, [A-Z0-9._-])."
    name = str(row.get("name") or row.get("name_en") or "").strip()
    if not name:
        return "Missing required 'name'."
    if not str(row.get("ministry") or "").strip():
        return "Missing required 'ministry'."
    rules = row.get("eligibility_rules")
    if rules is not None:
        try:
            parsed = _coerce_rules(rules)
            validate_rules(parsed)
        except ValidationError_ as exc:
            return f"Invalid eligibility_rules: {exc.message}"
        except Exception as exc:  # noqa: BLE001
            return f"Invalid eligibility_rules: {exc}"
    return None


def _code_ok(code: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{1,31}", code))


def _rows_from_csv_text(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    return [
        {k.strip(): (v or "").strip() for k, v in row.items() if k and (v or "").strip()}
        for row in reader
    ]


def rows_from_upload(file_obj: Any) -> list[dict[str, Any]]:
    """Parse a CSV UploadFile body into list-of-dict rows (best-effort)."""
    try:
        text = file_obj.read().decode("utf-8-sig")
    except (AttributeError, UnicodeDecodeError):
        return []
    return _rows_from_csv_text(text)


def _coerce_rules(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [r for r in value if isinstance(r, dict)]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return []
        return [r for r in parsed if isinstance(r, dict)] if isinstance(parsed, list) else []
    return []


def _localized(value: Any, default: str = "") -> LocalizedText:
    if isinstance(value, dict):
        return LocalizedText(en=value.get("en") or default, native=value.get("native") or default)
    text = str(value or "").strip()
    if text:
        return LocalizedText(en=text, native=text)
    return LocalizedText(en=default, native=default)


def _row_create_payload(row: dict[str, Any], *, code: str) -> SchemeCreate:
    name = str(row.get("name") or row.get("name_en") or "").strip()
    category = str(row.get("category") or "other").lower()
    valid_categories = {
        "education",
        "health",
        "housing",
        "employment",
        "agriculture",
        "pension",
        "women",
        "disability",
        "food-security",
        "financial-inclusion",
        "other",
    }
    if category not in valid_categories:
        category = "other"
    return SchemeCreate(
        code=code,
        name=_localized(row.get("name") or row.get("name_en"), name),
        summary=_localized(row.get("summary") or row.get("summary_en"), name),
        description=_localized(row.get("description") or row.get("description_en"), name),
        category=category,
        ministry=str(row.get("ministry") or "").strip(),
        department=str(row.get("department") or "").strip() or None,
        scope="state" if str(row.get("scope") or "").strip().lower() == "state" else "central",
        state_code=str(row.get("state_code") or "*").strip() or "*",
        scheme_status="draft",
        eligibility_rules=_coerce_rules(row.get("eligibility_rules")),
        source_name=str(row.get("source_name") or "").strip() or None,
        source_url=str(row.get("source_url") or "").strip() or None,
        source_type=str(row.get("source_type") or "").strip() or None,
        tags=_split_tags(row.get("tags")),
    )


def _row_update_payload(row: dict[str, Any]) -> SchemeUpdate:
    rules = _coerce_rules(row.get("eligibility_rules"))
    return SchemeUpdate(
        name=_localized(row.get("name") or row.get("name_en")),
        summary=_localized(row.get("summary") or row.get("summary_en")),
        description=_localized(row.get("description") or row.get("description_en")),
        category=(str(row.get("category")).lower() if row.get("category") else None),
        ministry=str(row.get("ministry") or "").strip() or None,
        department=str(row.get("department") or "").strip() or None,
        eligibility_rules=rules if row.get("eligibility_rules") is not None else None,
        source_name=str(row.get("source_name") or "").strip() or None,
        source_url=str(row.get("source_url") or "").strip() or None,
        source_type=str(row.get("source_type") or "").strip() or None,
    )


def _split_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(t).strip() for t in value if str(t).strip()]
    text = str(value or "").strip()
    return [t.strip() for t in re.split(r"[;,|]", text) if t.strip()]
