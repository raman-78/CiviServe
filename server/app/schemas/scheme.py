"""Pydantic schemas for the scheme catalog + user scheme interactions.

Field names are camelCase over the wire (via ``APIModel``), mirroring
``shared/src/domain/scheme.ts``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from app.schemas.common import APIModel

SCHEME_CATEGORIES = (
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
)
SCHEME_SCOPES = ("central", "state")
SCHEME_STATUSES = (
    "draft",
    "pending_review",
    "verified",
    "published",
    "temporarily_unavailable",
    "archived",
    "expired",
)
#: Statuses considered "live" for the public catalog (search/browse/RAG).
PUBLIC_SCHEME_STATUSES = ("published",)
SCHEME_VERIFICATION_STATUSES = ("unverified", "pending", "verified", "failed", "stale")
SCHEME_SORTS = ("relevance", "updated", "popular")


class LocalizedText(APIModel):
    en: str = Field(default="", max_length=2000)
    native: str = Field(default="", max_length=2000)


class SchemeCreate(APIModel):
    """Admin create payload. Rich fields are validated as structured JSON."""

    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Z0-9][A-Z0-9._-]*$")
    short_name: str | None = Field(default=None, max_length=80)
    name: LocalizedText
    summary: LocalizedText
    description: LocalizedText
    category: str
    sub_category: str | None = Field(default=None, max_length=60)
    ministry: str = Field(default="", max_length=120)
    department: str | None = Field(default=None, max_length=120)
    scope: Literal["central", "state"] = "central"
    state_code: str = "*"
    applicable_states: list[str] = Field(default_factory=list, max_length=40)
    target_beneficiaries: list[str] = Field(default_factory=list, max_length=50)
    benefits: list[str] = Field(default_factory=list, max_length=100)
    eligibility_rules: list[dict[str, Any]] = Field(default_factory=list)
    required_documents: list[dict[str, Any]] = Field(default_factory=list)
    application_steps: list[dict[str, Any]] = Field(default_factory=list)
    renewal_process: dict[str, Any] | None = None
    application_links: dict[str, Any] = Field(default_factory=dict)
    official_website: str | None = Field(default=None, max_length=500)
    official_application_link: str | None = Field(default=None, max_length=500)
    faqs: list[dict[str, Any]] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=100)
    scheme_status: Literal[
        "draft",
        "pending_review",
        "verified",
        "published",
        "temporarily_unavailable",
        "archived",
        "expired",
    ] = "published"
    last_verified_at: datetime | None = None
    #: Source provenance + content verification (Prompt 15 admin).
    source_name: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)
    source_type: str | None = Field(default=None, max_length=40)
    verification_status: Literal["unverified", "pending", "verified", "failed", "stale"] = (
        "unverified"
    )
    review_note: str | None = Field(default=None, max_length=500)

    @field_validator("category")
    @classmethod
    def _category_known(cls, value: str) -> str:
        if value not in SCHEME_CATEGORIES:
            raise ValueError(f"Unknown category '{value}'.")
        return value

    @field_validator("applicable_states", "tags", "keywords", mode="before")
    @classmethod
    def _strip_blank(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return value
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]


class SchemeUpdate(APIModel):
    """Admin update payload — every field optional, partial merges only."""

    short_name: str | None = Field(default=None, max_length=80)
    name: LocalizedText | None = None
    summary: LocalizedText | None = None
    description: LocalizedText | None = None
    category: str | None = None
    sub_category: str | None = Field(default=None, max_length=60)
    ministry: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    scope: Literal["central", "state"] | None = None
    state_code: str | None = None
    applicable_states: list[str] | None = None
    target_beneficiaries: list[str] | None = None
    benefits: list[str] | None = None
    eligibility_rules: list[dict[str, Any]] | None = None
    required_documents: list[dict[str, Any]] | None = None
    application_steps: list[dict[str, Any]] | None = None
    renewal_process: dict[str, Any] | None = None
    application_links: dict[str, Any] | None = None
    official_website: str | None = Field(default=None, max_length=500)
    official_application_link: str | None = Field(default=None, max_length=500)
    faqs: list[dict[str, Any]] | None = None
    keywords: list[str] | None = None
    tags: list[str] | None = None
    scheme_status: (
        Literal[
            "draft",
            "pending_review",
            "verified",
            "published",
            "temporarily_unavailable",
            "archived",
            "expired",
        ]
        | None
    ) = None
    last_verified_at: datetime | None = None
    source_name: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)
    source_type: str | None = Field(default=None, max_length=40)
    verification_status: Literal["unverified", "pending", "verified", "failed", "stale"] | None = (
        None
    )
    review_note: str | None = Field(default=None, max_length=500)

    @field_validator("category")
    @classmethod
    def _category_known(cls, value: str | None) -> str | None:
        if value is not None and value not in SCHEME_CATEGORIES:
            raise ValueError(f"Unknown category '{value}'.")
        return value


class SchemeOut(APIModel):
    id: str
    code: str
    short_name: str | None = None
    name: LocalizedText
    summary: LocalizedText
    description: LocalizedText
    category: str
    sub_category: str | None = None
    ministry: str
    department: str | None = None
    scope: str
    state_code: str
    applicable_states: list[str] = Field(default_factory=list)
    target_beneficiaries: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    eligibility_rules: list[dict[str, Any]] = Field(default_factory=list)
    required_documents: list[dict[str, Any]] = Field(default_factory=list)
    application_steps: list[dict[str, Any]] = Field(default_factory=list)
    renewal_process: dict[str, Any] | None = None
    application_links: dict[str, Any] = Field(default_factory=dict)
    official_website: str | None = None
    official_application_link: str | None = None
    helpline: str | None = None
    faqs: list[dict[str, Any]] = Field(default_factory=list)
    scheme_status: str = "published"
    last_verified_at: datetime | None = None
    source_name: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    verification_status: str = "unverified"
    review_note: str | None = None
    keywords: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    popularity: int = 0
    view_count: int = 0
    bookmark_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SchemeSummaryOut(APIModel):
    id: str
    code: str
    category: str
    scope: str
    state_code: str
    short_name: str | None = None
    name: LocalizedText
    summary: LocalizedText
    tags: list[str] = Field(default_factory=list)
    match_score: int | None = None
    popularity: int = 0


class SchemeSearchResultOut(SchemeSummaryOut):
    """Search result — summary plus a 0-100 relevance score."""


class SuggestionsOut(APIModel):
    query: str
    suggestions: list[str] = Field(default_factory=list)
    corrected: str | None = None


class TrendingOut(APIModel):
    rank: int
    scheme: SchemeSummaryOut


class BookmarkStatusOut(APIModel):
    scheme_id: str
    saved: bool
    bookmark_count: int = 0


class SavedSearchOut(APIModel):
    id: str
    query: str
    filters: dict[str, Any] = Field(default_factory=dict)
    notify_on_update: bool = False
    created_at: datetime


class SavedSearchCreate(APIModel):
    query: str = Field(min_length=1, max_length=200)
    filters: dict[str, Any] = Field(default_factory=dict)
    notify_on_update: bool = False


class SearchHistoryOut(APIModel):
    id: str
    query: str
    created_at: datetime
