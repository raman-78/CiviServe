"""Multilingual services: language detection + translation.

- :mod:`detect`      — script-based best-effort language detection.
- :mod:`terminology` — protect codes/URLs/money + loanword normalisation.
- :mod:`glossary`    — localized copy for the deterministic fallback provider.
- :mod:`providers`   — Google Translate / IndicTrans2 / identity providers.
- :mod:`service`     — :class:`TranslationService` facade for the chat pipeline.
"""

from app.services.translation.detect import Detection, detect, effective_language
from app.services.translation.service import TranslationService

__all__ = [
    "Detection",
    "TranslationService",
    "detect",
    "effective_language",
]
