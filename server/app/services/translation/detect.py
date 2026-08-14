"""Best-effort language detection from Unicode script ranges.

The catalog has exactly one language per Indic script except Devanagari
(hi/mr) and Bengali (bn/as), which share scripts — those pairs get a light
word-marker heuristic and otherwise fall back to the more common language.
Latin text (English, romanized Hinglish) is reported as ``en``; callers
should prefer the client-declared language for romanized input.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.translation.languages import FALLBACK_LANGUAGE, is_supported

#: Unicode block start..end (inclusive) → default language for that script.
_SCRIPT_RANGES: tuple[tuple[int, int, str], ...] = (
    (0x0600, 0x06FF, "ur"),  # Arabic (Urdu)
    (0x0750, 0x077F, "ur"),  # Arabic supplement
    (0xFB50, 0xFDFF, "ur"),  # Arabic presentation forms-A
    (0xFE70, 0xFEFF, "ur"),  # Arabic presentation forms-B
    (0x0900, 0x097F, "hi"),  # Devanagari (hi / mr)
    (0x0980, 0x09FF, "bn"),  # Bengali (bn / as)
    (0x0A00, 0x0A7F, "pa"),  # Gurmukhi (Punjabi)
    (0x0A80, 0x0AFF, "gu"),  # Gujarati
    (0x0B00, 0x0B7F, "or"),  # Odia
    (0x0B80, 0x0BFF, "ta"),  # Tamil
    (0x0C00, 0x0C7F, "te"),  # Telugu
    (0x0C80, 0x0CFF, "kn"),  # Kannada
    (0x0D00, 0x0D7F, "ml"),  # Malayalam
)

#: Devanagari word markers used to split Hindi vs Marathi.
_MR_MARKERS = ("आहे", "आहोत", "नाही", "वाटते", "होते")
_HI_MARKERS = ("हैं", "है ", "नहीं", "में ", "हूँ")

#: Bengali-script markers used to split Assamese vs Bengali.
_AS_MARKERS = ("আপুনি", "অসম", "কেনেকৈ", "লগত", "বিচাৰি")
_BN_MARKERS = ("আপনি", "আছে", "কী", "আমি")

_LATIN_START, _LATIN_END = 0x0041, 0x024F


@dataclass(frozen=True)
class Detection:
    """Result of analysing one piece of text."""

    language: str
    confidence: float
    script: str
    mixed: bool = False


def detect(text: str) -> Detection:
    """Detect the dominant written language from the text's script ranges."""
    counts = _script_counts(text)
    if not counts:
        return Detection(language=FALLBACK_LANGUAGE, confidence=0.0, script="latin")
    total = sum(counts.values())
    dominant_lang, dominant_count = max(counts.items(), key=lambda item: item[1])
    confidence = dominant_count / total if total else 0.0

    language = dominant_lang
    if language == "hi":
        language = _refine_devanagari(text)
    elif language == "bn":
        language = _refine_bengali(text)

    # Mixed when at least two scripts appear with a meaningful number of chars
    # (e.g. "தமிழ் schemes for farmers" mixes Tamil + Latin).
    mixed = len([count for count in counts.values() if count >= 2]) > 1
    return Detection(language=language, confidence=confidence, script=dominant_lang, mixed=mixed)


def effective_language(text: str, preferred: str | None = None) -> str:
    """Detected language for non-Latin input; otherwise the declared preference.

    ``preferred`` is the language the client/user selected (e.g. the profile
    ``preferredLanguage``). It wins for Latin-script input (including romanized
    Hinglish) so replies follow the user's declared choice; real Indic script
    always overrides it.
    """
    detection = detect(text)
    if detection.language == FALLBACK_LANGUAGE and preferred and is_supported(preferred):
        return preferred
    return detection.language


def _script_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for char in text:
        codepoint = ord(char)
        for start, end, lang in _SCRIPT_RANGES:
            if start <= codepoint <= end:
                counts[lang] = counts.get(lang, 0) + 1
                break
        else:
            if _LATIN_START <= codepoint <= _LATIN_END:
                counts["en"] = counts.get("en", 0) + 1
    return counts


def _refine_devanagari(text: str) -> str:
    if any(marker in text for marker in _MR_MARKERS):
        return "mr"
    return "hi"


def _refine_bengali(text: str) -> str:
    if any(marker in text for marker in _AS_MARKERS):
        return "as"
    return "bn"
