"""Unit tests for the structured eligibility engine (Prompt 10).

Covers the operator matrix, value coercion, the status ladder, OR-grouping
semantics, soft (is_required=False) signals, scoring and reasons.
"""

from __future__ import annotations

import pytest
from app.services.recommendation.engine import evaluate_rule, evaluate_scheme


def test_eq_number_matches() -> None:
    outcome = evaluate_rule({"field": "age", "operator": "eq", "value": 45}, {"age": 45})
    assert outcome.matched and outcome.present


def test_eq_number_broken() -> None:
    outcome = evaluate_rule({"field": "age", "operator": "eq", "value": 45}, {"age": 30})
    assert not outcome.matched and outcome.present


def test_neq_matches_and_broken() -> None:
    assert evaluate_rule(
        {"field": "gender", "operator": "neq", "value": "female"}, {"gender": "male"}
    ).matched
    assert not evaluate_rule(
        {"field": "gender", "operator": "neq", "value": "female"}, {"gender": "female"}
    ).matched


@pytest.mark.parametrize("value", [60, 61, 120])
def test_gte_boundary(value: int) -> None:
    assert evaluate_rule({"field": "age", "operator": "gte", "value": 60}, {"age": value}).matched


def test_lte_and_broken() -> None:
    assert evaluate_rule({"field": "age", "operator": "lte", "value": 18}, {"age": 17}).matched
    assert not evaluate_rule({"field": "age", "operator": "lte", "value": 18}, {"age": 19}).matched


@pytest.mark.parametrize("value", [18, 40, 60])
def test_between_inclusive(value: int) -> None:
    outcome = evaluate_rule(
        {"field": "age", "operator": "between", "value": [18, 60]}, {"age": value}
    )
    assert outcome.matched


def test_between_out_of_range() -> None:
    assert not evaluate_rule(
        {"field": "age", "operator": "between", "value": [18, 60]}, {"age": 61}
    ).matched


def test_in_case_insensitive() -> None:
    rule = {"field": "income_band", "operator": "in", "value": ["below-poverty", "low"]}
    assert evaluate_rule(rule, {"income_band": "BELOW-POVERTY"}).matched
    assert not evaluate_rule(rule, {"income_band": "upper"}).matched


def test_in_on_occupation_string() -> None:
    rule = {"field": "occupation", "operator": "in", "value": ["farmer", "cultivator"]}
    assert evaluate_rule(rule, {"occupation": "Farmer"}).matched


def test_exists_present() -> None:
    assert evaluate_rule(
        {"field": "district", "operator": "exists"}, {"district": "Chennai"}
    ).matched


def test_exists_missing_broken() -> None:
    outcome = evaluate_rule({"field": "district", "operator": "exists"}, {})
    assert not outcome.matched and outcome.present


def test_boolean_eq_true_and_false() -> None:
    assert evaluate_rule(
        {"field": "is_farmer", "operator": "eq", "value": True}, {"is_farmer": True}
    ).matched
    assert evaluate_rule(
        {"field": "is_farmer", "operator": "eq", "value": False}, {"is_farmer": False}
    ).matched
    assert not evaluate_rule(
        {"field": "is_farmer", "operator": "eq", "value": True}, {"is_farmer": False}
    ).matched


def test_boolean_string_true_coerced() -> None:
    assert evaluate_rule(
        {"field": "is_student", "operator": "eq", "value": True}, {"is_student": "yes"}
    ).matched


def test_missing_field_gives_needs_more_info() -> None:
    ev = evaluate_scheme([{"field": "income_band", "operator": "in", "value": ["low"]}], {})
    assert ev.status == "needs_more_info"
    assert ev.missing_fields == ["income_band"]
    assert ev.broken_rules == []


def test_unknown_field_not_in_catalog() -> None:
    ev = evaluate_scheme([{"field": "land_size_acres", "operator": "gte", "value": 1}], {})
    assert ev.status == "needs_more_info"
    assert not ev.fully_eligible


def test_unknown_operator_graceful() -> None:
    outcome = evaluate_rule({"field": "age", "operator": "regex", "value": "^4"}, {"age": 45})
    assert not outcome.matched and outcome.unknown_operator


