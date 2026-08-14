# @civiserve/shared

Canonical domain models shared across the monorepo.

## What lives here

- `src/domain/` — TypeScript contracts for **UserProfile, ChatSession, ChatMessage,
  Scheme, EligibilityRule, RequiredDocument, ServiceCenter, Recommendation, LanguageInfo**.
- `schemas/*.schema.json` — language-neutral JSON Schema mirroring the TS contracts
  (future: generate Pydantic models from these, or validate against them).
- These types are the **single source of truth** for the API surface. The FastAPI
  schemas and the SQLAlchemy models must serialize to the exact field names here.

## Why not duplicate types?

1. **One contract** — the client (`@civiserve/client`) imports from this package
   via the Vite/TS path alias; the server declares its Pydantic models against the
   same names (checked by integration tests in a later prompt).
2. **No drift** — a rename here fails `typecheck` in the client immediately.
3. **Machine-checkable** — the JSON Schema files can later drive codegen for both
   TypeScript (zod schemas) and Python (pydantic models).

## Domain model map (→ future DB tables / Pydantic)

| TS type             | Future server Pydantic schema | Future DB table      |
| ------------------- | ----------------------------- | -------------------- |
| UserProfile         | `ProfileIn/Out`               | `user_profiles`      |
| ChatSession         | `SessionIn/Out`               | `chat_sessions`      |
| ChatMessage         | `MessageIn/Out`               | `chat_messages`      |
| Scheme / SchemeSummary | `SchemeOut`                | `schemes`            |
| EligibilityRule     | `EligibilityRule`             | `scheme_eligibility_rules` |
| RequiredDocument    | `DocumentOut`                 | `scheme_documents`   |
| ServiceCenter       | `CenterOut`                   | `service_centers`    |
| Recommendation      | `RecommendationOut`           | (computed, not stored) |
| LanguageInfo        | `LanguageOut`                 | `languages` (static) |

## Notes

- Rich scheme text is **bilingual (en + native) at rest**; additional languages are
  produced on demand by the translation service and cached.
- Geographic types use WGS84 `lat/lng`; the DB layer stores them as `geometry(Point,
  4326)` via PostGIS.
- Message payloads are JSONB on the server; `JsonObject` keeps them typed here.
