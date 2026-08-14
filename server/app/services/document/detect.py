"""Document-type detection from OCR text (Prompt 11).

OCR itself runs in the browser (tesseract.js) because PaddleOCR/Cloud OCR are
not configured in this MVP; the browser pushes extracted text to the server via
``POST /documents/{id}/ocr``. This module decides *which* canonical document
type the text belongs to using a keyword + regex detector, then extracts a few
high-value fields (Aadhaar number, name, DOB, PAN, voter code, ...) with
masking for display.

Design notes (docs/architecture/17):
- Detection is heuristic and explicitly *never* proves authenticity; it only
  helps the citizen label the scan.
- Sensitive extracted values are masked (``masked``) for display; the raw value
  is still stored so the review step can show it to the owner.
- Keyword lists are small and curated per type to keep the detector auditable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

# Detection verdicts (mirrors shared OcrResult.detectionCode).
DetectionCode = Literal["matched", "partial", "unrecognised", "mismatch"]

# Confidences carried into the DB (mirrors shared OcrConfidence).
OcrConfidenceT = Literal["high", "needs_review", "low"]

#: Normalised keyword → canonical code. Lower-cased, ASCII-folded.
_KEYWORDS: dict[str, tuple[str, ...]] = {
    "AADHAAR": ("aadhaar", "uidai", "unique identification", "aadhar"),
    "PAN_CARD": ("permanent account number", "income tax department", "p.a.n.", "pan card"),
    "RATION_CARD": (
        "ration card",
        "food security",
        "pds",
        "fair price shop",
        "nf rations",
        "rationcrd",
    ),
    "BANK_PASSBOOK": ("passbook", "savings account", "account number", "ifsc", "bank branch"),
    "BANK_ACCOUNT": ("account number", "ifsc code", "beneficiary", "micro atm"),
    "INCOME_CERTIFICATE": ("income certificate", "annual income", "domicile", "income cert"),
    "COMMUNITY_CERTIFICATE": ("community certificate", "caste certificate", "comm cert"),
    "CASTE_CERTIFICATE": (
        "caste certificate",
        "obc",
        "sc",
        "st",
        "tribe certificate",
        "cast",
    ),
    "RESIDENCE_CERTIFICATE": ("residence certificate", "domicile certificate", "resident of"),
    "DISABILITY_CERTIFICATE": (
        "disability certificate",
        "differently abled",
        "disability",
        "divyang",
    ),
    "BIRTH_CERTIFICATE": ("birth certificate", "date of birth", "born", "birth place"),
    "MARK_SHEET": ("marksheet", "mark sheet", "grade card", "result", "cgpa", "semester"),
    "VOTER_ID": ("voter id", "epic", "electoral", "voter", "vote card"),
    "PASSPORT": ("passport", "passport no", "ministry of external affairs", "p address"),
    "LAND_RECORD": ("land record", "patta", "record of rights", "mutation", "land rpr"),
    "PHOTOGRAPH": ("photograph", "photo"),
    "MARRIAGE_CERTIFICATE": ("marriage certificate", "married", "mukhyalaya"),
    "APPLICATION_FORM": ("application form", "आवेदन", "registration form", "form no"),
    "OTHER": (),
}

# A few recognised value extracts. Each returns raw + masked; masking keeps only
# the tail characters so the citizen can verify the contents.
_PATTERNS: dict[str, re.Pattern[str]] = {
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "voter": re.compile(r"\b[A-Z]{3}\d{7}\b"),
    "passport": re.compile(r"\b[AB]\d{7}\b"),
    "dob": re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"),
    "gender": re.compile(r"\b(Male|Female|M|F)\b", re.IGNORECASE),
}


def _mask(value: str | None, *, keep_tail: int = 4) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if not digits:
        return None
    tail = digits[-keep_tail:]
    if len(digits) > keep_tail:
        return f"{'X' * (len(digits) - keep_tail)}{tail}"
    return "X" * len(digits)


def _normalise(text: str) -> str:
    """Lower + strip spaces for blame-free matching."""
    return re.sub(r"\s+", " ", text or "").strip().lower()


@dataclass
class DetectedDocument:
    """Result of running the detector over OCR text."""

    code: str
    confidence: float = 0.0
    extracted: list[dict] = field(default_factory=list)
    verdict: DetectionCode = "unrecognised"
    ocr_confidence: OcrConfidenceT = "needs_review"


def detect_document(ocr_text: str, *, expected: str | None = None) -> DetectedDocument:
    """Classify OCR text into a canonical document code.

    - Scores each keyword hit; the best match short-circuits when confident.
    - ``expected`` lets the router check the detected type against the scheme's
      required document (for typeMatches) and pick a partial verdict otherwise.
    """
    if not ocr_text or not ocr_text.strip():
        return DetectedDocument(code="OTHER", verdict="unrecognised", ocr_confidence="low")
    text = _normalise(ocr_text)

    best_code: str | None = None
    best_hits = 0
    for code, keywords in _KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits and (best_code is None or hits > best_hits):
            best_code, best_hits = code, hits
            # One strong keyword match (or Aadhaar numeric) is decisive.
            if hits >= 2 or (code == "AADHAAR" and _PATTERNS["aadhaar"].search(ocr_text)):
                break

    if best_code is None:
        # Fallback: a clean 12-digit number alone usually is an Aadhaar.
        if _PATTERNS["aadhaar"].search(ocr_text):
            best_code, best_hits = "AADHAAR", 1
        else:
            return DetectedDocument(code="OTHER", verdict="unrecognised", ocr_confidence="low")

    code = best_code
    extracted: list[dict] = []
    aadhaar = dob = pan = voter = passport = gender = None
    if m := _PATTERNS["aadhaar"].search(ocr_text):
        aadhaar = m.group(0).replace(" ", "")
    if m := _PATTERNS["pan"].search(ocr_text):
        pan = m.group(0)
    if m := _PATTERNS["voter"].search(ocr_text):
        voter = m.group(0)
    if m := _PATTERNS["passport"].search(ocr_text):
        passport = m.group(0)
    if m := _PATTERNS["dob"].search(ocr_text):
        dob = m.group(1)
    g = _PATTERNS["gender"].search(text)
    if g:
        gender = g.group(1).title()

    def field(key: str, label: str, value: str | None) -> dict | None:
        if not value:
            return None
        return {"key": key, "label": label, "value": value, "masked": _mask(value)}

    candidates = [
        field("aadhaar_no", "Aadhaar Number", aadhaar),
        field("pan_no", "PAN Number", pan),
        field("voter_id", "Voter ID / EPIC", voter),
        field("passport_no", "Passport Number", passport),
        field("date_of_birth", "Date of Birth", dob),
        field("gender", "Gender", gender),
    ]
    extracted = [c for c in candidates if c is not None]

    # Confidence: matched document with a recognised value > bare keyword.
    has_value = bool(extracted)
    confidence = 0.9 if has_value else 0.6
    ocr_confidence: OcrConfidenceT = "high" if has_value else "needs_review"
    verdict: DetectionCode = "matched" if has_value else "partial"

    if expected:
        expected_code = expected.upper()
        if expected_code in _KEYWORDS and any(kw in text for kw in _KEYWORDS[expected_code]):
            # User told us which doc this should be, and the text corroborates.
            code = expected_code
            verdict = "matched"
            confidence = max(confidence, 0.8)
        elif code != expected_code:
            verdict = "mismatch"
            code = expected_code
            confidence = 0.3

    return DetectedDocument(
        code=code,
        confidence=confidence,
        extracted=extracted,
        verdict=verdict,
        ocr_confidence=ocr_confidence,
    )
