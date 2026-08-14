"""Admin dashboard API (Prompt 15).

RBAC split enforced server-side:

- ``require_admin``       — only ``admin`` principals (approve/publish/manage).
- ``require_staff``       — ``admin`` + ``content_editor`` (create/edit/import).

Every endpoint 401s unauthenticated callers, 403s non-privileged roles, and the
service layer re-checks the per-action status transitions so a crafted payload
can never jump a scheme to an invalid state.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, cast

from fastapi import (
    APIRouter,
    Depends,
    File,
    Query,
    UploadFile,
)
from fastapi import (
    status as fastapi_status,
)
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db
from app.core.errors import ForbiddenError
from app.core.security import AuthPrincipal, get_current_user
from app.models.user import User
from app.repositories.scheme_repo import SchemeRepository
from app.schemas.admin import (
    AdminUsersPageOut,
    AuditLogOut,
    FeedbackOut,
    ImportJobOut,
    ReviewQueueOut,
    SchemeAdminPageOut,
    SchemeOutAdminDetail,
    SchemeVersionOut,
)
from app.schemas.common import APIModel
from app.schemas.scheme import SchemeCreate, SchemeOut, SchemeUpdate
from app.services.admin.service import AdminService, rows_from_upload
from app.services.scheme import SchemeService
from app.services.user import UserService

router = APIRouter(tags=["admin"], prefix="/admin")

DbDep = Annotated[AsyncSession, Depends(get_db)]
PrincipalDep = Annotated[AuthPrincipal, Depends(get_current_user)]

_ADMIN = {"admin"}
_STAFF = {"admin", "content_editor"}


def _require_admin(principal: AuthPrincipal) -> AuthPrincipal:
    principal.require_role(*_ADMIN)
    return principal


def _require_staff(principal: AuthPrincipal) -> AuthPrincipal:
    principal.require_role(*_STAFF)
    return principal


async def _admin_user(db: AsyncSession, principal: AuthPrincipal) -> User:
    if principal.is_guest:
        raise ForbiddenError("Guests cannot access the admin dashboard.")
    return await UserService(db).get_or_create_by_firebase(principal.uid)


def _scheme_admin_to(service: AdminService, s: Any, *, version: int | None = None) -> dict:
    dto = service.to_admin_out(s, version=version).model_dump(by_alias=True, exclude_none=True)
    dto["tags"] = s.tags or []
    dto["name"] = {"en": s.name_en, "native": s.name_native}
    dto["summary"] = {"en": s.summary_en, "native": s.summary_native}
    dto["description"] = {"en": s.description_en, "native": s.description_native}
    return dto


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


@router.get("/overview")
async def admin_overview(
    db: DbDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """Dashboard summary (admin)."""
    _require_admin(principal)
    await _admin_user(db, principal)
    return cast("dict[str, Any]", await AdminService(db).overview())


# ---------------------------------------------------------------------------
# Scheme knowledge-base management
# ---------------------------------------------------------------------------


@router.get("/schemes", response_model=SchemeAdminPageOut)
async def list_schemes_admin(
    db: DbDep,
    principal: PrincipalDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    q: str | None = Query(default=None, max_length=120),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None, max_length=30),
    verification_status: str | None = Query(default=None, alias="verificationStatus"),
    ministry: str | None = Query(default=None, max_length=120),
    scope: str | None = Query(default=None, pattern="^(central|state)$"),
    sort: str = Query(default="updated", pattern="^(updated|popular|name)$"),
) -> dict[str, Any]:
    """Admin catalog listing across *all* statuses (admin)."""
    _require_admin(principal)
    await _admin_user(db, principal)
    service = AdminService(db)
    schemes, total = await service.list_schemes(
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
    return {
        "items": [_scheme_admin_to(service, s) for s in schemes],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


@router.post("/schemes", response_model=SchemeOut, status_code=fastapi_status.HTTP_201_CREATED)
async def create_scheme_admin(
    payload: SchemeCreate,
    db: DbDep,
    principal: PrincipalDep,
) -> SchemeOut:
    """Create a scheme; duplicate codes/names detected server-side (staff)."""
    _require_staff(principal)
    user = await _admin_user(db, principal)
    scheme = await AdminService(db).create_scheme(user, payload)
    return SchemeService(db).to_out(scheme)


@router.get("/schemes/{code}/detail", response_model=SchemeOutAdminDetail)
async def get_scheme_admin_detail(
    code: str,
    db: DbDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """Admin editor payload for one scheme (+ duplicate warnings)."""
    _require_admin(principal)
    await _admin_user(db, principal)
    service = AdminService(db)
    scheme, version, dup_ids = await service.get_scheme_detail(code)
    return {
        "scheme": _scheme_admin_to(service, scheme, version=version),
        "duplicate_ids": [d["id"] for d in dup_ids],
    }


@router.get("/schemes/{code}/versions", response_model=list[SchemeVersionOut])
async def scheme_versions(
    code: str,
    db: DbDep,
    principal: PrincipalDep,
) -> list[dict[str, Any]]:
    """Version history for one scheme (admin)."""
    _require_admin(principal)
    await _admin_user(db, principal)
    return await AdminService(db).list_versions(code)


@router.put("/schemes/{code}", response_model=SchemeOut)
async def update_scheme_admin(
    code: str,
    payload: SchemeUpdate,
    db: DbDep,
    principal: PrincipalDep,
    x_review_note: str | None = Query(default=None, alias="reason", max_length=500),
) -> SchemeOut:
    """Partial content update; writes a version + audit row automatically (staff)."""
    _require_staff(principal)
    user = await _admin_user(db, principal)
    payload._reason = x_review_note  # type: ignore[attr-defined]  # noqa: B010
    scheme = await AdminService(db).update_scheme(user, code, payload)
    return SchemeService(db).to_out(scheme)


@router.patch("/schemes/{code}/status", response_model=SchemeOut)
async def change_scheme_status(
    code: str,
    db: DbDep,
    principal: PrincipalDep,
    status: str = Query(..., pattern="^[a-z_]+$"),
    note: str | None = Query(default=None, max_length=500),
) -> SchemeOut:
    """Publish / temporarily-unavailable / archive / expire a scheme (admin)."""
    _require_admin(principal)
    user = await _admin_user(db, principal)
    scheme = await AdminService(db).change_status(user, code, status=status, note=note)
    return SchemeService(db).to_out(scheme)


@router.post("/schemes/{code}/submit-for-review", response_model=dict)
async def submit_scheme_review(
    code: str,
    db: DbDep,
    principal: PrincipalDep,
    note: str | None = Query(default=None, max_length=500),
) -> dict[str, Any]:
    """Submit a draft for review (staff)."""
    _require_staff(principal)
    user = await _admin_user(db, principal)
    return await AdminService(db).submit_for_review(user, code, note=note)


@router.get("/reviews", response_model=dict)
async def list_reviews(
    db: DbDep,
    principal: PrincipalDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """Pending review queue (admin)."""
    _require_admin(principal)
    await _admin_user(db, principal)
    service = AdminService(db)
    rows, total = await service.list_review_queue(page=page, page_size=page_size)
    return {
        "items": [
            ReviewQueueOut(
                id=str(r.id),
                scheme_id=str(r.scheme_id),
                scheme_code=r.scheme_code,
                status=r.status,
                from_status=r.from_status,
                request_note=r.request_note,
                note=r.note,
                requester_id=str(r.requester_id) if r.requester_id else None,
                reviewer_id=str(r.reviewer_id) if r.reviewer_id else None,
                created_at=r.created_at,
            ).model_dump(by_alias=True)
            for r in rows
        ],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


@router.post("/reviews/{review_id}/decision", response_model=SchemeOut)
async def decide_review(
    review_id: str,
    db: DbDep,
    principal: PrincipalDep,
    approve: bool = Query(True),
    publish: bool = Query(False),
    note: str | None = Query(default=None, max_length=500),
) -> SchemeOut:
    """Approve/reject a pending review; approve+publish publishes (admin)."""
    _require_admin(principal)
    user = await _admin_user(db, principal)
    scheme = await AdminService(db).decide_review(
        user, review_id, approve=approve, note=note, publish=publish
    )
    return SchemeService(db).to_out(scheme)


@router.delete("/schemes/{code}", status_code=fastapi_status.HTTP_204_NO_CONTENT)
async def delete_scheme_admin(
    code: str,
    db: DbDep,
    principal: PrincipalDep,
) -> None:
    """Delete a scheme; published schemes must be archived first (admin)."""
    _require_admin(principal)
    user = await _admin_user(db, principal)
    await AdminService(db).delete_scheme(user, code)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@router.get("/users", response_model=AdminUsersPageOut)
async def list_users_admin(
    db: DbDep,
    principal: PrincipalDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    q: str | None = Query(default=None, max_length=120),
    role: str | None = Query(default=None, pattern="^(citizen|admin|content_editor)$"),
    status: str | None = Query(default=None, pattern="^(active|suspended|deleted)$"),
) -> dict[str, Any]:
    """User directory for admins (no sensitive profile data exposed)."""
    _require_admin(principal)
    await _admin_user(db, principal)
    service = AdminService(db)
    users, total = await service.list_users(
        page=page, page_size=page_size, q=q, role=role, status=status
    )
    return {
        "items": [
            {
                "id": str(u.id),
                "firebase_uid": u.firebase_uid,
                "role": u.role,
                "status": u.status,
                "email": u.email,
                "display_name": u.display_name,
                "preferred_language": u.preferred_language,
                "is_guest": u.is_guest,
                "created_at": u.created_at,
                "last_login_at": u.last_login_at,
            }
            for u in users
        ],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


@router.put("/users/{user_id}/role", response_model=dict)
async def set_user_role(
    user_id: str,
    db: DbDep,
    principal: PrincipalDep,
    role: str = Query(..., pattern="^(citizen|admin|content_editor)$"),
) -> dict[str, Any]:
    _require_admin(principal)
    admin = await _admin_user(db, principal)
    user = await AdminService(db).set_user_role(admin, user_id, role)
    return {"id": str(user.id), "role": user.role}


@router.put("/users/{user_id}/status", response_model=dict)
async def set_user_status(
    user_id: str,
    db: DbDep,
    principal: PrincipalDep,
    status: str = Query(..., pattern="^(active|suspended)$"),
) -> dict[str, Any]:
    _require_admin(principal)
    admin = await _admin_user(db, principal)
    user = await AdminService(db).set_user_status(admin, user_id, status)
    return {"id": str(user.id), "status": user.status}


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------


@router.get("/audit-logs", response_model=dict)
async def audit_logs(
    db: DbDep,
    principal: PrincipalDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    entity_type: str | None = Query(default=None, alias="entityType"),
    action: str | None = Query(default=None),
) -> dict[str, Any]:
    _require_admin(principal)
    await _admin_user(db, principal)
    rows, total = await AdminService(db).list_audit_logs(
        page=page, page_size=page_size, entity_type=entity_type, action=action
    )
    return {
        "items": [
            AuditLogOut(
                id=str(r.id),
                actor_id=str(r.actor_id) if r.actor_id else None,
                actor_role=r.actor_role,
                action=r.action,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                entity_code=r.entity_code,
                summary=r.summary,
                diff=r.diff,
                created_at=r.created_at,
            ).model_dump(by_alias=True)
            for r in rows
        ],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


@router.get("/feedback", response_model=dict)
async def list_feedback(
    db: DbDep,
    principal: PrincipalDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    status: str | None = Query(default=None, pattern="^(new|acknowledged|resolved|archived)$"),
) -> dict[str, Any]:
    _require_admin(principal)
    await _admin_user(db, principal)
    service = AdminService(db)
    rows, total = await service.list_feedback(page=page, page_size=page_size, status=status)
    by_status = await service.feedback_counts()
    return {
        "items": [
            FeedbackOut(
                id=str(r.id),
                user_id=str(r.user_id) if r.user_id else None,
                scheme_code=str(r.scheme_id) if r.scheme_id else None,
                rating=r.rating,
                category=r.category,
                comment=r.comment,
                language=r.language,
                status=r.status,
                created_at=r.created_at,
            ).model_dump(by_alias=True)
            for r in rows
        ],
        "page": page,
        "pageSize": page_size,
        "total": total,
        "byStatus": by_status,
    }


@router.patch("/feedback/{feedback_id}", response_model=dict)
async def update_feedback(
    feedback_id: str,
    db: DbDep,
    principal: PrincipalDep,
    feedback_status: str = Query(alias="status", pattern="^(new|acknowledged|resolved|archived)$"),
    note: str | None = Query(default=None, max_length=500),
) -> dict[str, Any]:
    _require_admin(principal)
    admin = await _admin_user(db, principal)
    fb = await AdminService(db).update_feedback(
        admin, feedback_id, status=feedback_status, note=note
    )
    return {"id": str(fb.id), "status": fb.status}


# ---------------------------------------------------------------------------
# Bulk import (architecture + preview + apply)
# ---------------------------------------------------------------------------


@router.post("/import/preview", response_model=dict)
async def preview_import(
    db: DbDep,
    principal: PrincipalDep,
    file: Annotated[UploadFile | None, File()] = None,
    payload: str | None = Query(default=None, max_length=1_000_000),
    kind: str = Query(default="scheme", pattern="^(scheme)$"),
) -> dict[str, Any]:
    """Validate rows without writing; report create vs update per code (staff)."""
    _require_staff(principal)
    await _admin_user(db, principal)
    rows = _rows_for_import(file, payload)
    return await AdminService(db).preview_import(rows, kind=kind)


@router.post("/import/apply", response_model=dict)
async def apply_import(
    db: DbDep,
    principal: PrincipalDep,
    file: Annotated[UploadFile | None, File()] = None,
    payload: str | None = Query(default=None, max_length=1_000_000),
    kind: str = Query(default="scheme", pattern="^(scheme)$"),
) -> dict[str, Any]:
    """Commit an import — creates/updates schemes, records an ImportJob (staff)."""
    _require_staff(principal)
    user = await _admin_user(db, principal)
    rows = _rows_for_import(file, payload)
    return await AdminService(db).apply_import(user, rows, kind=kind)


@router.get("/import/jobs", response_model=dict)
async def import_jobs(
    db: DbDep,
    principal: PrincipalDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    _require_admin(principal)
    await _admin_user(db, principal)
    service = AdminService(db)
    jobs, total = await service.list_import_jobs(page=page, page_size=page_size)
    return {
        "items": [
            ImportJobOut(
                id=str(j.id),
                kind=j.kind,
                filename=j.filename,
                status=j.status,
                total_rows=j.total_rows,
                imported_rows=j.imported_rows,
                failed_rows=j.failed_rows,
                errors=j.errors,
                created_at=j.created_at,
            ).model_dump(by_alias=True)
            for j in jobs
        ],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


def _rows_for_import(file: UploadFile | None, payload: str | None) -> list[dict[str, Any]]:
    if file is not None:
        return rows_from_upload(file)
    if payload:
        try:
            data = json.loads(payload)
        except (TypeError, ValueError):
            return []
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
    return []


# ---------------------------------------------------------------------------
# Citizen feedback submission (public, unauthenticated slot).
# ---------------------------------------------------------------------------


class _FeedbackCreate(APIModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    category: str | None = Field(default=None, max_length=24)
    comment: str | None = Field(default=None, max_length=2000)
    language: str | None = Field(default=None, max_length=8)
    scheme_code: str | None = Field(default=None, max_length=40)


@router.post("/feedback", response_model=dict, tags=["admin"])
async def create_feedback_public(
    payload: _FeedbackCreate,
    db: DbDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """Citizen feedback submission (any authenticated user)."""
    principal.require_role("citizen", "admin", "content_editor")
    user = await UserService(db).get_or_create_by_firebase(principal.uid)
    scheme = None
    if payload.scheme_code:
        scheme = await SchemeRepository(db).by_code(payload.scheme_code)
    from app.models.admin import Feedback as FeedbackModel

    fb = FeedbackModel(
        user_id=user.id,
        scheme_id=scheme.id if scheme else None,
        rating=payload.rating,
        category=payload.category,
        comment=payload.comment,
        language=payload.language or "en",
        status="new",
    )
    db.add(fb)
    await db.commit()
    return {"id": str(fb.id), "status": fb.status, "createdAt": fb.created_at}


# ---------------------------------------------------------------------------
# System health
# ---------------------------------------------------------------------------


@router.get("/health", response_model=dict)
async def system_health(
    db: DbDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """Run an on-demand health probe across subsystems (admin)."""
    _require_admin(principal)
    admin = await _admin_user(db, principal)
    return await AdminService(db).run_health_check(admin)
