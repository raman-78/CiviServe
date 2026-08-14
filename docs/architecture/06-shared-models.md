# 06 — Shared Models

## Purpose

`shared/` is the **single source of truth for the API surface**. The client
consumes the TypeScript types directly; the server's Pydantic schemas and DB
tables must serialize to the exact same field names; JSON Schema mirrors allow
machine-checking the contract.

```
shared/
├── package.json            # @schemesathi/shared (workspace:*) — consumed by client
├── src/
│   ├── index.ts
│   └── domain/
│       ├── common.ts          # LanguageCode, StateCode, UUID, ISODateString, ...
│       ├── user.ts            # UserProfile, ConsentFlags, AccessibilityPreferences
│       ├── chat.ts            # ChatSession, ChatMessage, ChatRequest, Intents
│       ├── scheme.ts          # Scheme, EligibilityRule, RequiredDocument, SchemeSummary
│       ├── centers.ts         # ServiceCenter, NearbyCentersRequest, GeoPoint
│       ├── recommendation.ts  # Recommendation, EligibilityStatus, Requests
│       └── language.ts        # SUPPORTED_LANGUAGES catalog + LanguageInfo
└── schemas/
    └── scheme.schema.json     # language-neutral JSON Schema mirror
```

## Why this model works

1. **No drift by construction.** Renaming a field in `shared` fails `typecheck`
   in the client immediately; a contract test (later prompt) compares the server's
   OpenAPI schema against the JSON Schema.
2. **Language-neutral JSON Schema** is the formal contract; TS types and future
   generated Pydantic models both derive from it.
3. **Multilingual-ready.** Rich scheme text is bilingual (`en` + `native`) at rest;
   `ChatMessage` keeps the canonical language and `renderedText` separately so the
   UI can switch languages without re-calling the backend.

## Core entities (fields that define the product)

| Entity | Critical fields |
| ------ | --------------- |
| `UserProfile` | `firebaseUid`, `stateCode`, `age`, `incomeBand`, `casteCategory`, `occupation`, `consent` |
| `ChatSession` | `userId`, `language`, `status` |
| `ChatMessage` | `role`, `contentType`, `content` (canonical), `language`, `renderedText`, `payload` (JSONB) |
| `Scheme` | `code`, `stateCode` (or `central`), `category`, `name/summary` (en+native), `eligibilityRules[]`, `requiredDocuments[]`, `applicationLinks` |
| `EligibilityRule` | `field` + `operator` + `value` (declarative, evaluable against profile) |
| `Recommendation` | `status` (eligible/likely/needs_more_info/not_eligible), `matchScore`, `matchedRules`, `brokenRules[]`, `fullyEligible` |
| `RequiredDocument` | `kind` (OCR/categorization), `name`, `optional`, `ocrSupported` |
| `ServiceCenter` | `type` (csc/esevai/tehsil/post_office/bank), `lat/lng`, `services[]`, `languages[]`, `verified` |
| `LanguageInfo` | `stt`, `tts`, `indicTrans` capability flags per language |

The **eligibility status ladder** (`eligible → likely → needs_more_info →
not_eligible`) is central to the chat: `needs_more_info` surfaces which profile
fields are missing so the assistant asks the right follow-up questions instead of
giving a false yes/no.

## Contract rules

- Field names: `camelCase` everywhere (JSON + TS + Pydantic `alias_generator`).
- Timestamps: ISO-8601 UTC strings.
- Enums are string unions in TS; string-backed Python `enum.StrEnum` server-side;
  `enum` arrays in JSON Schema.
- Unknown/extra fields: `additionalProperties: true` for forward-compat, but
  **required** fields are enforced — a breaking addition to a required field is a
  major contract change (v2).
- Geography: always `lat`/`lng` (WGS84) in API payloads; `geometry(Point,4326)`
  only inside the DB.

## Change process

1. Edit `shared/src/domain/*.ts` (+ JSON Schema mirror if structure changes).
2. Update the future Pydantic schema + Alembic migration in the same PR.
3. Add an ADR for anything that alters a required field or the entity graph.

## Optional codegen path (adopted later)

The hand-maintained TS types are authoritative now, but the repo is ready for a
**backend-owned codegen pipeline** to be switched on in a later prompt:
`openapi-typescript` reads `server`'s `openapi.json` → writes
`shared/contracts/generated/types.ts`, and a CI step fails if the generated output
is stale (`git diff --exit-code`). That flips the direction of truth to the
server's Pydantic models while keeping the JSON Schema as the formal contract. The
two sources are reconciled by a contract test (doc 04).