def test_ungrouped_rule_its_own_and_group() -> None:
    rules = [
        {"field": "age", "operator": "gte", "value": 60, "description": "Age 60+."},
        {"field": "is_senior_citizen", "operator": "eq", "value": True, "description": "Senior."},
    ]
    # age present but failing ⇒ conclusively broken (not blurred by the unknown senior flag).
    ev = evaluate_scheme(rules, {"age": 45})
    assert ev.status == "not_eligible"
    assert [r["field"] for r in ev.broken_rules] == ["age"]


def test_same_rule_group_is_or() -> None:
    rules = [
        {
            "field": "age",
            "operator": "gte",
            "value": 60,
            "rule_group": "alt",
            "description": "Seniors",
        },
        {
            "field": "is_widow",
            "operator": "eq",
            "value": True,
            "rule_group": "alt",
            "description": "Widows",
        },
    ]
    ev = evaluate_scheme(rules, {"is_widow": True})
    assert ev.status == "eligible"
    assert ev.match_score == 50.0


def test_or_group_all_unknown() -> None:
    rules = [
        {"field": "age", "operator": "gte", "value": 60, "rule_group": "alt"},
        {"field": "is_widow", "operator": "eq", "value": True, "rule_group": "alt"},
    ]
    ev = evaluate_scheme(rules, {})
    assert ev.status == "needs_more_info"


def test_or_group_all_broken_not_eligible() -> None:
    rules = [
        {"field": "age", "operator": "gte", "value": 60, "rule_group": "alt"},
        {"field": "is_widow", "operator": "eq", "value": True, "rule_group": "alt"},
    ]
    ev = evaluate_scheme(rules, {"age": 30, "is_widow": False})
    assert ev.status == "not_eligible"


def test_soft_broken_rule_produces_likely() -> None:
    rules = [
        {
            "field": "is_self_employed",
            "operator": "eq",
            "value": True,
            "description": "Runs a business.",
        },
        {
            "field": "is_women",
            "operator": "eq",
            "value": True,
            "description": "Women encouraged.",
            "is_required": False,
        },
    ]
    ev = evaluate_scheme(rules, {"is_self_employed": True})
    assert ev.status == "likely"
    assert ev.match_score == 50.0


def test_soft_unknown_rule_produces_likely() -> None:
    rules = [
        {"field": "is_self_employed", "operator": "eq", "value": True},
        {"field": "is_women", "operator": "eq", "value": True, "is_required": False},
    ]
    ev = evaluate_scheme(rules, {"is_self_employed": True})
    assert ev.status == "likely"


def test_no_rules_is_eligible() -> None:
    ev = evaluate_scheme([], {})
    assert ev.status == "eligible"
    assert ev.match_score == 0.0
    assert ev.fully_eligible


def test_match_score_percentage() -> None:
    rules: list[dict[str, object]] = [
        {"field": "age", "operator": "gte", "value": 60},
        {"field": "income_band", "operator": "eq", "value": "below-poverty"},
    ]
    ev = evaluate_scheme(rules, {"age": 70, "income_band": "below-poverty"})
    assert ev.status == "eligible"
    assert ev.match_score == 100.0

    half = evaluate_scheme(rules, {"age": 70, "income_band": "middle"})
    assert half.status == "not_eligible"
    assert half.match_score == 50.0


def test_reasons_come_from_rule_descriptions() -> None:
    rules: list[dict[str, object]] = [
        {"field": "age", "operator": "gte", "value": 60, "description": "Age 60 years or above."},
        {
            "field": "income_band",
            "operator": "eq",
            "value": "below-poverty",
            "description": "Below poverty line.",
        },
    ]
    ev = evaluate_scheme(rules, {"age": 65, "income_band": "below-poverty"})
    assert ev.reasons == ["Age 60 years or above.", "Below poverty line."]


def test_annual_income_number_rule() -> None:
    rule = {
        "field": "annual_income",
        "operator": "lte",
        "value": 200000,
        "description": "Income cap.",
    }
    assert evaluate_rule(rule, {"annual_income_inr": 150000}).matched
    assert not evaluate_rule(rule, {"annual_income_inr": 250000}).matched


def test_caste_category_reads_community_profile_attr() -> None:
    rule = {"field": "caste_category", "operator": "in", "value": ["sc", "st", "obc"]}
    assert evaluate_rule(rule, {"community": "obc"}).matched
    assert not evaluate_rule(rule, {"community": "general"}).matched


def test_state_eq_is_case_insensitive() -> None:
    assert evaluate_rule(
        {"field": "state", "operator": "eq", "value": "TN"}, {"state_code": "tn"}
    ).matched
