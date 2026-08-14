"""Normalize the ORM user/profile onto the AI context shape.

Two maps are produced in one pass: the snake_case attributes used by the
missing-info checker, and the camelCase ones the demographic filter keys on —
so profile-correctness (age, income, flags, state) flows into both personalision
and RAG filtering without duplicating field lists.
"""

from __future__ import annotations

from typing import Any

from app.models.user import User, UserProfile

#: profile attribute name (camel) → (snake column on UserProfile/User).
_PROFILE_FIELDS: dict[str, str] = {
    "stateCode": "state_code",
    "district": "district",
    "age": "age",
    "gender": "gender",
    "incomeBand": "income_band",
    "occupation": "occupation",
    "education": "education_level",
    "annualIncome": "annual_income_inr",
    "isMinority": "is_minority",
    "isFarmer": "is_farmer",
    "isStudent": "is_student",
    "isSeniorCitizen": "is_senior_citizen",
    "isWidow": "is_widow",
    "isSelfEmployed": "is_self_employed",
    "isDisabled": "is_disabled",
    "community": "community",
}

_BOOL_FIELDS = {
    "is_minority",
    "is_farmer",
    "is_student",
    "is_senior_citizen",
    "is_widow",
    "is_self_employed",
    "is_disabled",
}


def profile_to_dict(user: User, profile: UserProfile | None) -> dict[str, Any]:
    """Flatten user + profile into the dict used across the AI pipeline."""
    out: dict[str, Any] = {}
    if profile is None:
        return out
    for camel, snake in _PROFILE_FIELDS.items():
        value = getattr(profile, snake, None)
        if value is None:
            continue
        out[camel] = value
        out[snake] = value
        if snake in _BOOL_FIELDS:
            out[snake] = bool(value)
            out[camel] = bool(value)
    if user and user.display_name:
        out["name"] = user.display_name
    if user.preferred_language:
        out["preferredLanguage"] = user.preferred_language
    return out
