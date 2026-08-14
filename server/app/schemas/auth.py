"""Auth-related schemas: guest token issuance + me endpoint.

Snake_case python fields (alias generator → camelCase JSON).
"""

from __future__ import annotations

from datetime import datetime

from app.schemas.common import APIModel


class GuestTokenRequest(APIModel):
    """POST /auth/guest — optionally carries a preferred language."""

    language: str = "en"


class GuestTokenResponse(APIModel):
    token: str
    token_type: str = "Bearer"  # noqa: S105 - not a credential, an OAuth scheme name
    expires_in_seconds: int
    user_id: str


class MeResponse(APIModel):
    user_id: str
    firebase_uid: str | None = None
    email: str | None = None
    display_name: str | None = None
    role: str = "citizen"
    is_guest: bool = False
    auth_method: str = "email"
    email_verified: bool = False
    preferred_language: str = "en"
    created_at: datetime | None = None


class RevokeResponse(APIModel):
    """POST /auth/revoke — logout from all devices."""

    revoked: bool = True
