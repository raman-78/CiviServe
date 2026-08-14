# 02 — Relationships & Normalization

## Relationship graph (by aggregate)

```
CITIZEN STACK
  users 1──0..1 user_profiles
  users 1──0..1 admin_users
  users 1──0..* chat_sessions 1──0..* chat_messages
  users 1──0..* user_saved_schemes 0..*──1 schemes
  users 1──0..* user_eligibility_results 0..*──1 schemes
  users 1──0..* notifications 0..*──1 schemes
  users 1──0..* feedback 0..1──1 chat_messages
  users 1──0..* user_documents 0..1──1 document_types

SCHEME KNOWLEDGE STACK
  schemes 1──0..* scheme_category_links 0..*──1 scheme_categories
  schemes 1──0..* scheme_states 0..*──1 states
  schemes 1──0..* scheme_tags
  schemes 1──0..* scheme_regional_languages 0..*──1 languages
  schemes 1──0..* scheme_benefits
  schemes 1──0..* scheme_application_steps
  schemes 1──0..* scheme_faqs
  schemes 1──0..* scheme_official_links
  schemes 1──0..* scheme_documents 0..1──1 document_types
  schemes 1──0..* eligibility_rules 0..1──1 eligibility_filter_defs

SERVICE-CENTRE STACK
  states 1──0..* service_centres 1──0..* service_centre_services

RAG STACK
  knowledge_sources 1──0..* knowledge_chunks 1──0..* embeddings 0..1──1 embedding_models
  knowledge_chunks 0..*──1 schemes
  chat_messages 1──0..* citations 0..*──1 knowledge_chunks
```

## Cardinality cheat-sheet

| From | To | Multiplicity | Notes |
| ---- | -- | ------------ | ----- |
| users | user_profiles | 1 : 0..1 | lazy profile; created on first consent |
| users | admin_users | 1 : 0..1 | staff are users + a staff row |
| chat_sessions | chat_messages | 1 : 0..N | ordered by `created_at` |
| schemes | eligibility_rules | 1 : 0..N | incl. hard + soft rules |
| schemes | scheme_category_links | 1 : 0..N | a scheme can be many categories |
| schemes | scheme_states | 1 : 0..N | central = implicit all states |
| schemes | scheme_regional_languages | 1 : 0..N | languages shipped for the scheme |
| schemes | scheme_faqs | 1 : 0..N | each FAQ = one RAG chunk |
| service_centres | service_centre_services | 1 : 0..N | services offered |
| knowledge_sources | knowledge_chunks | 1 : 0..N | chunking produces many |
| knowledge_chunks | embeddings | 1 : 0..N | one per model version |
| chat_messages | citations | 1 : 0..N | grounded answer → chunks |
| users | notifications | 1 : 0..N | push/email/in-app |
| users | user_eligibility_results | 1 : 0..N | history of checks |
| users | audit_logs | 0..1 : 0..N | actor may be system |

## Normalization: forms targeted

- **1NF**: atomic columns; arrays only for genuinely-set-valued attributes
  (`languages[]`, `accepted_file_formats[]`, `permissions[]`); child entities
  (benefits, steps, FAQs, links, documents) are separate tables.
- **2NF / 3NF**: no partial or transitive key dependencies. Examples:
  - Ministry/state/category are reference or FK columns, not repeated text.
  - `scheme_application_steps` uses a surrogate PK; `(scheme_id, step_type,
    step_no)` is UNIQUE (domain key) — a scheme's step list is keyed by the
    domain constraint.
  - Document requirements point at a `document_types` master row; name/format
    facts live once.
- **4NF (M2M)**: multi-valued dependencies are split via pure junction tables:
  `scheme_category_links`, `scheme_states`, `scheme_tags`,
  `scheme_regional_languages`, `service_centre_services`, `user_saved_schemes`.

## Intentional denormalization (documented trade-offs)

| Denormalization | Why | Guardrail |
| --------------- | --- | --------- |
| `schemes.name_en/description_en` + full `localized_texts` | fast en search/scoring; English is the RAG canonical | en is written once (canonical); localized_texts has `translation_status` |
| `schemes.primary_category_id` | cheap category filter without a join | real list lives in `scheme_category_links`; triggers keep it in sync |
| `schemes.age_min/age_max/gender_allowed/annual_income_limit_inr` | eligibility fast-path for simple schemes | authoritative rules remain in `eligibility_rules`; these are mirrors |
| `chat_sessions.message_count` | list UI without COUNT() | trigger-maintained |
| `user_profiles` flattened flags | the eligibility engine reads a flat row | flags map 1:1 to `eligibility_filter_defs` keys |
| `schemes.content_hash` | change detection for data refresh | recomputed on each publish |

## Key strategy

- **UUID PKs** (`users`, `chat_sessions`, `schemes`, `service_centres`,
  `knowledge_*`, reference catalogs): globally unique, safe to expose to
  clients/mobile/app, avoidable collisions in bulk import, uniform across
  entities. Chat message `id` is `BIGINT IDENTITY` (never referenced by
  external clients at scale, saves index bytes on the hottest table).
- **Natural PKs** where stable and short: `languages.code`, `states.code`,
  `eligibility_filter_defs.key`, composite junction PKs.
- Junction PKs are composite (`(scheme_id, category_id)`), no surrogate needed.

## FK & referential action policy

| Policy | Applied to | Rationale |
| ------ | ---------- | --------- |
| `ON DELETE CASCADE` | user-owned and scheme-owned children | deleting a user/scheme removes its dependent rows; audit keeps history |
| `ON DELETE SET NULL` | nullable contextual refs (`feedback.chat_message_id`, `user_eligibility_results.scheme_id`, `user_documents.document_type_id`) | history survives parent removal |
| `RESTRICT` (default) | reference catalogs referenced by live rows (`languages`, `states`, `document_types`, `eligibility_filter_defs`) | prevent breaking integrity; deactivate instead of delete |
| Soft delete | `users.status`, `schemes.status`, content `status`/`active` | audit + undo-ability; never `DELETE` content rows in practice |

## Integrity guards

- **Check constraints** on all enums and numeric ranges (`age 0..130`, `rating
  1..5`, `lat/lng` bounds).
- **Partial unique indexes** for business rules: one active `client_request_id`
  per send; one primary `scheme_official_links.url` per active link; one active
  primary state per scheme (enforced in app when `scope=state`).
- **citext** for case-insensitive identity columns (`email`, `code`, `tag`).
- **Triggers** maintain `search_document_en`, `geom`, `message_count`,
  `content_hash`, and mirror columns; all triggers are **idempotent** and defined
  inside migrations (no app-side drift).
