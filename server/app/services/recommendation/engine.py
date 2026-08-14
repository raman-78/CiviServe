"""Structured eligibility evaluator (docs/database/03 §"evaluation model").

Pure functions: a scheme's ``eligibility_rules`` (JSON rule dicts of shape
``{field, operator, value, description}`` with optional ``is_required`` /
``rule_group``) are evaluated against a flattened profile dict. The ladder is:

- ``not_eligible``     — a required condition group is conclusively violated.
- ``needs_more_info``  — a required condition needs profile data we don't have.
- ``likely``           — required conditions hold; soft signals are uncertain.
- ``eligible``         — every required condition holds and no soft doubts remain.

``matchScore`` is the share of satisfied rules (soft rules weigh down only the
score, never the verdict). ``reasons`` are taken verbatim from the rule
``description`` fields so the client/chat never invents eligibility logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.services.recommendation.filters import FilterDef, filter_def

#: engine_version stamped onto persisted results (docs/database/01 §333).
ENGINE_VERSION = "eligibility-v1"

#: Set of supported rule ``operator`` values (mirrors shared EligibilityOperator).
_SUPPORTED_OPERATORS = frozenset({"eq", "neq", "gte", "lte", "in", "between", "exists"})

EligibilityStatus = Literal["eligible", "likely", "needs_more_info", "not_eligible"]


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"true", "yes", "y", "1", "on"}


def _to_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _norm_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip().lower()


def _profile_value(defn: FilterDef, profile: dict[str, Any]) -> Any:
    """First non-``None`` profile attribute backing this filter (unknown → None)."""
    for key in defn.profile_keys:
        value = profile.get(key)
        if value is not None:
            return value
    return None


def _rule_matches(rule: dict[str, Any], value: Any, defn: FilterDef) -> bool:
    """Evaluate one condition against an already-**present** profile value."""
    operator = str(rule.get("operator", "eq")).lower()
    raw = rule.get("value")

    if operator == "exists":
        return True  # presence of the attribute is asserted; value exists already

    if defn.value_type == "boolean":
        return _to_bool(value) == _to_bool(raw)

    if defn.value_type == "number":
        left = _to_number(value)
        if operator == "eq":
            return (
                left is not None
                and left == _to_number(raw)
                or (left is None and _norm_text(raw) == _norm_text(value))
            )
        if operator == "neq":
            return not (
                left is not None
                and left == _to_number(raw)
                or (left is None and _norm_text(raw) == _norm_text(value))
            )
        if operator == "gte":
            right = _to_number(raw)
            return left is not None and right is not None and left >= right
        if operator == "lte":
            right = _to_number(raw)
            return left is not None and right is not None and left <= right
        if operator in {"in", "between"}:
            haystack = raw if isinstance(raw, (list, tuple)) else [raw]
            if operator == "between":
                if len(haystack) != 2:
                    return False
                low, high = _to_number(haystack[0]), _to_number(haystack[1])
                return (
                    left is not None
                    and low is not None
                    and high is not None
                    and low <= left <= high
                )
            numbers = [_to_number(item) for item in haystack]
            return left is not None and any(n == left for n in numbers if n is not None)
        return False

    text = _norm_text(value)
    raw_text = raw
    if operator == "eq":
        return text == _norm_text(raw_text)
    if operator == "neq":
        return text != _norm_text(raw_text)
    if operator == "gte":
        return text >= _norm_text(raw_text)
    if operator == "lte":
        return text <= _norm_text(raw_text)
    if operator == "in":
        haystack = raw if isinstance(raw, (list, tuple)) else [raw]
        return any(text == _norm_text(item) for item in haystack)
    if operator == "between":
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            return False
        return _norm_text(raw[0]) <= text <= _norm_text(raw[1])
    return False


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    """Result of evaluating a single rule against a profile."""

    rule: dict[str, Any]
    field: str
    matched: bool
    #: False when the profile lacks the attribute the rule needs (unknown).
    present: bool
    #: True when the rule targets a filter the catalog doesn't know yet.
    unsupported: bool = False
    unknown_operator: bool = False

    @property
    def required(self) -> bool:
        # soft signals (is_required=False) score but never decide the verdict.
        return bool(self.rule.get("is_required", True))


@dataclass
class SchemeEvaluation:
    """Deterministic evaluation of a scheme's rules against one profile."""

    status: EligibilityStatus
    match_score: float
    matched_rules: list[dict[str, Any]]
    broken_rules: list[dict[str, Any]]
    missing_fields: list[str]
    reasons: list[str]
    group_outcomes: list[dict[str, Any]] = field(default_factory=list)

    @property
    def fully_eligible(self) -> bool:
        return self.status == "eligible"


