"""High-level translation service for the chat pipeline.

Responsibilities:
- detect the user's language (script-based, prefers the declared choice for
  romanized input),
- translate a user query to English so intent detection, fact extraction and
  RAG retrieval operate on the catalog's language,
- localize the assistant's reply back into the user's language,
- preserve scheme codes / URLs / money / numbers through every translation,
- never fail the request: providers are optional and failures degrade to the
  original text with a logged warning.

English↔English is always a no-op, and translation output is cached (the cache
is shared with the scheme rails but uses the longer translation TTL).
"""

from __future__ import annotations

import hashlib

from app.core.cache import get_cache
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.translation.detect import Detection, detect, effective_language
from app.services.translation.providers import (
    IdentityProvider,
    TranslationProvider,
    get_translation_provider,
)
from app.services.translation.terminology import normalise_query, protect

logger = get_logger(__name__)


class TranslationService:
    """Facade used by the AI pipeline; cheap to construct per request."""

    def __init__(self, provider: TranslationProvider | None = None) -> None:
        self.provider = provider or get_translation_provider()
        self.cache = get_cache()

    # ------------------------------------------------------------ detection --

    def detect(self, text: str, *, preferred: str | None = None) -> Detection:
        raw = detect(text)
        return Detection(
            language=effective_language(text, preferred),
            confidence=raw.confidence,
            script=raw.script,
            mixed=raw.mixed,
        )

    # ----------------------------------------------------------- translation --

    async def translate(self, text: str, *, source: str, target: str) -> str:
        """Translate ``text`` source→target, restoring protected spans."""
        text = (text or "").strip()
        if not text or source == target or not self.provider.capable:
            return text

        protected = protect(text)
        cache_key = self._cache_key(source, target, protected.text)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return str(cached)

        try:
            translated = await self.provider.translate(protected.text, source=source, target=target)
        except Exception as exc:  # noqa: BLE001 — providers must never break chat
            logger.warning("translation_failed", source=source, target=target, exc=str(exc)[:200])
            return protected.restore()

        result = protected.restore(translated) if translated else text
        settings = get_settings()
        self.cache.set(cache_key, result, ttl_seconds=settings.translation_cache_ttl_seconds)
        return result

    async def to_english(self, text: str, source: str) -> str:
        """Translate a user query to English (no-op for English or identity)."""
        if source == "en":
            return text
        translated = await self.translate(text, source=source, target="en")
        if translated == text:
            return normalise_query(text)
        return translated

    async def translate_answer(self, text: str, *, target: str) -> str:
        """Translate a generated reply into ``target`` when it is not already."""
        if not text or target == "en" or not self.provider.capable:
            return text
        source = effective_language(text, preferred=None)
        if source == target:
            return text
        return await self.translate(text, source=source, target=target)

    @staticmethod
    def _cache_key(source: str, target: str, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        return f"tr:{source}:{target}:{digest}"


__all__ = ["IdentityProvider", "TranslationService", "TranslationProvider"]
