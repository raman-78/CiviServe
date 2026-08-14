"""Turn the provider's raw output into a validated, client-ready message.

The LLM is asked for JSON (``response_mime_type=application/json`` in Gemini);
we defensively parse it, clamp every referenced scheme `code` to the retrieved
catalog (the client renders cards from these, so hallucinated codes are dropped),
and derive the grounding claim used by the UI ("verified" vs "could not be
verified" plus the official sources it came from).
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger
from app.services.ai.providers import SchemeRef

logger = get_logger(__name__)

_INTENTS = {
    "scheme_discovery",
    "eligibility_check",
    "document_guidance",
    "application_help",
    "center_locator",
    "greeting",
    "feedback",
    "general",
}


class ParsedAnswer:
    """Structured, validated assistant output for one turn."""

    def __init__(self, **kw: Any) -> None:
        self.answer: str = kw["answer"]
        self.intent: str = kw["intent"]
        self.referenced_codes: list[str] = kw["referenced_codes"]
        self.recommendations: list[dict[str, Any]] = kw["recommendations"]
        self.follow_up_questions: list[str] = kw["follow_up_questions"]
        self.needs_more_info: bool = kw["needs_more_info"]
        self.verified: bool = kw["verified"]
        self.note: str = kw["note"]

    def to_payload(
        self,
        *,
        schemes_by_code: dict[str, SchemeRef],
        verified: bool,
        note: str,
        source_codes: list[str],
    ) -> dict[str, Any]:
        referenced = [
            scheme_to_payload(schemes_by_code[code])
            for code in self.referenced_codes
            if code in schemes_by_code
        ]
        recommendations = [
            rec for rec in self.recommendations if rec.get("code") in schemes_by_code
        ]
        return {
            "intent": self.intent,
            "needsMoreInfo": self.needs_more_info,
            "followUpQuestions": self.follow_up_questions,
            "referencedSchemes": referenced,
            "recommendations": recommendations,
            "grounding": {
                "verified": verified,
                "note": note,
                "sources": [{"code": code} for code in source_codes],
            },
        }


def scheme_to_payload(ref: SchemeRef) -> dict[str, Any]:
    return {
        "id": ref.id,
        "code": ref.code,
        "name": ref.name_en,
        "category": ref.category,
        "subCategory": ref.sub_category,
        "summary": ref.summary_en,
        "officialWebsite": ref.official_website,
        "lastVerifiedAt": _iso(ref.last_verified_at),
    }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    serializer = getattr(value, "isoformat", None)
    return serializer() if callable(serializer) else str(value)


class ResponseFormatter:
    """Parse raw LLM text into :class`ParsedAnswer` bound to the catalog."""

    def parse(self, raw: str, retrieved: list[SchemeRef]) -> ParsedAnswer:
        data = self._load_json(raw)
        answer = _clean_str(data.get("answer"))
        if not answer:
            answer = raw.strip()

        intent = _clean_str(data.get("intent")) or "general"
        if intent not in _INTENTS:
            intent = "general"

        needs_more = bool(data.get("needsMoreInfo", False)) or not answer
        follow_ups = _as_list(data.get("followUpQuestions"))
        recommendations = _as_recs(data.get("recommendations"))
        codes = _clamp_codes(_as_list(data.get("referencedSchemes")), retrieved)

        verified = bool(codes) and "could not be verified" not in answer.lower()
        note = (
            f"Verified against {len(codes)} catalog entr{'ies' if len(codes) != 1 else 'y'}."
            if verified
            else "This answer could not be verified from the available catalog; "
            "please confirm on the official portal."
        )
        return ParsedAnswer(
            answer=answer,
            intent=intent,
            referenced_codes=codes,
            recommendations=recommendations,
            follow_up_questions=follow_ups,
            needs_more_info=needs_more,
            verified=verified,
            note=note,
        )

    @staticmethod
    def _load_json(raw: str) -> dict[str, Any]:
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else {}
        except (ValueError, TypeError):
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end > start:
                try:
                    obj = json.loads(raw[start : end + 1])
                    return obj if isinstance(obj, dict) else {}
                except (ValueError, TypeError):
                    pass
            return {}


def _clean_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _as_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _as_recs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict) and item.get("code"):
            out.append(
                {
                    "code": str(item["code"]).strip().upper(),
                    "reason": str(item.get("reason") or "").strip(),
                }
            )
    return out


def _clamp_codes(codes: list[str], retrieved: list[SchemeRef]) -> list[str]:
    known = {ref.code for ref in retrieved}
    seen: set[str] = set()
    clamped: list[str] = []
    for code in codes:
        code = str(code).strip().upper()
        if code and code in known and code not in seen:
            seen.add(code)
            clamped.append(code)
    return clamped
