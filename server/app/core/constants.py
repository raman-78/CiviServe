"""App-wide constants shared across server modules.

Error codes are namespaced per docs/architecture/13 (`CHAT_`, `AUTH_`,
`USER_`, `SCHEME_`, `RATE_LIMIT_`, ...). Those live next to the exception
hierarchy in ``core.errors``; this module holds domain/application constants.
"""

from __future__ import annotations

SERVICE_NAME = "scheme-sathi-server"

DEFAULT_LANGUAGE = "en"
DEFAULT_CHANNEL = "web"
DEFAULT_ROLE = "citizen"

#: Chat session lifecycle.
SESSION_STATUSES = ("active", "closed", "archived")
MESSAGE_ROLES = ("user", "assistant", "system")
MESSAGE_STATUSES = ("queued", "processing", "complete", "failed")
MESSAGE_CONTENT_TYPES = (
    "text",
    "scheme-card",
    "scheme-list",
    "eligibility-result",
    "document-list",
    "location-card",
    "center-list",
    "application-link",
    "quick-replies",
    "image",
    "error",
)

#: Row id for "no real redis yet" staging.
DEV_GUEST_PREFIX = "guest_"
