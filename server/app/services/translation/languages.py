"""Canonical server-side language catalog (mirrors ``shared/src/domain/language.ts``).

Keeps the 13 supported BCP-47 codes, script direction and IndicTrans2 coverage
in one place so detection, translation, prompt assembly and persistence all
agree on the same list.
"""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_LANGUAGES: tuple[str, ...] = (
    "as",
    "bn",
    "en",
    "gu",
    "hi",
    "kn",
    "ml",
    "mr",
    "or",
    "pa",
    "ta",
    "te",
    "ur",
)

FALLBACK_LANGUAGE = "en"

#: RTL writing systems — currently only Urdu.
_RTL_LANGUAGES = frozenset({"ur"})

_NATIVE_NAMES: dict[str, str] = {
    "as": "অসমীয়া",
    "bn": "বাংলা",
    "en": "English",
    "gu": "ગુજરાતી",
    "hi": "हिन्दी",
    "kn": "ಕನ್ನಡ",
    "ml": "മലയാളം",
    "mr": "मराठी",
    "or": "ଓଡ଼ିଆ",
    "pa": "ਪੰਜਾਬੀ",
    "ta": "தமிழ்",
    "te": "తెలుగు",
    "ur": "اردو",
}


@dataclass(frozen=True)
class LanguageInfo:
    """Surface metadata for one supported language."""

    code: str
    native_name: str
    english_name: str
    rtl: bool
    indic_trans: bool


def is_supported(code: str) -> bool:
    """True for one of the canonical 13 codes."""
    return code in SUPPORTED_LANGUAGES


def is_rtl(code: str) -> bool:
    """True when the language is written right-to-left (Urdu)."""
    return code in _RTL_LANGUAGES


def native_name(code: str) -> str:
    return _NATIVE_NAMES.get(code, code)


def english_name(code: str) -> str:
    return {
        "as": "Assamese",
        "bn": "Bengali",
        "en": "English",
        "gu": "Gujarati",
        "hi": "Hindi",
        "kn": "Kannada",
        "ml": "Malayalam",
        "mr": "Marathi",
        "or": "Odia",
        "pa": "Punjabi",
        "ta": "Tamil",
        "te": "Telugu",
        "ur": "Urdu",
    }.get(code, code)
