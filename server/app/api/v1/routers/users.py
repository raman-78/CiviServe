"""User profile endpoints (authenticated)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db
from app.core.security import AuthPrincipal, get_current_user
from app.models.user import User, UserProfile
from app.schemas.user import ProfileCompletionOut, UserProfileOut, UserProfileUpdate
from app.services.user import UserService

router = APIRouter(tags=["users"], prefix="/users")

DbDep = Annotated[AsyncSession, Depends(get_db)]
PrincipalDep = Annotated[AuthPrincipal, Depends(get_current_user)]


def _profile_to_out(user: User, profile: UserProfile) -> UserProfileOut:
    return UserProfileOut(
        id=str(profile.id),
        firebase_uid=user.firebase_uid,
        name=user.display_name,
        phone=user.phone,
        state_code=profile.state_code,
        district=profile.district,
        age=profile.age,
        gender=profile.gender,
        income_band=profile.income_band,
        caste_category=profile.community,
        education=profile.education_level,
        occupation=profile.occupation,
        is_student=profile.is_student,
        is_farmer=profile.is_farmer,
        is_minority=profile.is_minority,
        is_disabled=profile.is_disabled,
        disability_type=profile.disability_type,
        marital_status=profile.marital_status,
        preferred_language=user.preferred_language,
        preferred_input_method=profile.preferred_input_method,
        preferred_output_method=profile.preferred_output_method,
        notification_preference=profile.notification_preference,
        languages=profile.languages or [],
        accessibility_preferences=profile.accessibility_json or {},
        consent=user.consent_json or {},
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _empty_profile_out(user: User) -> UserProfileOut:
    now = datetime.now(UTC)
    return UserProfileOut(
        id=str(user.id), firebase_uid=user.firebase_uid, created_at=now, updated_at=now
    )


@router.get("/me/profile", response_model=UserProfileOut)
async def get_my_profile(
    principal: PrincipalDep,
    db: DbDep,
) -> UserProfileOut:
    """Return the caller's stored profile."""
    service = UserService(db)
    user = await service.get_or_create_by_firebase(principal.uid)
    _, profile = await service.get_profile(user)
    if profile is None:
        # Return an empty profile shell rather than a 404 so the client can
        # hydrate it with a PUT.
        return _empty_profile_out(user)
    return _profile_to_out(user, profile)


@router.get("/me/profile/completion", response_model=ProfileCompletionOut)
async def get_my_profile_completion(
    principal: PrincipalDep,
    db: DbDep,
) -> ProfileCompletionOut:
    """Return the caller's profile completion indicator."""
    service = UserService(db)
    user = await service.get_or_create_by_firebase(principal.uid)
    _, profile = await service.get_profile(user)
    return ProfileCompletionOut(**service.profile_completion(user, profile))


@router.put("/me/profile", response_model=UserProfileOut)
async def update_my_profile(
    payload: UserProfileUpdate,
    principal: PrincipalDep,
    db: DbDep,
) -> UserProfileOut:
    """Create or update the caller's profile (citizen-facing subset)."""
    service = UserService(db)
    user = await service.get_or_create_by_firebase(principal.uid)
    user, profile = await service.upsert_profile(user, payload)
    return _profile_to_out(user, profile)


@router.delete("/me/profile", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_profile(
    principal: PrincipalDep,
    db: DbDep,
) -> None:
    """Permanently delete the caller's account and cascading data (right to erasure)."""
    service = UserService(db)
    user = await service.get_or_create_by_firebase(principal.uid)
    await service.delete_profile(user)
