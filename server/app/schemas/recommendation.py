"""Pydantic schemas for the eligibility recommendation API (Prompt 10).

Field names are camelCase over the wire (via ``APIModel``), mirroring
``shared/src/domain/recommendation.ts``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from app.schemas.common import APIModel
from app.schemas.scheme import SchemeSummaryOut


class RecommendationRequest(APIModel):
    """Profile facts the engine evaluates (every field optional; camelCase JSON)."""

    state_code: str | None = Field(default=None, max_length=8)
    district: str | None = Field(default=None, max_length=80)
    age: int | None = Field(default=None, ge=0, le=130)
    gender: str | None = Field(default=None, max_length=20)
    income_band: str | None = Field(default=None, max_length=20)
    annual_income_inr: int | None = Field(default=None, ge=0)
    education: str | None = Field(default=None, max_length=30)
    occupation: str | None = Field(default=None, max_length=40)
    caste_category: str | None = Field(default=None, max_length=20)
    is_farmer: bool | None = None
    is_student: bool | None = None
    is_disabled: bool | None = None
    is_minority: bool | None = None
    is_senior_citizen: bool | None = None
    is_self_employed: bool | None = None
    is_widow: bool | None = None
    is_women: bool | None = None
    limit: int = Field(default=10, ge=1, le=50)

    @field_validator(
        "gender",
        "income_band",
        "education",
        "occupation",
        "caste_category",
        mode="after",
    )
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            value = value.strip().lower()
        return value

    def to_profile(self) -> dict[str, Any]:
        """Flatten into the snake_case profile dict the engine reads."""
        data = self.model_dump(exclude_unset=True, exclude_none=True)
        data.pop("limit", None)
        if "caste_category" in data:
            data["community"] = data.pop("caste_category")
        if "annual_income_inr" in data:
            data["annual_income_inr"] = int(data["annual_income_inr"])
        return data

    @property
    def requested_limit(self) -> int:
        return self.limit


class RecommendationOut(APIModel):
    """One scheme's engine verdict, enriched with its reference for rendering."""

    scheme_id: str
    scheme: SchemeSummaryOut
    status: Literal["eligible", "likely", "needs_more_info", "not_eligible"]
    match_score: float
    matched_rules: list[dict[str, Any]] = Field(default_factory=list)
    broken_rules: list[dict[str, Any]] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    fully_eligible: bool


class RecommendationBatchOut(APIModel):
    """Batch evaluation response (docs recommendation.ts `RecommendationResponse`)."""

    recommendations: list[RecommendationOut]
    missing_fields: list[str] = Field(default_factory=list)


class MissingFieldsOut(APIModel):
    """Fields the candidate schemes need but the profile doesn't cover yet."""

    missing_fields: list[str] = Field(default_factory=list)
