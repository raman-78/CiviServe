"""Pytest fixtures: SQLite test DB + FastAPI TestClient with dev-bypass auth."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

os.environ["ENV"] = "development"
os.environ["DEBUG"] = "true"
os.environ["DEV_BYPASS_AUTH"] = "true"
os.environ["LOG_LEVEL"] = "WARNING"

_TMPDIR = tempfile.mkdtemp(prefix="scheme-sathi-tests-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMPDIR}/test.db"


from app.core.config import clear_settings_cache  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

clear_settings_cache()

from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"X-Dev-User-Id": "dev-user-123"}


@pytest.fixture()
def guest_headers() -> dict[str, str]:
    return {"X-Dev-User-Id": "guest_abc"}
