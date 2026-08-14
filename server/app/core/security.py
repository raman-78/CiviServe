"""Authentication helpers: Firebase ID-token verification + role guards.

Production uses ``firebase-admin`` ``verify_id_token`` (docs/architecture/15).
In development/tests with ``DEV_BYPASS_AUTH=true`` the caller's
``X-Dev-User-Id`` header is trusted instead, so the API is testable without a
Firebase project.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Header, Request

from app.core.config import get_settings
from app.core.errors import AuthenticationError, ForbiddenError
from app.core.logging import get_logger

logger = get_logger(__name__)

#: Role claims allowed to touch admin/content endpoints.
STAFF_ROLES = {"admin", "content_editor"}


@dataclass(frozen=True)
class AuthPrincipal:
    """Decoded caller identity, independent of the Firebase payload shape."""

    uid: str
    email: str | None = None
    name: str | None = None
    phone: str | None = None
    role: str = "citizen"
    is_guest: bool = False
    email_verified: bool = False
    auth_method: str = "email"

    def require_role(self, *roles: str) -> AuthPrincipal:
        if self.role not in roles:
            raise ForbiddenError("You do not have permission to perform this action.")
        return self


def _load_firebase_app() -> Any:
    """Lazily init firebase-admin (import cost + optional dependency)."""
    from firebase_admin import credentials as firebase_creds
    from firebase_admin import initialize_app

    settings = get_settings()
    if settings.firebase_service_account_json:
        import json

        cred = firebase_creds.Certificate(json.loads(settings.firebase_service_account_json))
    elif settings.firebase_service_account_path:
        cred = firebase_creds.Certificate(settings.firebase_service_account_path)
    else:
        raise AuthenticationError("Firebase is not configured.")

    # idempotent; returns the already-created app when re-initialized
    return initialize_app(cred, options={"projectId": settings.firebase_project_id})


#: Firebase sign-in provider -> our canonical auth_method.
_SIGN_IN_PROVIDER_MAP = {
    "password": "email",
    "google.com": "google",
    "phone": "phone",
}


async def verify_id_token(token: str) -> AuthPrincipal:
    """Verify a Firebase ID token and map claims to an :class:`AuthPrincipal`."""
    from firebase_admin import auth as firebase_auth

    try:
        app = _load_firebase_app()
        decoded = firebase_auth.verify_id_token(token, app=app)
    except AuthenticationError:
        raise
    except Exception as exc:  # noqa: BLE001 — firebase wraps errors in generic exceptions
        raise AuthenticationError("Invalid or expired authentication token.") from exc

    role = decoded.get("role") or "citizen"
    provider = (decoded.get("firebase") or {}).get("sign_in_provider")
    auth_method = decoded.get("auth_method") or _SIGN_IN_PROVIDER_MAP.get(provider or "", "email")
    return AuthPrincipal(
        uid=decoded.get("uid", ""),
        email=decoded.get("email"),
        name=decoded.get("name"),
        phone=decoded.get("phone_number"),
        role=role,
        is_guest=bool(decoded.get("is_guest", False)),
        email_verified=bool(decoded.get("email_verified", False)),
        auth_method=auth_method,
    )


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    x_dev_user_id: str | None = Header(default=None),
    x_dev_user_role: str | None = Header(default=None),
) -> AuthPrincipal:
    """FastAPI dependency → current authenticated principal."""
    settings = get_settings()
    if settings.dev_bypass_auth:
        if not x_dev_user_id:
            raise AuthenticationError("DEV_BYPASS_AUTH requires an X-Dev-User-Id header.")
        role = (
            x_dev_user_role
            if x_dev_user_role in {"citizen", "admin", "content_editor"}
            else "citizen"
        )
        return AuthPrincipal(
            uid=x_dev_user_id,
            role=role,
            is_guest=x_dev_user_id.startswith("guest_"),
        )

    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise AuthenticationError("Empty bearer token.")
    return await verify_id_token(token)


async def get_optional_user(
    request: Request,
    authorization: str | None = Header(default=None),
    x_dev_user_id: str | None = Header(default=None),
) -> AuthPrincipal | None:
    """Dependency for routes that work with or without authentication."""
    settings = get_settings()
    if settings.dev_bypass_auth:
        if not x_dev_user_id:
            return None
        return AuthPrincipal(uid=x_dev_user_id, is_guest=x_dev_user_id.startswith("guest_"))
    if not authorization:
        return None
    try:
        return await get_current_user(request, authorization)
    except AuthenticationError:
        return None


async def require_staff(user: AuthPrincipal | None = None) -> AuthPrincipal:  # type: ignore[assignment]
    """Guard: reject non-staff principals (used by admin/content routes)."""
    if user is None:
        raise AuthenticationError("Authentication required.")
    return user.require_role(*STAFF_ROLES)
