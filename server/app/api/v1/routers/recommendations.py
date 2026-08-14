"""Eligibility recommendation endpoints (Prompt 10).

- ``POST /recommendations/evaluate``     — structured batch evaluation + ranking.
- ``POST /recommendations/missing-fields`` — progressive-questioning follow-ups.
- ``POST /recommendations/{code}/alternatives`` — schemes a failed rule doesn't bar.

Authenticated, non-guest users have the top results snapshot to
``user_eligibility_results`` (best-effort, never fails the request). This API is
rate-limited like search: it is cheap (pure rule evaluation) but noisy.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db, rate_limit_search
from app.core.config import get_settings
from app.core.security import AuthPrincipal, get_optional_user
from app.schemas.recommendation import (
    MissingFieldsOut,
    RecommendationBatchOut,
    RecommendationOut,
    RecommendationRequest,
)
from app.services.recommendation.eligibility import EligibilityService
from app.services.user import UserService

router = APIRouter(tags=["recommendations"], prefix="/recommendations")

DbDep = Annotated[AsyncSession, Depends(get_db)]
OptionalPrincipalDep = Annotated[AuthPrincipal | None, Depends(get_optional_user)]


def _persist_limit() -> int:
    return get_settings().rag_top_k


@router.post(
    "/evaluate",
    response_model=RecommendationBatchOut,
    dependencies=[Depends(rate_limit_search)],
)
async def evaluate_recommendations(
    payload: RecommendationRequest,
    principal: OptionalPrincipalDep,
    db: DbDep,
) -> RecommendationBatchOut:
    """Rank schemes for a profile using the structured eligibility engine."""
    service = EligibilityService(db)
    profile = payload.to_profile()
    recommendations, missing = await service.evaluate(profile, limit=payload.requested_limit)

    if principal and not principal.is_guest:
        user = await UserService(db).get_or_create_by_firebase(principal.uid)
        try:
            await service.record_results(
                user.id,
                [(rec.scheme_id, rec) for rec in recommendations[: _persist_limit()]],
                profile,
            )
        except Exception:  # noqa: BLE001 — persistence never fails a verdict
            await db.rollback()

    return RecommendationBatchOut(
        recommendations=recommendations[: payload.requested_limit], missing_fields=missing
    )


@router.post(
    "/missing-fields",
    response_model=MissingFieldsOut,
    dependencies=[Depends(rate_limit_search)],
)
async def missing_recommendation_fields(
    payload: RecommendationRequest,
    db: DbDep,
) -> MissingFieldsOut:
    """Fields the candidate schemes need from the profile (asks only what matters)."""
    service = EligibilityService(db)
    missing = await service.missing_fields(payload.to_profile())
    return MissingFieldsOut(missing_fields=missing)


@router.post(
    "/{code}/alternatives",
    response_model=list[RecommendationOut],
    dependencies=[Depends(rate_limit_search)],
)
async def recommend_alternatives(
    code: str,
    payload: RecommendationRequest,
    db: DbDep,
) -> list[RecommendationOut]:
    """Schemes a not-eligible scheme's blocking rule doesn't constrain."""
    service = EligibilityService(db)
    return await service.alternatives(code, payload.to_profile(), limit=payload.requested_limit)