def evaluate_rule(rule: dict[str, Any], profile: dict[str, Any]) -> RuleOutcome:
    """Evaluate one rule dict against ``profile`` (never raises for bad data)."""
    normalized: dict[str, Any] = {str(k): v for k, v in rule.items()}
    field = str(normalized.get("field", "")).lower()
    operator = str(normalized.get("operator", "eq")).lower()

    defn = filter_def(field)
    if defn is None:
        # Unsupported filter: we cannot judge, so it stays "unknown" (ask more).
        return RuleOutcome(normalized, field, False, False, unsupported=True)
    if operator not in _SUPPORTED_OPERATORS:
        return RuleOutcome(normalized, field, False, False, unknown_operator=True)

    if operator == "exists":
        # Explicitly asserts the attribute exists in the profile: missing ⇒ broken.
        return RuleOutcome(normalized, field, _profile_value(defn, profile) is not None, True)

    value = _profile_value(defn, profile)
    if value is None:
        return RuleOutcome(normalized, field, False, False)
    matched = _rule_matches(normalized, value, defn)
    return RuleOutcome(normalized, field, matched, True)


def evaluate_scheme(
    rules: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    profile: dict[str, Any],
) -> SchemeEvaluation:
    """Evaluate the rules, group them, and derive the status ladder + score.

    Rule semantics (docs/database/03 §`eligibility_rules`):
    - rules sharing the same non-empty ``rule_group`` are OR-ed (the group passes
      when any rule inside it passes);
    - different groups are AND-ed (every group must pass for a recommendation);
    - a rule with no ``rule_group`` forms its own AND group;
    - ``is_required`` selects hard rules (decisive) vs soft signals (score only);
      absent defaults to True, so existing unannotated seed rules stay hard.
    """
    outcomes = [evaluate_rule(rule, profile) for rule in (rules or [])]

    groups: dict[str, list[RuleOutcome]] = {}
    for index, outcome in enumerate(outcomes):
        declared = outcome.rule.get("rule_group")
        # Only rules that *explicitly* share a rule_group are OR-ed; a rule with
        # no group is its own AND constraint (matches existing seed data).
        group_key = str(declared) if declared else f"__single_{index}"
        groups.setdefault(group_key, []).append(outcome)

    matched_rules: list[dict[str, Any]] = []
    broken_rules: list[dict[str, Any]] = []
    missing: list[str] = []
    group_verdicts: list[dict[str, Any]] = []
    required_broken = False
    required_unknown = False

    for group_key, group in groups.items():
        required = any(o.required for o in group)
        any_matched = any(o.matched for o in group)

        if any_matched:
            verdict = "satisfied"
            matched_rules.extend(o.rule for o in group if o.matched)
        else:
            any_unknown = any(not o.present for o in group)
            verdict = "unknown" if any_unknown else "broken"
            if required and any_unknown:
                required_unknown = True
                for o in group:
                    if not o.present and o.field not in missing:
                        missing.append(o.field)
            if required and not any_unknown:
                required_broken = True
                broken_rules.extend(o.rule for o in group)

        group_verdicts.append({"group": group_key, "required": required, "verdict": verdict})

    total = len(outcomes)
    satisfied = sum(1 for o in outcomes if o.matched)
    score = round(100 * satisfied / total) if total else 0

    status: EligibilityStatus
    if required_broken:
        status = "not_eligible"
    elif required_unknown:
        status = "needs_more_info"
    elif total == 0 or not any(
        not v["required"] and v["verdict"] in {"broken", "unknown"} for v in group_verdicts
    ):
        status = "eligible"
    else:
        status = "likely"

    reasons: list[str] = []
    for rule in matched_rules:
        description = str(rule.get("description") or "").strip()
        reasons.append(description or _rule_reason(rule))

    return SchemeEvaluation(
        status=status,
        match_score=float(score),
        matched_rules=matched_rules,
        broken_rules=broken_rules,
        missing_fields=missing,
        reasons=list(dict.fromkeys(reasons)),
        group_outcomes=group_verdicts,
    )


def _rule_reason(rule: dict[str, Any]) -> str:
    """Fallback human line when a rule carries no description."""
    field = rule.get("field", "profile")
    operator = rule.get("operator", "eq")
    value = rule.get("value")
    return f"{field} {operator} {value}"
