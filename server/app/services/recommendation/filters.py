"""Declarative eligibility-filter catalog (docs/database/03 §`eligibility_filter_defs`).

Each supported rule ``field`` maps to a :class:`FilterDef` describing its value
type, allowed values, unit and which profile attribute shadows it. The evaluator
(:mod:`app.services.recommendation.engine`) uses this metadata to read, coerce
and validate profile values. The set is data, not code: adding a new filter is
one row here (later migrated to a ``eligibility_filter_defs`` table for the admin
dashboard without touching the engine).
"""

from __future__ import annotations

from dataclasses import dataclass

#: value_type → coercion strategy used by the evaluator.
number = "number"
string = "string"
boolean = "boolean"
enum = "enum"

GENDERS = frozenset({"male", "female", "transgender", "prefer-not-to-say"})
INCOME_BANDS = frozenset({"below-poverty", "low", "middle", "upper"})
COMMUNITIES = frozenset({"general", "sc", "st", "obc", "ews"})
EDUCATION_LEVELS = frozenset(
    {
        "none",
        "below-primary",
        "primary",
        "secondary",
        "higher-secondary",
        "graduate",
        "post-graduate",
    }
)


@dataclass(frozen=True, slots=True)
class FilterDef:
    """One catalog entry for a supported eligibility filter key."""

    key: str
    value_type: str
    #: profile-dict attribute names (snake + camel aliases) that feed this filter.
    profile_keys: tuple[str, ...]
    allowed_values: frozenset[str] | None = None
    unit: str | None = None
    description: str = ""


def _def(
    key: str,
    value_type: str,
    profile_keys: tuple[str, ...],
    *,
    allowed_values: frozenset[str] | None = None,
    unit: str | None = None,
    description: str = "",
) -> FilterDef:
    return FilterDef(
        key=key,
        value_type=value_type,
        profile_keys=profile_keys,
        allowed_values=allowed_values,
        unit=unit,
        description=description,
    )


FILTER_DEFS: dict[str, FilterDef] = {
    def_.key: def_
    for def_ in (
        _def("age", number, ("age", "age"), unit="years", description="Age in years"),
        _def(
            "annual_income",
            number,
            ("annual_income_inr", "annualIncome", "annual_income"),
            unit="INR",
            description="Annual income in INR",
        ),
        _def(
            "income_band",
            enum,
            ("income_band", "incomeBand"),
            allowed_values=INCOME_BANDS,
            description="Family income bracket",
        ),
        _def(
            "gender",
            enum,
            ("gender", "gender"),
            allowed_values=GENDERS,
            description="Gender",
        ),
        _def("state", string, ("state_code", "stateCode", "state"), description="State code"),
        _def("district", string, ("district",), description="District"),
        _def(
            "occupation",
            string,
            ("occupation",),
            description="Occupation or work profile",
        ),
        _def(
            "education",
            enum,
            ("education_level", "education_level"),
            allowed_values=EDUCATION_LEVELS,
            description="Education level",
        ),
        _def(
            "caste_category",
            enum,
            ("community", "caste_category", "casteCategory"),
            allowed_values=COMMUNITIES,
            description="Caste / community category",
        ),
        _def(
            "community",
            enum,
            ("community", "caste_category", "casteCategory"),
            allowed_values=COMMUNITIES,
            description="Community category",
        ),
        _def("is_farmer", boolean, ("is_farmer", "isFarm", "isFarmer"), description="Farmer"),
        _def("is_student", boolean, ("is_student", "isStudent"), description="Student"),
        _def("is_disabled", boolean, ("is_disabled", "isDisabled"), description="Has a disability"),
        _def(
            "is_minority",
            boolean,
            ("is_minority", "isMinority"),
            description="Minority community member",
        ),
        _def(
            "is_senior_citizen",
            boolean,
            ("is_senior_citizen", "isSeniorCitizen"),
            description="Senior citizen",
        ),
        _def("is_widow", boolean, ("is_widow", "isWidow"), description="Widow / widowed"),
        _def(
            "is_self_employed",
            boolean,
            ("is_self_employed", "isSelfEmployed"),
            description="Self-employed",
        ),
        _def("is_women", boolean, ("is_women", "isWomen"), description="Women-targeted"),
        _def("marital_status", string, ("marital_status",), description="Marital status"),
    )
}


def filter_def(field: str) -> FilterDef | None:
    """Look up a filter by its rule ``field`` key (unknown → None)."""
    return FILTER_DEFS.get(field)


def filter_defs() -> list[FilterDef]:
    """All catalog entries, keyed by their declaration order semantics."""
    return list(FILTER_DEFS.values())
