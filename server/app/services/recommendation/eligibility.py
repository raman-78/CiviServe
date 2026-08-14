"""Eligibility orchestration service (Prompt 10).

Runs the pure engine (:mod:`app.services.recommendation.engine`) over the public
scheme catalog, ranks by verdict/matching, exposes the progressive-questioning
missing-fields list, finds not-eligible alternatives, and snapshots results to
``user_eligibility_results`` for authenticated users (best-effort).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.eligibility import UserEligibilityResult
from app.schemas.recommendation import RecommendationOut
from app.services.recommendation.engine import ENGINE_VERSION, evaluate_scheme
from app.services.scheme import SchemeService

#: priority order used to sort mixed-status batches.
_RANK: dict[str, int] = {
    "eligible": 3,
    "likely": 2,
    "needs_more_info": 1,
    "not_eligible": 0,
}


class EligibilityService:
    """Model-agnostic evaluator bound to the scheme catalog."""

    def __init__(self, session: AsyncSession) -> None:
        self.schemes = SchemeService(session)
        self.session = session

    # ------------------------------------------------------------------ eval --

    async def evaluate(
        self,
        profile: dict[str, Any] | None = None,
        *,
        limit: int | None = None,
        include_not_eligible: bool = True,
        exclude_codes: list[str] | None = None,
    ) -> tuple[list[RecommendationOut], list[str]]:
        """Evaluate the whole public catalog for one profile (sorted, capped).

        Returns ``(recommendations, missingFields)`` mirroring
        ``shared/src/domain/recommendation.ts``.
        """
        profile = profile or {}
        exclude = set(exclude_codes or ())
        schemes = await self.schemes.repo.all_public()

        collected: list[tuple[str, float, Any, str, RecommendationOut]] = []
        missing: set[str] = set()
        for scheme in schemes:
            if scheme.code in exclude:
                continue
            state = _state_of(profile)
            if state and not self.schemes._state_applies(scheme, state):
                continue
            verdict = evaluate_scheme(scheme.eligibility_rules or [], profile)
            if verdict.status == "not_eligible" and not include_not_eligible:
                missing.update(verdict.missing_fields)
                continue
            missing.update(verdict.missing_fields)
            collected.append(
                (
                    verdict.status,
                    verdict.match_score,
                    scheme,
                    scheme.code,
                    RecommendationOut(
                        scheme_id=str(scheme.id),
                        scheme=self.schemes.to_summary(scheme),
                        status=verdict.status,
                        match_score=verdict.match_score,
                        matched_rules=verdict.matched_rules,
                        broken_rules=verdict.broken_rules,
                        missing_fields=verdict.missing_fields,
                        reasons=verdict.reasons,
                        fully_eligible=verdict.fully_eligible,
                    ),
                )
            )

        collected.sort(key=lambda row: (-_RANK[row[0]], -row[1], -row[2].popularity, row[3]))
        top = [rec for _, _, _, _, rec in collected]
        if limit is not None:
            top = top[:limit]
        return top, _ordered(missing)

    async def missing_fields(self, profile: dict[str, Any] | None = None) -> list[str]:
        """Progressive-questioning list: fields the candidate schemes still need."""
        _top, missing = await self.evaluate(profile, limit=50)
        return missing

    async def alternatives(
        self,
        code: str,
        profile: dict[str, Any] | None = None,
        *,
        limit: int = 3,
    ) -> list[RecommendationOut]:
        """For a not-eligible scheme, schemes the same blocking rule doesn't bar."""
        profile = profile or {}
        schemes = await self.schemes.repo.all_public()
        target = next((s for s in schemes if s.code == code), None)
        if target is None:
            raise NotFoundError("Scheme not found.")
        target_verdict = evaluate_scheme(target.eligibility_rules or [], profile)
        blocked_fields = {r.get("field") for r in target_verdict.broken_rules}

        candidates: list[tuple[int, int, float, str, RecommendationOut]] = []
        for scheme in schemes:
            if scheme.code == code:
                continue
            state = _state_of(profile)
            if state and not self.schemes._state_applies(scheme, state):
                continue
            verdict = evaluate_scheme(scheme.eligibility_rules or [], profile)
            if verdict.status == "not_eligible":
                continue
            rule_fields = {r.get("field") for r in (scheme.eligibility_rules or [])}
            if blocked_fields and rule_fields & blocked_fields:
                continue
            same_category = int(scheme.category == target.category)
            candidates.append(
                (
                    same_category,
                    _RANK[verdict.status],
                    verdict.match_score,
                    scheme.code,
                    RecommendationOut(
                        scheme_id=str(scheme.id),
                        scheme=self.schemes.to_summary(scheme),
                        status=verdict.status,
                        match_score=verdict.match_score,
                        matched_rules=verdict.matched_rules,
                        broken_rules=verdict.broken_rules,
                        missing_fields=verdict.missing_fields,
                        reasons=verdict.reasons,
                        fully_eligible=verdict.fully_eligible,
                    ),
                )
            )
        candidates.sort(key=lambda row: (-row[0], -row[1], -row[2], row[3]))
        return [rec for _, _, _, _, rec in candidates[:limit]]

    # ------------------------------------------------------------ persistence --

    async def record_results(
        self,
        user_id: Any,
        results: list[tuple[Any, RecommendationOut]],
        profile: dict[str, Any],
    ) -> None:
        """Replace the user's latest verdicts for the listed schemes (best-effort)."""
        from uuid import UUID

        if not results:
            return
        snapshot = {key: value for key, value in (profile or {}).items() if value is not None}
        pairs = [(UUID(str(scheme_id)), rec) for scheme_id, rec in results]
        for scheme_id, _rec in pairs:
            await self.session.execute(
                sa_delete(UserEligibilityResult).where(
                    UserEligibilityResult.user_id == user_id,
                    UserEligibilityResult.scheme_id == scheme_id,
                )
            )
        self.session.add_all(
            UserEligibilityResult(
                user_id=user_id,
                scheme_id=scheme_id,
                profile_snapshot=snapshot,
                result_status=rec.status,
                match_score=rec.match_score,
                matched_rules=rec.matched_rules,
                broken_rules=rec.broken_rules,
                engine_version=ENGINE_VERSION,
            )
            for scheme_id, rec in pairs
        )
        await self.session.commit()


def _state_of(profile: dict[str, Any]) -> str | None:
    value = profile.get("state_code") or profile.get("stateCode")
    return str(value) if value else None


def _ordered(values: set[str]) -> list[str]:
    return sorted(values)
