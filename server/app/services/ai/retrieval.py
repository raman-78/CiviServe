"""RAG over the scheme catalog: retrieve a bounded, relevant context per turn.

Reuses :class:`SchemeService`'s hybrid scoring (keyword + fuzzy + demographic
"not obviously excluded") so the chat grounding agrees with the search rails.
The catalog is loaded once per request — the dataset is small and the request
path is already the hot one; a vector/tsvector index can slot in later without
changing the contract (see docs/database/06).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheme import Scheme
from app.services.ai.providers import SchemeRef
from app.services.scheme import SchemeService

#: Profile keys accepted by the demographic "not obviously excluded" filter.
_DEMOGRAPHIC_KEYS = (
    "gender",
    "incomeBand",
    "occupation",
    "education",
    "isWomen",
    "is_farmer",
    "is_student",
    "is_disabled",
    "is_minority",
    "is_senior_citizen",
    "is_self_employed",
    "is_widow",
)


def scheme_to_ref(scheme: Scheme) -> SchemeRef:
    """Project a full ORM scheme onto the compact JSON-safe grounding ref."""
    return SchemeRef(
        id=str(scheme.id),
        code=scheme.code,
        name_en=scheme.name_en,
        category=scheme.category,
        sub_category=scheme.sub_category,
        summary_en=scheme.summary_en,
        benefits=tuple(scheme.benefits or []),
        eligibility_rules=tuple(scheme.eligibility_rules or []),
        required_documents=tuple(scheme.required_documents or []),
        application_steps=tuple(scheme.application_steps or []),
        official_website=scheme.official_website,
        last_verified_at=scheme.last_verified_at,
    )


def profile_to_demographic(profile: dict[str, Any]) -> dict[str, Any]:
    """Map a normalized profile onto the scheme-filter parameter names.

    ``age`` becomes ``ageMin``/``ageMax`` (the same keys the browse/search API
    accept); boolean flags and demographic enums pass through as-is.
    """
    params: dict[str, Any] = {}
    for key in _DEMOGRAPHIC_KEYS:
        if key in profile and profile[key] is not None:
            params[key] = profile[key]
    state = profile.get("stateCode") or profile.get("state_code")
    if state:
        params["state"] = str(state)
    age = profile.get("age")
    if isinstance(age, (int, float)):
        params["ageMin"] = int(age)
        params["ageMax"] = int(age)
    return params


class RetrievalService:
    """Retrieve top-k schemes + their compact refs for one chat turn."""

    def __init__(self, session: AsyncSession) -> None:
        self.schemes = SchemeService(session)

    async def retrieve(
        self,
        query: str,
        *,
        profile: dict[str, Any] | None = None,
        top_k: int = 6,
    ) -> list[SchemeRef]:
        profile = profile or {}
        demographic = profile_to_demographic(profile)
        items, _ = await self.schemes.search(
            q=query,
            page=1,
            page_size=top_k,
            sort="relevance",
            filters=demographic or None,
        )
        if not items:
            # Generic/greeting turns produce no keyword hits; default to popular.
            all_schemes = await self.schemes.repo.all_public()
            popular = sorted(all_schemes, key=lambda s: s.view_count, reverse=True)
            return [scheme_to_ref(s) for s in popular[:top_k]]
        return [scheme_to_ref(scheme) for scheme, _score in items][:top_k]
