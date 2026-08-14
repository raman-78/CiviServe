"""Production-hardening tests (Prompt 14): docs hidden, dev-bypass locked out."""

from __future__ import annotations

import pytest
from app.core.config import Settings, clear_settings_cache, get_settings


def test_dev_bypass_forced_off_in_production() -> None:
    """DEV_BYPASS_AUTH must be disabled whenever ENV=production."""
    clear_settings_cache()
    settings = Settings(env="production", dev_bypass_auth=True)
    assert settings.is_production
    assert settings.dev_bypass_auth is False


def test_dev_bypass_honoured_outside_production() -> None:
    """The bypass stays available for development/test runs."""
    clear_settings_cache()
    settings = Settings(env="development", dev_bypass_auth=True)
    assert settings.dev_bypass_auth is True


def test_production_docs_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    """Swagger docs/OpenAPI must not be served in production."""
    prod_settings = Settings(env="production")
    assert prod_settings.is_production
    clear_settings_cache()
    monkeypatch.setattr("app.core.config.get_settings", lambda: prod_settings)
    monkeypatch.setattr("app.main.get_settings", lambda: prod_settings)
    from app.main import create_app

    prod_app = create_app()
    assert prod_app.docs_url is None
    assert prod_app.redoc_url is None
    assert prod_app.openapi_url is None


def test_runtime_env_not_production() -> None:
    """Sanity: the running app under test uses the dev environment."""
    assert get_settings().env != "production"
