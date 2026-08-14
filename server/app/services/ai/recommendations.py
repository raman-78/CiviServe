"""Conversation-safe scheme recommendations for the chat pipeline.

The LLM proposes recommendations and reasons in its answer; this module is the
*fallback* and *safety net* used when the model returns none (or in the
rule-based provider) — but now those fallbacks are produced by the **structured
eligibility engine** (:mod:`app.services.recommendation.engine`) over the exact
catalog the request retrieved, so the chat never invents eligibility logic. The
topic-relevance boost from the query text still applies on top of the engine
verdict so responses stay relevant without ever overriding it.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.retrieval import profile_to_demographic
from app.services.recommendation.engine import SchemeEvaluation, evaluate_scheme
from app.services.scheme import SchemeService
from app.services.translation.glossary import localize

#: category keyword boosts applied when the user's query mentions a topic.
_CATEGORY_BOOST: dict[str, tuple[str, ...]] = {
    "agriculture": ("farmer", "crop", "kisan", "land"),
    "health": ("health", "hospital", "insurance", "medical", "beema"),
    "education": ("education", "student", "school", "college", "scholarship"),
    "housing": ("house", "home", "housing", "awas", "shelter"),
    "employment": ("job", "employment", "skill", "training"),
    "social-welfare": ("pension", "widow", "disabled", "senior", "elderly"),
    "women": ("woman", "women", "mahila"),
}

_RANK: dict[str, int] = {"eligible": 3, "likely": 2, "needs_more_info": 1, "not_eligible": 0}


class RecommendationService:
    """Engine-driven fallback recommendations for a chat turn."""

    def __init__(self, session: AsyncSession) -> None:
        self.schemes = SchemeService(session)

    async def recommend(
        self,
        *,
        query: str,
        profile: dict[str, Any] | None = None,
        exclude_codes: list[str] | None = None,
        limit: int = 3,
        language: str = "en",
    ) -> list[dict[str, str]]:
        """Top engine-verified recommendations (ranked), with rule-grounded reasons."""
        profile = profile or {}
        exclude = set(exclude_codes or ())
        query_lower = query.lower()
        demographic = profile_to_demographic(profile)

        scored: list[tuple[int, float, int, str, SchemeEvaluation, Any]] = []
        for scheme in await self.schemes.repo.all_public():
            if scheme.code in exclude:
                continue
            verdict = evaluate_scheme(scheme.eligibility_rules or [], profile)
            if verdict.status == "not_eligible":
                continue  # conclusively excluded — never surface in the fallback
            boost = 0.0
            for category, keywords in _CATEGORY_BOOST.items():
                if category == scheme.category and any(k in query_lower for k in keywords):
                    boost += 40
                    break
            total = verdict.match_score + boost + (scheme.popularity or 0) / 100.0
            scored.append(
                (_RANK[verdict.status], total, -scheme.popularity, scheme.code, verdict, scheme)
            )

        scored.sort(key=lambda row: (-row[0], -row[1], -row[2], row[3]))
        out: list[dict[str, str]] = []
        for _rank, _total, _pop, _code, verdict, scheme in scored[:limit]:
            out.append(
                {
                    "code": scheme.code,
                    "name": scheme.name_en,
                    "category": scheme.category,
                    "reason": (
                        verdict.reasons[0]
                        if verdict.reasons
                        else _reason(scheme, demographic, language)
                    ),
                }
            )
        return out


def _reason(scheme: Any, demographic: dict[str, Any], language: str = "en") -> str:
    if demographic.get("is_senior_citizen"):
        return localize("reason_senior", language)
    if demographic.get("age"):
        return localize("reason_age", language)
    if demographic.get("state"):
        return localize("reason_state", language)
    return localize("reason_general", language)
