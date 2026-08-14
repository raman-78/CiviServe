# 03 — Eligibility Engine (database design)

## Goal

The AI must answer *"am I eligible?"* for any scheme across every Indian state,
using filters that grow over time **without code changes**. That means
eligibility is **declarative data**, evaluated by a generic engine, not a
per-scheme function.

## Two tables do the work

### `eligibility_filter_defs` — the catalog of supported filters

One row per filter the engine understands. The set is data-driven, so new
filters (per the requirement: senior citizen, widow, self-employed, …) are
**rows, not code**.

```
age            (number, years)
gender         (enum: male | female | transgender | prefer-not-to-say)
occupation     (enum/set)
income         (number, INR)          ← annual income
education      (enum: below-primary | primary | secondary | higher-secondary |
                           graduate | post-graduate | none)
state          (enum: states.code)
district       (string)
disability     (bool / enum by type)
is_farmer      (bool)
is_student     (bool)
community      (enum: general | sc | st | obc | ews)
is_minority    (bool)
is_senior_citizen (bool)
is_widow       (bool)
is_self_employed (bool)
… future       (value_type: number | string | boolean | enum | range | set)
```

Each def declares `value_type`, optional `allowed_values` (for enums/sets), and
`unit`. The evaluator uses this metadata to validate and coerce values. Adding a
filter later = insert `filter_defs` row (+ optionally a `user_profiles` column
in the same migration if a new profile attribute is needed).

### `eligibility_rules` — one scheme's constraints

| Column | Meaning |
| ------ | ------- |
| scheme_id | scheme this rule belongs to |
| filter_key | which filter (FK → defs.key) |
| operator | `eq \| neq \| gte \| lte \| in \| between \| exists \| contains` |
| value_js | value: scalar, `{min,max}` or array (JSONB, validated against value_type) |
| value_min / value_max | **materialized** numeric bounds for indexed range prefiltering |
| is_required | **hard** rule (must hold) vs **soft** signal (boosts match) |
| rule_group | group label; **rules in the same group are OR-ed**, groups are AND-ed |
| description_en | human-readable explanation (also used by the LLM to explain) |
| active | enable/disable without delete |

### Example rules (PM-KISAN, illustrative)

| filter_key | operator | value_js | is_required | rule_group |
| ---------- | -------- | -------- | ----------- | ---------- |
| state | in | `["*"]` or omitted | true | main |
| is_farmer | eq | `true` | true | main |
| age | gte | `18` | false | main |
| income | lte | `200000` | false | alternative_a |
| community | in | `["obc","sc","st"]` | false | alternative_a |
| occupation | in | `["farmer","cultivator"]` | false | alternative_b |

### How a new filter is added (no code)

1. Insert into `eligibility_filter_defs` (e.g. `is_widow`, `value_type=boolean`,
   `source_field=user_profiles.is_widow`).
2. If the profile lacks the attribute, a later migration adds the column
   `user_profiles.is_widow BOOLEAN` (nullable — no backfill needed).
3. Scheme editors attach rules using the new key.

The eligibility service (future prompt) renders this generically: read defs →
build evaluator for the user's profile row → evaluate rules → produce
`Recommendation{ status, matchScore, matchedRules, brokenRules, reasons }`
(matches `shared/src/domain/recommendation.ts` incl. the
`eligible | likely | needs_more_info | not_eligible` ladder).

## Evaluation model

```
profile snapshot (user_profiles + consent) 
   │
   ▼
prefilter   (Postgres): WHERE scheme active & scope/state match &
             value_min/value_max indexed range check per filter_key
   │
   ▼
evaluate    (application): read eligibility_rules for candidate schemes,
             group by rule_group → OR within group, AND across groups,
             hard rules decisive, soft rules add score
   │
   ▼
status ladder: eligible | likely | needs_more_info | not_eligible
   │              (missing fields from profile → needs_more_info → chat follow-ups)
   ▼
persist user_eligibility_results (profile_snapshot + matched/broken rules)
```

### `needs_more_info` is first-class

When a hard rule references a filter whose profile value is `NULL`, the engine
returns `needs_more_info` and lists the missing `filter_keys`. The chat layer
uses exactly that list to ask the next question — which is why
`user_eligibility_results.profile_snapshot` is stored: the follow-up turn knows
what was already asked.

## Indexed fast path

- **Range prefilter**: partial index per required `filter_key` on
  `(filter_key, operator)` with `value_min/value_max` enables a coarse
  candidate filter in SQL before the app-level evaluator runs — keeps the
  "thousands of schemes" scale.
- **Scope/state filter**: `schemes(scope, primary_category_id)` +
  `scheme_states(scheme_id, state_code)` quickly restrict to a user's state.
- Results cached in `ai_responses_cache` keyed by
  `(profile_hash, state, query_hash)` — identical checks never re-run the engine.

## Extensibility contract

- Engine version is stamped on every `user_eligibility_results` row
  (`engine_version`) so rule-semantics changes don't corrupt history.
- Rules carry `description_en` → the LLM explains *why* in the user's language
  without re-deriving eligibility logic.
- Doc-based filters (e.g. *"needs a disability certificate"*) are modeled the
  same way with `source_field = document_types.code` and are evaluated against
  `user_documents.verification_status`.
