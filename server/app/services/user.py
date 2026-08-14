"""User/profile domain service."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.user import User, UserProfile
from app.repositories.user_repo import ProfileRepository, UserRepository
from app.schemas.user import COMPLETION_FIELDS, UserProfileUpdate

#: Schema field -> ORM attribute for fields whose names diverge from the contract.
_FIELD_MAP = {"caste_category": "community", "education": "education_level"}


class UserService:
    """Orchestrates user + profile reads/writes; no HTTP awareness."""

    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)
        self.profiles = ProfileRepository(session)
        self.session = session

    async def get_or_create_by_firebase(
        self, firebase_uid: str, *, auth_method: str = "email"
    ) -> User:
        return await self.users.get_or_create_by_firebase(firebase_uid, auth_method=auth_method)

    async def get_by_id(self, user_id: Any) -> User:
        user = await self.users.by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    async def get_profile(self, user: User) -> tuple[User, UserProfile | None]:
        profile = await self.profiles.by_user(user.id)
        return user, profile

    async def upsert_profile(
        self, user: User, payload: UserProfileUpdate, *, source: str = "manual"
    ) -> tuple[User, UserProfile]:
        # mode="json" yields plain primitives (dicts for nested models) so the
        # JSON columns receive serializable data directly.
        data = payload.model_dump(exclude_unset=True, exclude_none=True, mode="json")
        # Treat empty optional strings as unset so they clear the column (NULL).
        data = {
            key: (None if isinstance(value, str) and not value.strip() else value)
            for key, value in data.items()
        }

        consent = data.pop("consent", None)
        accessibility = data.pop("accessibility_preferences", None)
        if consent is not None:
            user.consent_json = consent
        if "name" in data:
            user.display_name = data.pop("name")
        if "phone" in data:
            user.phone = data.pop("phone")
        if "preferred_language" in data:
            user.preferred_language = data.pop("preferred_language")

        def _apply(profile: UserProfile, key: str, value: Any) -> None:
            attr = _FIELD_MAP.get(key, key)
            if attr == "languages":
                profile.languages = value or []
            else:
                setattr(profile, attr, value)

        profile = await self.profiles.by_user(user.id)
        if profile is None:
            languages = data.pop("languages", [])
            profile = UserProfile(user_id=user.id, source=source, languages=languages or [])
            if accessibility is not None:
                profile.accessibility_json = accessibility
            for key, value in data.items():
                _apply(profile, key, value)
            self.session.add(profile)
        else:
            if accessibility is not None:
                profile.accessibility_json = accessibility
            for key, value in data.items():
                _apply(profile, key, value)

        await self.session.commit()
        await self.session.refresh(profile)
        return user, profile

    async def delete_profile(self, user: User) -> None:
        """Delete the user account + cascade (profile, chat history, saved data).

        Implements the DPDP right-to-erasure path (docs/architecture/15 §6).
        """
        await self.users.delete(user)
        await self.session.commit()

    def profile_completion(self, user: User, profile: UserProfile | None) -> dict[str, Any]:
        """Completion indicator over the canonical required field list."""
        completed: list[str] = []
        for field in COMPLETION_FIELDS:
            if _is_present(self._field_value(user, profile, field)):
                completed.append(field)
        missing = [f for f in COMPLETION_FIELDS if f not in completed]
        percent = round(len(completed) / len(COMPLETION_FIELDS) * 100)
        return {
            "percent": percent,
            "is_complete": not missing,
            "completed_fields": completed,
            "missing_fields": missing,
        }

    @staticmethod
    def _field_value(user: User, profile: UserProfile | None, field: str) -> Any:
        if field == "name":
            return user.display_name
        if field == "phone":
            return user.phone
        if profile is None:
            return None
        if field == "languages":
            return profile.languages
        key = re.sub(r"(?<!^)(?=[A-Z])", "_", field).lower()
        attr = _FIELD_MAP.get(key, key)
        return getattr(profile, attr, None)


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    return not (isinstance(value, (list, dict, str)) and not value)
