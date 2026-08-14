"""Application settings via pydantic-settings, mirroring server/.env.example."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Values come from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    app_name: str = "civiserve-server"
    version: str = "0.1.0"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:4173"]

    # --- Database (async engine, PostgreSQL in prod) ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/civiserve"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 1800

    # --- Redis (rate limiting + cache + queues). Optional for MVP. ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Firebase Authentication ---
    firebase_project_id: str = ""
    firebase_service_account_path: str = ""
    firebase_service_account_json: str = ""
    # Dev-only: skip real Firebase verification and trust the caller UID header.
    dev_bypass_auth: bool = False

    # --- Gemini (AI, wired in a later prompt) ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    gemini_temperature: float = 0.3
    gemini_max_output_tokens: int = 1024
    gemini_timeout_seconds: int = 30
    gemini_cache_enabled: bool = True
    gemini_cache_ttl_seconds: int = 86400
    #: Failed provider calls are retried up to this many extra attempts.
    gemini_retry_attempts: int = 2
    gemini_retry_min_delay_seconds: float = 0.8

    # --- AI chat pipeline ---
    rag_top_k: int = 6
    chat_context_message_limit: int = 30
    chat_context_max_chars: int = 6000
    chat_auto_title_max_chars: int = 50

    # --- Translation (IndicTrans2 preferred, Google fallback) ---
    #: auto | google | indictrans | identity — auto picks IndicTrans2 → Google → identity.
    translation_provider: Literal["auto", "google", "indictrans", "identity"] = "auto"
    indictrans_enabled: bool = False
    indictrans_endpoint: str = "http://localhost:8100/translate"
    indictrans_model_dir: str = "/models/indic-trans"
    google_translate_api_key: str = ""
    translation_cache_ttl_seconds: int = 604800

    # --- Speech / OCR / storage (future prompts) ---
    google_speech_language_hint: str = "hi-IN"
    paddleocr_endpoint: str = ""
    gcs_bucket: str = ""

    # --- Documents (Prompt 11) ---
    #: Private storage root for uploaded documents. Never served statically.
    document_storage_dir: str = "storage/documents"
    #: Maximum upload size in bytes (default 10 MB).
    document_max_size_bytes: int = 10 * 1024 * 1024
    #: Allowed file extensions (server-side validation, not just client-side).
    document_accepted_formats: str = "pdf,jpg,jpeg,png"
    #: SHA-256 integrity checks are kept when this is enabled.
    document_store_checksum: bool = True

    # --- Observability ---
    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""

    # --- Rate limiting ---
    rate_limit_max_per_minute: int = 60
    rate_limit_max_per_user_per_hour: int = 300
    ai_endpoint_rate_limit_max_per_minute: int = 20
    #: Search endpoints are cheaper-but-noisy; cap them tighter than the global limit.
    scheme_search_rate_limit_per_minute: int = 30

    # --- Scheme catalog caching ---
    scheme_cache_ttl_seconds: int = 300
    scheme_cache_max_entries: int = 512

    # --- Maps / location (maps-locator prompt) ---
    #: osm | google — drives the external-directions links and tile selection.
    maps_provider: Literal["osm", "google"] = "osm"
    #: Radius presets surfaced by the UI (km), mirror of the shared contract.
    center_radius_presets: str = "5,10,25,50"
    #: Default search radius when the client does not send one.
    center_default_radius_km: float = 10.0
    #: Cache TTL for centre scans (never the anchor — one-shot only).
    center_scan_cache_ttl_seconds: int = 300

    # --- Security ---
    no_ai_path_prefixes: str = "/healthz,/metrics"

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @model_validator(mode="after")
    def _lock_down_production_security(self) -> Settings:
        """Never allow the dev auth bypass in production, however it is set."""
        if self.env == "production":
            self.dev_bypass_auth = False
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return self.cors_origins

    @property
    def no_ai_prefixes(self) -> list[str]:
        return [p.strip() for p in self.no_ai_path_prefixes.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton (dependency-injectable, overrideable in tests)."""
    return Settings()


def clear_settings_cache() -> None:
    """Drop the cached settings (used by tests after monkeypatching env)."""
    get_settings.cache_clear()
