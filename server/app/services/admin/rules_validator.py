"""Eligibility-rule validation used by the admin dashboard (Prompt 15).

The public engine (:mod:`app.services.recommendation.engine`) is *lenient* —
unknown fields/operators degrade to "more info needed" so bad seed data never
crashes a recommendation. The admin rule editor is the opposite: it must reject
rules the engine cannot honour. This module validates each rule dict against the
same canonical data the engine consumes
(:mod:`app.services.recommendation.filters`), so a rule that passes here is
guaranteed to be evaluable.

Admin write paths (create/update/publish) run these checks, so broken
eligibility rules can never reach production (Prompt 15 security gate).
"""

from __future__ import annotations

from typing import Any

from app.core.errors import ValidationError_
from app.services.recommendation.engine import _SUPPORTED_OPERATORS
from app.services.recommendation.filters import filter_def

#: Operators that expect a list value (the engine compares against each item).
_LIST_OPERATORS = frozenset({"in", "between"})

#: Operator asserted without a meaningful literal value.
_VALUE_FREE_OPERATORS = frozenset({"exists"})


class EligibilityRuleError(ValidationError_):
    """Raised when an eligibility rule is malformed or unsupported."""


def _field_keys() -> list[str]:
    from app.services.recommendation.filters import filter_defs

    return [def_.key for def_ in filter_defs()]


def validate_rule(rule: dict[str, Any], *, allow_unknown_field: bool = False) -> None:
    """Validate a single rule dict; raises :class:`EligibilityRuleError` on failure.

    ``allow_unknown_field`` supports archival/legacy flows that want to keep
    old-but-inert rules (they still get rejected on publish).
    """
    if not isinstance(rule, dict):
        raise EligibilityRuleError("Each eligibility rule must be an object.")

    field = str(rule.get("field") or "").strip().lower()
    if not field:
        raise EligibilityRuleError("Rule is missing 'field'.")
    defn = filter_def(field)
    if defn is None and not allow_unknown_field:
        known = ", ".join(sorted(_field_keys()))
        raise EligibilityRuleError(f"Unknown rule field '{field}'. Supported: {known}")

    operator = str(rule.get("operator") or "eq").strip().lower()
    if operator not in _SUPPORTED_OPERATORS:
        supported = ", ".join(sorted(_SUPPORTED_OPERATORS))
        raise EligibilityRuleError(
            f"Unsupported operator '{operator}' for field '{field}'. Supported: {supported}"
        )

    description = str(rule.get("description") or "")
    if len(description) > 500:
        raise EligibilityRuleError("Rule description must be 500 characters or fewer.")

    if rule.get("is_required") not in (None, True, False):
        raise EligibilityRuleError("Rule 'is_required' must be a boolean.")
    if rule.get("rule_group") is not None and not isinstance(rule.get("rule_group"), (str, int)):
        raise EligibilityRuleError("Rule 'rule_group' must be a string or number.")

    if operator in _VALUE_FREE_OPERATORS:
        return
    _validate_value(field, defn, operator, rule.get("value"))


def _validate_value(field: str, defn: Any, operator: str, value: Any) -> None:
    if value is None:
        if operator in _LIST_OPERATORS:
            raise EligibilityRuleError(f"Operator '{operator}' requires a value.")
        return  # eq against a null value is legal ("no income declared yet")

    if operator in _LIST_OPERATORS:
        if not isinstance(value, list) or not value:
            raise EligibilityRuleError(f"Operator '{operator}' requires a non-empty list.")
        if operator == "between" and len(value) != 2:
            raise EligibilityRuleError("Operator 'between' requires exactly two values.")
        for item in value:
            _check_single(field, defn, item)
        return

    _check_single(field, defn, value)


def _check_single(field: str, defn: Any, value: Any) -> None:
    if defn is None:
        return
    if defn.value_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EligibilityRuleError(f"Rule field '{field}' expects a number.")
    elif defn.value_type == "boolean":
        if not isinstance(value, bool):
            raise EligibilityRuleError(f"Rule field '{field}' expects a boolean.")
    elif defn.value_type in ("string", "enum"):
        if not isinstance(value, str) or not value.strip():
            raise EligibilityRuleError(f"Rule field '{field}' expects a non-empty string.")
        if defn.value_type == "enum" and defn.allowed_values and value not in defn.allowed_values:
            allowed = ", ".join(sorted(defn.allowed_values))
            raise EligibilityRuleError(f"Rule field '{field}' must be one of: {allowed}.")


def validate_rules(rules: list[dict[str, Any]], *, allow_unknown_field: bool = False) -> None:
    """Validate a scheme's whole ``eligibility_rules`` (all-or-nothing)."""
    if not isinstance(rules, list):
        raise EligibilityRuleError("eligibility_rules must be a list.")
    for rule in rules:
        validate_rule(rule, allow_unknown_field=allow_unknown_field)


def validate_rules_for_publish(rules: list[dict[str, Any]]) -> None:
    """Strict gate before publication: unknown fields/operators are hard errors."""
    validate_rules(rules, allow_unknown_field=False)
