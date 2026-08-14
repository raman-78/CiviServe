"""User + profile schemas, mirroring ``shared/src/domain/user.ts``.

Snake_case python fields (matching ORM attrs); the APIModel alias generator
emits camelCase JSON (`stateCode`, `casteCategory`, ...). ``caste_category`` maps
to the DB ``community`` column.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import APIModel

GENDERS = ("male", "female", "transgender", "prefer-not-to-say")
INCOME_BANDS = ("below-poverty", "low", "middle", "upper")
CASTE_CATEGORIES = ("general", "sc", "st", "obc", "ews")
EDUCATION_LEVELS = (
    "none",
    "primary",
    "secondary",
    "higher-secondary",
    "diploma",
    "graduate",
    "postgraduate",
    "professional",
    "other",
)
MARITAL_STATUSES = ("unmarried", "married", "widowed", "divorced", "prefer-not-to-say")
INPUT_OUTPUT_METHODS = ("text", "voice", "both")
NOTIFICATION_PREFERENCES = ("all", "essential", "none")

#: Fields counted toward profile completion (single source of truth).
COMPLETION_FIELDS = (
    "name",
    "phone",
    "stateCode",
    "district",
    "age",
    "gender",
    "incomeBand",
    "education",
    "languages",
)


class ConsentFlags(BaseModel):
    dataProcessing: bool = False
    voiceProcessing: bool = False
    locationAccess: bool = False


class AccessibilityPreferences(BaseModel):
    textOnly: bool = False
    highContrast: bool = False
    slowSpeech: bool = False


class UserProfileOut(APIModel):
    id: str
    firebase_uid: str | None = None
    name: str | None = None
    phone: str | None = None
    state_code: str | None = None
    district: str | None = None
    age: int | None = Field(default=None, ge=0, le=130)
    gender: str | None = None
    income_band: str | None = None
    caste_category: str | None = None
    education: str | None = None
    occupation: str | None = None
    is_student: bool | None = None
    is_farmer: bool | None = None
    is_minority: bool | None = None
    is_disabled: bool | None = None
    disability_type: str | None = None
    marital_status: str | None = None
    preferred_language: str | None = None
    preferred_input_method: str | None = None
    preferred_output_method: str | None = None
    notification_preference: str | None = None
    languages: list[str] = Field(default_factory=list)
    accessibility_preferences: dict = Field(default_factory=dict)
    consent: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class UserProfileUpdate(APIModel):
    """Writable subset — only what a citizen is asked to provide."""

    name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    state_code: str | None = Field(default=None, max_length=8)
    district: str | None = Field(default=None, max_length=80)
    age: int | None = Field(default=None, ge=0, le=130)
    gender: str | None = None
    income_band: str | None = None
    caste_category: str | None = None
    education: str | None = Field(default=None, max_length=30)
    occupation: str | None = Field(default=None, max_length=40)
    is_student: bool | None = None
    is_farmer: bool | None = None
    is_minority: bool | None = None
    is_disabled: bool | None = None
    disability_type: str | None = Field(default=None, max_length=60)
    marital_status: str | None = None
    preferred_language: str | None = Field(default=None, max_length=8)
    preferred_input_method: str | None = None
    preferred_output_method: str | None = None
    notification_preference: str | None = None
    languages: list[str] | None = None
    accessibility_preferences: AccessibilityPreferences | None = None
    consent: ConsentFlags | None = None


class ProfileCompletionOut(APIModel):
    """Completion indicator (GET /users/me/profile/completion)."""

    percent: int
    is_complete: bool
    completed_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
