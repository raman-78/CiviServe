"""Translation providers behind a small async protocol.

Environment-configurable (see ``TRANSLATION_PROVIDER``):
- ``google``    — Google Cloud Translation v2 REST (needs ``GOOGLE_TRANSLATE_API_KEY``)
- ``indictrans``— IndicTrans2 served at ``INDICTRANS_ENDPOINT`` (best for Indic pairs)
- ``identity``  — passthrough (no external service; used when nothing is configured)
- ``auto``      — IndicTrans2 when enabled, else Google when a key is set, else identity

Keys live only on the server; the frontend never sees provider credentials.
All providers are non-fatal by contract: :class:`TranslationService` swallows
failures and returns the original text.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_GOOGLE_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"


class TranslationProvider(Protocol):
    """Minimal surface every translation provider must implement."""

    name: str
    capable: bool

    async def translate(self, text: str, *, source: str, target: str) -> str: ...


class IdentityProvider:
    """Returns text unchanged; marks the pipeline as having no real provider."""

    name = "identity"
    capable = False

    async def translate(self, text: str, *, source: str, target: str) -> str:
        return text


class GoogleTranslateProvider:
    """Google Cloud Translation v2 over HTTP (api-key auth, no GCP SDK needed)."""

    name = "google-translate-v2"
    capable = True

    def __init__(self, api_key: str, *, timeout: float = 20.0) -> None:
        self.api_key = api_key
        self.timeout = timeout

    async def translate(self, text: str, *, source: str, target: str) -> str:
        params: dict[str, Any] = {"q": text, "target": target, "key": self.api_key}
        if source and source != "auto":
            params["source"] = source
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(_GOOGLE_ENDPOINT, params=params)
            response.raise_for_status()
        data = response.json()
        return str(data["data"]["translations"][0]["translatedText"])


class IndicTrans2Provider:
    """IndicTrans2 served behind a simple JSON POST endpoint.

    Request: ``{"text": ..., "source_lang": "hi", "target_lang": "ta"}``.
    Response ``translated_text`` is the canonical key; a few common variants are
    tolerated so different server wraps work.
    """

    name = "indictrans2"
    capable = True

    def __init__(self, endpoint: str, *, timeout: float = 30.0) -> None:
        self.endpoint = endpoint
        self.timeout = timeout

    async def translate(self, text: str, *, source: str, target: str) -> str:
        payload = {"text": text, "source_lang": source, "target_lang": target}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()
        data = response.json()
        for key in ("translated_text", "translatedText", "translation", "result", "output"):
            value = data.get(key)
            if value:
                return str(value)
        return ""


def get_translation_provider() -> TranslationProvider:
    """Factory: pick the provider from ``TRANSLATION_PROVIDER`` + env flags."""
    settings = get_settings()
    mode = settings.translation_provider.lower()

    if mode == "google":
        return (
            GoogleTranslateProvider(api_key=settings.google_translate_api_key)
            if settings.google_translate_api_key
            else IdentityProvider()
        )
    if mode == "indictrans":
        return (
            IndicTrans2Provider(endpoint=settings.indictrans_endpoint)
            if settings.indictrans_enabled
            else IdentityProvider()
        )
    if mode == "identity":
        return IdentityProvider()

    # auto
    if settings.indictrans_enabled and settings.indictrans_endpoint:
        return IndicTrans2Provider(endpoint=settings.indictrans_endpoint)
    if settings.google_translate_api_key:
        return GoogleTranslateProvider(api_key=settings.google_translate_api_key)
    return IdentityProvider()
