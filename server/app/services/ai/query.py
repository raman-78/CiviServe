"""Natural-language analysis of a single user turn.

- intent detection (keyword-based; the LLM re-validates the final label)
- structured fact extraction (age / income / state / demographic flags)
- follow-up detection (short turns referencing the previous exchange)
- missing-info derivation: which eligibility fields the *retrieved* schemes
  constrain but the known profile / turn doesn't cover yet.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.ai.providers import SchemeRef

_INTENTS: list[tuple[str, tuple[str, ...]]] = [
    ("greeting", ("hello", "hi ", "hii", "hey", "namaste", "good morning", "good evening")),
    ("feedback", ("feedback", "complaint", "suggestion", "improve", "rating")),
    ("center_locator", ("center", "locate", "near me", "office", "csc ", "kiosk", "where can i")),
    ("document_guidance", ("document", "paper", "proof", "aadhaar", "ration card", "certificate")),
    ("application_help", ("apply", "application", "how to apply", "form", "process", "steps")),
    ("eligibility_check", ("eligible", "eligibility", "can i get", "am i", "suit", "fit")),
    ("scheme_discovery", ("scheme", "yojana", "benefit", "support", "assistance", "help")),
]

_FLAG_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("is_farmer", ("farmer", "kisan", "farming", "cultivat")),
    ("is_student", ("student", "school", "college", "education")),
    ("is_disabled", ("disabled", "disability", "divyang")),
    ("is_minority", ("minority", "muslim", "christian", "sikh", "jain", "parsi")),
    ("is_senior_citizen", ("senior citizen", "senior", "elderly", "old age")),
    ("is_widow", ("widow", "widowed", "vidhva")),
    ("is_self_employed", ("self-employed", "self employed", "business", "shop owner")),
]

_AGE_RE = re.compile(r"(\d{1,3})\s*(?:years|yrs|year|yo|saal)?\s*(?:old)?", re.IGNORECASE)
_INCOME_RE = re.compile(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*(?:lakh|lac|lakhs|lakhs?)\b", re.IGNORECASE)

#: rule ``field`` → profile attribute whose absence makes it a gap.
_RULE_TO_PROFILE: dict[str, str] = {
    "age": "age",
    "income_band": "income_band",
    "annual_income": "annual_income_inr",
    "gender": "gender",
    "occupation": "occupation",
    "education": "education_level",
    "state": "state_code",
    "is_farmer": "is_farmer",
    "is_student": "is_student",
    "is_disabled": "is_disabled",
    "is_minority": "is_minority",
    "is_widow": "is_widow",
    "is_self_employed": "is_self_employed",
    "community": "community",
}

_STATES: dict[str, str] = {
    "andhra pradesh": "AP",
    "bihar": "BR",
    "chhattisgarh": "CG",
    "delhi": "DL",
    "goa": "GA",
    "gujarat": "GJ",
    "haryana": "HR",
    "himachal pradesh": "HP",
    "jharkhand": "JH",
    "karnataka": "KA",
    "kerala": "KL",
    "madhya pradesh": "MP",
    "maharashtra": "MH",
    "odisha": "OD",
    "punjab": "PB",
    "rajasthan": "RJ",
    "tamil nadu": "TN",
    "telangana": "TS",
    "uttar pradesh": "UP",
    "uttarakhand": "UK",
    "west bengal": "WB",
}

_ANAPHORA = (
    "what about",
    "and this",
    "and that",
    "that one",
    "this one",
    "that scheme",
    "any other",
    "also",
    "what else",
    "more like",
)


class QueryAnalysis:
    """Result of analysing one turn (immutable-by-convention plain object)."""

    def __init__(
        self,
        *,
        intent: str,
        query: str,
        extracted_facts: dict[str, Any],
        missing_fields: list[str],
        is_follow_up: bool,
    ) -> None:
        self.intent = intent
        self.query = query
        self.extracted_facts = extracted_facts
        self.missing_fields = missing_fields
        self.is_follow_up = is_follow_up


class QueryProcessor:
    """Heuristic pre-analysis; cheap enough to run before every LLM call."""

    def detect_intent(self, text: str) -> str:
        lowered = " " + text.lower().strip() + " "
        for intent, keywords in _INTENTS:
            if any(keyword in lowered for keyword in keywords):
                return intent
        return "scheme_discovery"

    def extract_facts(self, text: str) -> dict[str, Any]:
        facts: dict[str, Any] = {}
        lowered = text.lower()

        age_match = re.search(r"(\d{1,3})\s*(?:years|yrs|year|yo)", lowered)
        if age_match:
            age = int(age_match.group(1))
            facts["age"] = age
            facts["is_senior_citizen"] = age >= 60

        income_match = _INCOME_RE.search(lowered)
        if income_match:
            lakhs = float(income_match.group(1).replace(",", ""))
            facts["annual_income_inr"] = int(lakhs * 100000)
            if lakhs <= 2:
                facts["income_band"] = "below-poverty"
            elif lakhs <= 5:
                facts["income_band"] = "low"
            elif lakhs <= 12:
                facts["income_band"] = "middle"
            else:
                facts["income_band"] = "upper"

        for state_name, code in _STATES.items():
            if state_name in lowered:
                facts["state_code"] = code
                break

        if "woman" in lowered or "women" in lowered or "mahila" in lowered:
            facts["gender"] = "female"
        elif "man" in lowered:
            facts["gender"] = "male"

        for flag, keywords in _FLAG_KEYWORDS:
            if any(keyword in lowered for keyword in keywords):
                facts[flag] = True
        return facts

    def is_follow_up(self, text: str) -> bool:
        lowered = text.lower().strip()
        if len(lowered) > 90:
            return False
        return any(phrase in lowered for phrase in _ANAPHORA)

    def missing_fields(self, schemes: list[SchemeRef], profile: dict[str, Any]) -> list[str]:
        """Fields the retrieved schemes constrain but we still don't know."""
        needed: list[str] = []
        for scheme in schemes:
            for rule in scheme.eligibility_rules:
                field = rule.get("field")
                if field not in _RULE_TO_PROFILE:
                    continue
                profile_attr = _RULE_TO_PROFILE[field]
                known = profile.get(profile_attr) or profile.get(field)
                if known is None and field not in needed:
                    needed.append(field)
        return needed

    def analyse(
        self,
        query: str,
        *,
        profile: dict[str, Any],
        retrieved: list[SchemeRef],
    ) -> QueryAnalysis:
        facts = self.extract_facts(query)
        merged = dict(profile)
        merged.update(facts)
        missing = self.missing_fields(retrieved, merged)
        return QueryAnalysis(
            intent=self.detect_intent(query),
            query=query,
            extracted_facts=facts,
            missing_fields=missing,
            is_follow_up=self.is_follow_up(query),
        )
