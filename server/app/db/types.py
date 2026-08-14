"""DB types shared across models (JSON/CITEXT variants)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import CITEXT as PgCITEXT
from sqlalchemy.dialects.postgresql import JSONB


def json_type() -> Any:
    """JSONB on PostgreSQL, generic JSON elsewhere (SQLite-compatible for tests)."""
    return JSON().with_variant(JSONB, "postgresql")


def citext_type(length: int | None = None) -> Any:
    """Case-insensitive text: PostgreSQL CITEXT, plain VARCHAR elsewhere."""
    base: String = String(length) if length else String()
    return base.with_variant(PgCITEXT(), "postgresql")
