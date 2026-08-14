"""Admin dashboard DTOs (Prompt 15).

All admin responses stay in the ``{error,...}`` envelope for errors and use the
camelCase ``APIModel`` convention over the wire.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import APIModel

SchemeStatus = Literal[
    "draft",
    "pending_review",
    "verified",
    "published",
    "temporarily_unavailable",
    "archived",
    "expired",
]
VerificationStatus = Literal["unverified", "pending", "verified", "failed", "stale"]


# -- Overview / heartbeats ---------------------------------------------------


class AdminStatsOut(APIModel):
    scheme_total: int = 0
    scheme_published: int = 0
    scheme_draft: int = 0
    scheme_pending_review: int = 0
    scheme_archived: int = 0
    expired: int = 0
    temporarily_unavailable: int = 0
    user_total: int = 0
    users_last_30d: int = 0
    published_percent: float = 0.0
    pending_approvals: int = 0
    new_feedback: int = 0
    scheme_versions_count: int = 0
    last_verified_at: datetime | None = None


class SchemeStatusCountOut(APIModel):
    status: str
    count: int


class AdminOverviewOut(APIModel):
    stats: AdminStatsOut
    by_status: list[SchemeStatusCountOut]
    published_categories: list[dict[str, Any]] = Field(default_factory=list)


# -- scheme management -------------------------------------------------------


class AdminSchemeOut(APIModel):
    """Compact admin list/detail row for a scheme."""

    id: str
    code: str
    short_name: str | None = None
    name_en: str
    name_native: str = ""
    category: str
    sub_category: str | None = None
    ministry: str = ""
    department: str | None = None
    scope: str
    state_code: str = "*"
    scheme_status: str = "draft"
    verification_status: str = "unverified"
    source_name: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    review_note: str | None = None
    last_verified_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    popularity: int = 0
    view_count: int = 0
    bookmark_count: int = 0
    version_number: int | None = None
    duplicate_names: list[str] = Field(default_factory=list)


class SchemeAdminPageOut(APIModel):
    items: list[AdminSchemeOut]
    page: int
    page_size: int
    total: int


class SchemeStatusUpdate(APIModel):
    status: SchemeStatus
    note: str | None = Field(default=None, max_length=500)


class SchemeReviewRequest(APIModel):
    note: str | None = Field(default=None, max_length=500)


class SchemeReviewDecision(APIModel):
    approve: bool
    note: str | None = Field(default=None, max_length=500)
    #: When approving, optionally publish straight to the public catalog.
    publish: bool = False


class SchemeOutAdminDetail(APIModel):
    scheme: AdminSchemeOut
    duplicate_ids: list[str] = Field(default_factory=list)


# -- versions / audit / review queue ----------------------------------------


class SchemeVersionOut(APIModel):
    id: str
    scheme_id: str
    version_number: int
    changes: list[Any] = Field(default_factory=list)
    reason: str | None = None
    author: str | None = None
    created_at: datetime
    updated_at: datetime


class AuditLogOut(APIModel):
    id: str
    actor_id: str | None = None
    actor_role: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    entity_code: str | None = None
    summary: str | None = None
    diff: dict[str, Any] | None = None
    created_at: datetime


class ReviewQueueOut(APIModel):
    id: str
    scheme_id: str
    scheme_code: str
    status: str
    from_status: str | None = None
    request_note: str | None = None
    note: str | None = None
    requester_id: str | None = None
    reviewer_id: str | None = None
    created_at: datetime


# -- user management ---------------------------------------------------------


class AdminUserOut(APIModel):
    id: str
    firebase_uid: str | None = None
    role: str
    status: str
    email: str | None = None
    display_name: str | None = None
    preferred_language: str = "en"
    is_guest: bool = False
    created_at: datetime | None = None
    last_login_at: datetime | None = None


class AdminUsersPageOut(APIModel):
    items: list[AdminUserOut]
    page: int
    page_size: int
    total: int


class RoleUpdate(APIModel):
    role: Literal["citizen", "admin", "content_editor"]


class UserStatusUpdate(APIModel):
    status: Literal["active", "suspended"]


# -- bulk import -------------------------------------------------------------


class ImportPreviewRowOut(APIModel):
    row: int
    code: str | None = None
    name: str | None = None
    error: str | None = None
    will_create: bool = False
    will_update: bool = False


class ImportPreviewOut(APIModel):
    kind: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[ImportPreviewRowOut]


class ImportResultOut(APIModel):
    job_id: str
    kind: str
    imported_rows: int
    failed_rows: int
    errors: list[Any] = Field(default_factory=list)


class ImportJobOut(APIModel):
    id: str
    kind: str
    filename: str | None = None
    status: str
    total_rows: int = 0
    imported_rows: int = 0
    failed_rows: int = 0
    errors: list[Any] = Field(default_factory=list)
    created_at: datetime


class ImportJobsPageOut(APIModel):
    items: list[ImportJobOut]
    page: int
    page_size: int
    total: int


# -- feedback ----------------------------------------------------------------


class FeedbackOut(APIModel):
    id: str
    user_id: str | None = None
    scheme_code: str | None = None
    rating: int | None = None
    category: str | None = None
    comment: str | None = None
    language: str | None = None
    status: str
    created_at: datetime


class FeedbackListOut(APIModel):
    items: list[FeedbackOut]
    page: int
    page_size: int
    total: int
    by_status: dict[str, int] = Field(default_factory=dict)


class FeedbackUpdate(APIModel):
    status: Literal["new", "acknowledged", "resolved", "archived"]
    note: str | None = Field(default=None, max_length=500)


# -- system health -----------------------------------------------------------


class HealthCheckOut(APIModel):
    component: str
    status: str
    latency_ms: int | None = None
    message: str | None = None
    checked_at: datetime
