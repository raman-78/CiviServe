"""Rule-based eligibility + recommendation engine (Prompt 10).

Public API:
- :func:`app.services.recommendation.engine.evaluate_scheme` — pure rule evaluator
  producing the ``Recommendation`` fields (status, matchScore, matched/broken
  rules, missingFields, reasons).
- :class:`app.services.recommendation.eligibility.EligibilityService` — catalog
  batch evaluation, missing-data interrogation and not-eligible alternatives.
"""

from __future__ import annotations

from app.services.recommendation.engine import (
    ENGINE_VERSION,
    EligibilityStatus,
    SchemeEvaluation,
    evaluate_rule,
    evaluate_scheme,
)

__all__ = [
    "ENGINE_VERSION",
    "EligibilityStatus",
    "SchemeEvaluation",
    "evaluate_rule",
    "evaluate_scheme",
]
