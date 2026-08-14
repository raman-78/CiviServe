"""Auth endpoints: guest token, me, revoke-session."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db
from app.core.config import get_settings
from app.core.security import AuthPrincipal, get_current_user
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import GuestTokenRequest, GuestTokenResponse, MeResponse, RevokeResponse
from app.services.user import UserService

router = APIRouter(tags=["auth"], prefix="/auth")

DbDep = Annotated[AsyncSession, Depends(get_db)]
PrincipalDep = Annotated[AuthPrincipal, Depends(get_current_user)]


@router.post("/guest", response_model=GuestTokenResponse)
async def create_guest(
    payload: GuestTokenRequest,
    db: DbDep,
) -> GuestTokenResponse:
    """Create an anonymous guest user and return a dev guest token.

    Prompt 3 MVP: the token is ``guest_<user_id>`` so the auth dependency can
    resolve it without Firebase. The signed-guest-token mechanism lands with the
    full Firebase wiring.
    """
    service = UserService(db)
    user = User(
        auth_method="guest",
        is_guest=True,
        preferred_language=payload.language or "en",
    )
    await service.users.add(user)
    await db.commit()

    return GuestTokenResponse(
        token=f"guest_{user.id}",
        user_id=str(user.id),
        expires_in_seconds=3600,
    )


@router.get("/me", response_model=MeResponse)
async def me(
    principal: PrincipalDep,
    db: DbDep,
) -> MeResponse:
    """Resolve the current principal to a stored user (auto-provision + sync)."""
    service = UserService(db)
    user_repo = UserRepository(db)

    if principal.is_guest and principal.uid.startswith("guest_"):
        user_id = principal.uid.removeprefix("guest_")
        try:
            user = await user_repo.by_id(uuid.UUID(user_id))
        except ValueError:
            user = None
    else:
        user = await service.get_or_create_by_firebase(
            principal.uid, auth_method=principal.auth_method
        )

    if user is None:
        user = await service.get_or_create_by_firebase(
            principal.uid, auth_method=principal.auth_method
        )

    # Sync identity metadata from the verified token onto the stored user
    # (guests have no token-derived identity — keep their guest semantics).
    if not principal.is_guest:
        user.auth_method = principal.auth_method
        user.email_verified = principal.email_verified
        if principal.email:
            user.email = principal.email
        if principal.name:
            user.display_name = principal.name
        if principal.phone:
            user.phone = principal.phone
    user.last_login_at = datetime.now(UTC)
    await db.commit()

    return MeResponse(
        user_id=str(user.id),
        firebase_uid=user.firebase_uid,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_guest=user.is_guest,
        auth_method=user.auth_method,
        email_verified=user.email_verified,
        preferred_language=user.preferred_language,
        created_at=user.created_at,
    )


@router.post("/revoke", response_model=RevokeResponse)
async def revoke_session(
    principal: PrincipalDep,
) -> RevokeResponse:
    """Log out from all devices by revoking the user's Firebase refresh tokens.

    No-ops in dev-bypass mode (no Firebase project). Client-side sign-out still
    clears the local session; this endpoint invalidates tokens server-side.
    """
    settings = get_settings()
    if not settings.dev_bypass_auth:
        from firebase_admin import auth as firebase_auth

        firebase_auth.revoke_refresh_tokens(principal.uid)
    return RevokeResponse(revoked=True)
