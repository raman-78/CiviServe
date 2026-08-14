"""Terminology layer: what must never be mangled by machine translation.

Before translating (in either direction) we swap scheme codes, URLs, emails,
phones, currency amounts and plain numbers for numbered placeholders, translate
the rest, then restore the originals — so official names, government links,
scheme IDs and ₹ figures always survive verbatim. Also carries a small
loanword map used to normalise common Indian-language terms towards English
for retrieval when no translation provider is configured.
"""

from __future__ import annotations

import re

#: Scheme codes look like "PM-KISAN", "IGNOAPS", "KA-RAITHA".
_CODE_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b")
_URL_RE = re.compile(r"https?://[^\s]+")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"\+?\d[\d\s-]{8,}\d")
_MONEY_RE = re.compile(r"₹\s?\d[\d,]*(?:\.\d+)?")
_NUMBER_RE = re.compile(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?(?![A-Za-z])")

#: Match greediest first so a URL is protected before the numbers inside it.
_PATTERNS = (_URL_RE, _EMAIL_RE, _MONEY_RE, _CODE_RE, _PHONE_RE, _NUMBER_RE)

#: English loanwords often written in Indic scripts that map onto catalog terms.
LOANWORDS: dict[str, str] = {
    "योजना": "scheme",
    "किसान": "farmer",
    "विद्यार्थी": "student",
    "छात्र": "student",
    "महिला": "women",
    "पेंशन": "pension",
    "आवास": "housing",
    "स्वास्थ्य": "health",
    "शिक्षा": "education",
    "बीमा": "insurance",
    "निवृत्ति": "pension",
    "అర్జీ": "application",
    "பொருளாதார": "income",
}


class ProtectedText:
    """A string whose untranslatable spans were swapped for placeholders."""

    def __init__(self, text: str, tokens: list[tuple[str, str]]) -> None:
        self.text = text
        self.tokens = tokens

    def restore(self, translated: str | None = None) -> str:
        """Put the original spans back into ``translated`` (default: the input).

        The provider output (``translated``) carries ``[n]`` placeholders for the
        protected spans; this swaps them back to the exact original text. With no
        argument it returns the original input untouched.
        """
        result = self.text if translated is None else translated
        for placeholder, original in self.tokens:
            result = result.replace(placeholder, original)
        return result


def protect(text: str) -> ProtectedText:
    """Replace protected spans with ``[n]`` placeholders before translation."""
    spans: list[tuple[int, int, str]] = []
    for pattern in _PATTERNS:
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end(), match.group(0)))
    spans.sort(key=lambda span: (span[0], -(span[1] - span[0])))

    tokens: list[tuple[str, str]] = []
    parts: list[str] = []
    cursor = 0
    for index, (start, end, value) in enumerate(spans):
        if start < cursor:
            continue
        parts.append(text[cursor:start])
        placeholder = f"[{index}]"
        tokens.append((placeholder, value))
        parts.append(placeholder)
        cursor = end
    parts.append(text[cursor:])
    return ProtectedText("".join(parts), tokens)


def normalise_query(text: str) -> str:
    """Best-effort loanword normalisation for retrieval on untranslated text.

    Non-destructive: only replaces known words/phrases and collapses
    whitespace; anything unknown is left untouched so the caller can fall
    back to the original.
    """
    lowered = text.lower()
    for indic, english in LOANWORDS.items():
        lowered = lowered.replace(indic.lower(), english)
    return re.sub(r"\s+", " ", lowered).strip()
