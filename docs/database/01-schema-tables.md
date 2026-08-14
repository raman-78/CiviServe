# 01 — Schema & Table Definitions

All tables for the Government Scheme assistant database. Notation: **PK** =
primary key, **FK** = foreign key, **UQ** = unique, **IX** = index,
**CK** = check constraint, `C` = cascade, `SN` = set null.

---

## 1. `users` — citizens & accounts (Prompt list *1*)

| Column | Type | Constraints | Notes |
| ------ | ---- | ----------- | ----- |
| id | uuid | PK | externally-addressable identity |
| firebase_uid | varchar(128) | UQ, null | auth binding; null for guests |
| auth_method | varchar(20) | NN `'email'\|'phone'\|'google'\|'guest'` CK | |
| phone | varchar(20) | UQ, null | e164-ish |
| email | citext | UQ, null | case-insensitive unique |
| display_name | varchar(120) | | |
| role | varchar(20) | NN def `'citizen'` CK `citizen\|admin\|content_editor` | |
| status | varchar(20) | NN def `'active'` CK `active\|suspended\|deleted` | soft delete |
| preferred_language | varchar(8) | FK `languages.code` def `'en'` | |
| consent_json | jsonb | NN def `'{}'` | `{data_processing, voice_processing, location_access}` |
| is_guest | bool | NN def false | guest token sessions |
| created_at / updated_at / last_login_at | timestamptz | NN | |

**Indexes:** `firebase_uid` UQ · `email` UQ · `phone` UQ · IX `(status)`.

---

## 2. user_profiles — citizen attributes for eligibility (*2*)

| Column | Type | Constraints | Notes |
| ------ | ---- | ----------- | ----- |
| id | uuid | PK** | |
| user_id | uuid | FK unique → `users.id` C | 1:1 |
| state_code | varchar(8) | FK → `states.code`, null | |
| district | varchar(80) | | |
| age | int | CK `0..130`, null | |
| gender | varchar(20) | CK `male\|female\|transgender\|prefer-not-to-say`, null | |
| income_band | varchar(20) | CK `below-poverty\|low\|middle\|upper`, null | derived band |
| annual_income_inr | bigint | null | raw, when disclosed |
| education_level | varchar(30) | null | |
| occupation | varchar(40) | null | |
| community | varchar(20) | CK `general\|sc\|st\|obc\|ews`, null | |
| is_minority | bool | null | |
| is_farmer | bool | null | |
| is_student | bool | null | |
| is_senior_citizen | bool | null | |
| is_widow | bool | null | |
| is_self_employed | bool | null | |
| is_disabled | bool | null | |
| disability_type | varchar(60) | null | |
| languages | varchar(8)[] | NN def `{}` | preferred; FK-per-element not enforced |
| accessibility_json | jsonb | NN def `'{}'` | text-only, high-contrast, slow-speech |
| source | varchar(20) | def `'manual'` CK `manual\|chat\|ocr\|import` | track origin |
| created_at / updated_at | timestamptz | NN | |

**Indexes:** `user_id` UQ · IX `(state_code)` · IX `(income_band)` · GIN IX `(languages)`.

> Profile fields are **explicitly the mirrored input set** of the eligibility
> engine (`eligibility_filter_defs`). Adding a filter in the engine that needs a
> new profile attribute = a new column + a new filter def row in the later
> migration; consumers stay compatible because the engine reads the catalog, not
> field names in code.

## 3. `admin_users` — staff (*21*)

| Column | Type | Constraints | Notes |
| ------ | ---- | ----------- | ----- |
| id | uuid | PK | |
| user_id | uuid | FK, UQ → `users.id` C | one staff account |
| department | varchar(80) | | |
| role_level | varchar(20) | NN def `'editor'` CK `viewer\|editor\|approver\|super_admin` | |
| permissions | varchar(40)[] | def `[]` | granular: `schemes.approve`, `centers.import`, … |
| is_active | bool | def true | |
| created_at / updated_at / last_login_at | timestamptz | | |

**Indexes:** `user_id` UQ · IX `(role_level)`.

---

## 4. Conversation core

### `chat_sessions` — conversation history (*3*)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| user_id | uuid | FK → `users.id` C |
| language | varchar(8) | FK → `languages.code` |
| channel | varchar(16) | NN def `'web'` CK `web\|android\|ios\|whatsapp\|telegram\|ivr` |
| status | varchar(16) | def `'active'` CK `active\|closed\|archived` |
| title | varchar(160) | auto or user-set |
| message_count | int | def 0 |
| last_message_at | timestamptz | |
| created_at / updated_at | timestamptz | |

**Indexes:** IX `(user_id, updated_at DESC)` · IX `(user_id, status)` · IX `(last_message_at)`.
`channel` keeps multi-channel scope (web/mobile/WhatsApp) open (docs `16`,`17`).

### `chat_messages` (*4*)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | bigint ident | PK (hot, append-only) |
| session_id | uuid | FK → `chat_sessions.id` C |
| client_request_id | uuid | UQ *partial where not null* → idempotent sends |
| role | varchar(12) | NN CK `user\|assistant\|system` |
| content_type | varchar(24) | def `'text'` CK `text\|scheme-card\|…` |
| content | text | NN canonical-language text (usually `en` or native) |
| content_language | varchar(8) | FK → `languages.code` |
| rendered_text | text | localized rendering for the user's UI language |
| intent | varchar(40) | detected intent tag |
| payload | jsonb | NN def `'{}'` structured answer (schemes[], centers[], …) |
| status | varchar(16) | def `'complete'` CK queued\|processing\|complete\|failed |
| latency_ms | int | |
| audio_ref | varchar(255) | future server-side STT input |
| created_at | timestamptz | NN |

Mirrors `ChatMessage` in `shared/src/domain/chat.ts`.

**Indexes:** IX `(session_id, created_at)` · IX `(created_at)` · GIN `(payload)` ·
UQ *partial* `(client_request_id)` where not null.

---

## 5. Reference catalogs

### `states` (*13*)

| Column | Type | Notes |
| ------ | ---- | ----- |
| code | varchar(8) | PK (e.g. `IN`, `TN`, `KA`) |
| name | citext | NN |
| name_native | varchar(120) | |
| region | varchar(40) | `north\|south\|east\|west\|northeast\|central\|ut` |
| is_ut | bool | def false |
| active | bool | def true |
| created_at / updated_at | | |

### `languages` (*14*)

| Column | Type | Notes |
| ------ | ---- | ----- |
| code | varchar(8) | PK (`en`, `hi`, `ta`, `bn`, …) |
| name / native_name | varchar(120) | |
| script | varchar(40) | |
| is_rtl | bool | def false |
| stt / tts / indic_trans | bool | capability flags |
| is_fallback | bool | def false — the UI/translation fallback (`en`) |
| active | bool | def true |

Exactly mirrors `SUPPORTED_LANGUAGES` in `shared/src/domain/language.ts`; the
seeds import the same catalog.

### `scheme_categories` (*6*)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| code | varchar(40) | `UQ` (`education`, `health`, `housing`, …) |
| name_en | varchar(120) | |
| parent_id | uuid | FK self, null → hierarchy |
| sort_order | int | def 0 |
| icon | varchar(60) | |
| active | bool | def true |

**Indexes:** `code` UQ · IX `(parent_id)`.

### `document_types` (master catalogue of document kinds)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| code | varchar(32) | **UQ** (`AADHAAR`, `PAN`, `RATION_CARD`, `INCOME_CERT` …) |
| name_en | varchar(120) | |
| category | varchar(24) | CK identity\|address\|income\|age\|caste\|bank\|land\|disability\|family\|photo\|other |
| ocr_supported | bool | def false |
| accepted_formats | varchar(12)[] | def `{pdf,jpg,png,jpeg}` |
| active | bool | def true |

---

## 5. Government schemes — `schemes` (*5*)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| code | citext | **UQ** public slug (`PM-KISAN`) |
| short_name | varchar(80) | |
| name_en | varchar(200) | **NN** canonical English name |
| name_native | varchar(200) | native name (source) |
| description_en | text | **NN** canonical description |
| summary_en | text | short blurb for cards |
| original_language | varchar(8) | FK → languages, def `'en'` |
| ministry | varchar(120) | |
| department | varchar(120) | |
| scope | varchar(12) | **NN** def `'central'` CK `central\|state` |
| primary_category_id | uuid | FK → `scheme_categories`, denorm for fast filter |
| application_mode | varchar(12) | def `'online'` CK `online\|offline\|both` |
| application_cost_inr | numeric(12,2) | |
| is_renewable | bool | def false |
| renewal_frequency_months | int | |
| renewal_process_en | text | |
| age_min / age_max | int | null (mirror common rule) |
| gender_allowed | varchar(12)[] | |
| annual_income_limit_inr | bigint | null | |
| status | varchar(16) | def `'draft'` CK draft\|published\|archived\|expired |
| verification_status | varchar(16) | def `'unverified'` CK unverified\|pending\|verified\|rejected |
| last_verified_at | timestamptz | |
| version | int | def 1 — author revision |
| content_hash | varchar(64) | change detection for data refresh |
| published_at / updated_at / created_at | timestamptz | |
| search_document_en | tsvector | maintained by trigger — en search |
| extra | jsonb | def `{}` | open future fields |

The rich multilingual content (beyond `en`+name_native) lives in `localized_texts`
(doc 05); `schemes` keeps canonical English for search, scoring, and RAG
grounding. Need a field not listed? It goes to `extra` or a new migration — never
a schema break.

**Indexes:** `code` UQ · IX `(status)` · IX `(scope)` · IX `(primary_category_id)`
· GIN IX `(search_document_en)` · GIN triGIN on `name`/`name_native`.

---

## 6. Scheme child content (all FK → `schemes.id` ON DELETE CASCADE)

### `scheme_category_links` (M2M schemes ↔ categories)
| scheme_id uuid FK C · category_id uuid FK C · is_primary bool | **PK**(scheme_id, category_id) |

### `scheme_states` (M2M schemes ↔ applicable states; "all states" support)
| scheme_id uuid FK C · state_code varchar FK C · state_scheme_code varchar60 · is_primary bool · is_excluded bool · validity_from/validity_to date |
**PK**(scheme_id, state_code). For `scope=central`, absence = all states;
`is_excluded` allows an explicit carve-out state. For `scope=state`, exactly one
`primary` row is expected.

### `scheme_tags` (keywords / search tags / aliases)
| scheme_id uuid FK C · tag citext · tag_type varchar(16) `keyword\|search_tag\|alias` |
**PK**(scheme_id, tag). Feeds tag-search and keyword matching.

### `scheme_regional_languages` (*15* Supported Regional Languages)
| scheme_id uuid FK C · language_code varchar(8) FK C · is_original bool · translation_status varchar(16) `not_translated\|pending\|machine_translated\|human_reviewed` · verified bool · last_translated_at |
**PK**(scheme_id, language_code). See doc 05.

### `scheme_benefits` (*9*)
| id uuid PK · scheme_id uuid FK C · benefit_type varchar(24) CK cash\|subsidy\|loan\|kind\|service\|insurance\|other · title_en · amount_min/*max *numeric(14,2)· unit varchar(10) inr\|percent\|kg\|kwh\|nos · periodicity varchar(14) one-time\|monthly\|quarterly\|annual · benefit_text_en text · is_quantified bool · sort_order int |
IX `(scheme_id)`.

### `scheme_application_steps` (*10*)
| id uuid PK · FK C · step_type varchar(16) `application\|renewal\|appeal\|post_approval` · step_no int · mode varchar(12) `online\|offline\|both` · channel varchar(40) portal\|csc\|post_office\|bank\|app · title_en · description_en · instructions_json jsonb · requires_document bool · est_days int · sort_order |
**UK**(scheme_id, step_type, step_no) · IX `(scheme_id)`.

### `scheme_faqs` (*11*)
| id uuid PK · FK C · question_en · answer_en · keywords_en varchar(60)[] · status draft\|published\|archived · sort_order |
IX (scheme_id) · GIN keywords_en. Each FAQ is also a RAG chunk unit (doc 07).

### `scheme_official_links` (*12*)
| id uuid PK · FK C · link_type varchar(32) `official_website\|application_link\|guidelines\|helpline\|grievance\|portal\|pdf` · url · title_en · is_primary bool · verified_at · active bool |
IX `(scheme_id, link_type)` · **UQ partial** `(url)` where active.

### `scheme_documents` (*8* required/optional per scheme)
| id uuid PK · FK C · document_type_id uuid FK `document_types` SN null · custom_name_en varchar(200) null · is_required bool NN def true -> required | □□0 optional · description_en text · accepted_file_formats varchar(12)[] · validity_period_days int null (income cert ≈ 90d) · verification_required bool def false · ocr_supported bool def false · sort_order |
IX `(scheme_id, is_required)`.

---

## 7. Eligibility engine

### `eligibility_filter_defs` (the extensible filter catalog)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| key | varchar(48) | **UQ** (`age`, `gender`, `occupation`, `income`, `education`, `state`, `district`, `disability`, `is_farmer`, `is_student`, `community`, `is_minority`, `is_senior_citizen`, `is_widow`, `is_self_employed`, …) |
| label_en | varchar(120) | |
| value_type | varchar(20) | `number\|string\|boolean\|enum\|range\|set` |
| allowed_values | jsonb | for enum/set |
| unit | varchar(20) | `years\|inr\|km\|percent` |
| source_field | varchar(48) | user_profiles.attribute (or `document` for doc-based) |
| active | bool | def true |

**New eligibility filter = one row.** The evaluator reads this catalog — no code
changes (doc 03).

### `eligibility_rules` (*7*)
| id uuid PK · scheme_id FK C · filter_key FK `filter_defs.key` · operator varchar(16) `eq\|neq\|gte\|lte\|in\|between\|exists\|contains` · value_js jsonb (scalar/min-max/array) · value_min numeric · value_max numeric (materialized for ix) · is_required bool def (hard vs soft) · rule_group varchar(32) def `'default'` (OR-between-groups) · description_en · active bool |

**Indexes:** IX `(scheme_id)` · IX `(filter_key)` · IX *partial* `(filter_key, operator)` WHERE is_required.

---

## 6. Service centres & documents lifecycle

### `service_centres` (*16*)
| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| centre_type | varchar(24) | **NN** CK `csc\|e-sevai\|meeseva\|jan-seva\|district-office\|post_office\|bank\|seva-kendra` |
| name | varchar(200) | |
| state_code | varchar(8) | FK states |
| district | varchar(80) | |
| address | text | |
| lat / lng | double | CK `[-90,90]` / `[-180,180]`; maintained WGS84 |
| geom | geography(Point,4326) | null — derived from lat/lng (trigger) |
| working_hours | jsonb | `{"mon":{"open":"09:00","close":"17:00"}}` |
| contact_number | varchar(24) | |
| email | citext | |
| website | text | |
| verified | bool | def false |
| source | varchar(24) | `manual\|import\|api` |
| active | bool | def true |

**Indexes:** GiST(geom) · IX `(state_code, district)` · IX `(centre_type)`.

### `service_centre_services` (M2M centre ↔ "available services")
| id uuid PK · centre_id uuid FK C · service_code varchar(40) `scheme_application\|pan\|passport\|g2c\|document_fetch\|…` · is_primary bool |
**PK**(centre_id, service_code).

### `user_documents` (citizen's uploaded documents — OCR/verification ready)
| id uuid PK · user_id uuid FK C · document_type_id uuid FK SN · scheme_id uuid null FK SN · file_ref · file_format · ocr_text text null · verification_status varchar(16) `not_submitted\|pending\|verified\|rejected\|expired` · reviewed_by uuid FK admin_users SN · expires_at · created_at |

**Indexes:** IX `(user_id)` · IX `(verification_status)`.

---

## 7. Saved schemes, eligibility results, notifications, feedback, audit

### `user_saved_schemes` (*17*)
| user_id uuid FK C · scheme_id uuid FK C · notify_on_update bool · saved_at |
**PK**(user_id, scheme_id) · IX `(scheme_id)`.

### `user_eligibility_results` (*18*)
| id bigint ident PK · user_id uuid FK C · scheme_id uuid FK SN null · profile_snapshot jsonb · result_status varchar(16) `eligible|likely|needs_more_info|not_eligible` · match_score numeric(5,2) · matched_rules jsonb · broken_rules jsonb · engine_version varchar(20) · created_at |

**Indexes:** IX `(user_id, created_at)` · IX `(result_status)` · IX `(scheme_id)`.
`profile_snapshot` preserves what was evaluated so history is reproducible.

### `notifications` (*19*)
| id bigint ident PK · user_id uuid FK C · scheme_id uuid FK SN null · type varchar(24) `scheme_update|eligibility_match|renewal_reminder|announcement` · title_en/body_en · title_loc/body_loc jsonb · channel varchar(16) push\|email\|sms\|in_app · status queue\|sent\|delivered\|read\|failed\|cancelled · read_at · scheduled_for · sent_at |

**Indexes:** IX `(user_id, status)` · IX partial `(scheduled_for)` where queued · IX `(type)`.

### `feedback` (*20*)
| id bigint ident PK · user_id uuid FK SN · chat_message_id bigint FK SN · scheme_id uuid · rating smallint CK 1..5 · category varchar(24) · comment_en text · language varchar(8) · status new|acknowledged|resolved|archived |

**Indexes:** IX `(status)` · IX `(user_id)` · IX `(category)`.

### `audit_logs` (*22*)
| id bigint ident · issuer_type varchar(10) `user\|admin\|system` · actor_id uuid | entity_type varchar(32) | entity_id varchar(64) | action varchar(32) `create|update|delete|publish|verify|login|import` · before/after/diff jsonb · request_id uuid · actor_ip varchar(45) · user_agent text · language varchar(8) · created_at |

**Indexes:** IX `(entity_type, entity_id)` · IX `(actor_type, actor_id)` ·
IX `(created_at)` · IX `(action)` + consultation per month partition/aggread.

---

## 8. Caches (application-owned, Redis-first with PG fallback)

| Table | Key | Notes |
| ----- | --- | ----- |
| `translations_cache` | (text_hash, language) | machine-translation cache |
| `ai_responses_cache` | (key_hash) | Gemini/cached eligibility output, `expires_at` |
| `notes` | — | never stored per-user beyond consent |

`translations_cache` and `ai_responses_cache` are documented here but are
primarily Redis in production; the PG tables are the durable fallback (doc 05/16).

---

## 9. RAG knowledge base (doc 07 for detail)

| Table | PK | Key FKs | Key fields / indexes |
| ----- | --- | ------- | -------------------- |
| `knowledge_sources` | uuid | scheme_id → schemes · language_state · unique `source_uri` | source_type, official_body, content_hash, status, last_crawled_at |
| `knowledge_chunks` | uuid | source_id → sources C · scheme_id SN | section, language, content, content_loc jsonb, token_count, metadata, chunk_hash **UQ** |
| `embedding_models` | uuid | — | name UQ, provider, dimensions |
| `embeddings` | bigint | chunk_id → chunks C · model_id → models | vector(1536) via pgvector |
| `citations` | bigint | chat_message_id → messages C | chunk_id → chunks, source_id, rank, relevance_score, snippet |

**Indexes:** `knowledge_sources(source_uri)` UQ · `knowledge_chunks(scheme_id,
section)`, GIN `(metadata)`, `chunk_hash` UQ · `embeddings` HNSW/ivfflat index on
`vector` (created when embeddings are enabled — **not now**) · `citations
(chat_message_id)`.

---

## Table inventory vs. required list

| # | Requirement | Table(s) |
|---|-------------|----------|
| 1 | Users | `users` |
| 2 | User Profiles | `user_profiles` |
| 3 | Conversation History | `chat_sessions` |
| 4 | Chat Messages | `chat_messages` |
| 5 | Government Schemes | `schemes` |
| 6 | Scheme Categories | `scheme_categories`, `scheme_category_links` |
| 7 | Eligibility Rules | `eligibility_rules`, `eligibility_filter_defs` |
| 8 | Required Documents | `scheme_documents`, `document_types`, `user_documents` |
| 9 | Scheme Benefits | `scheme_benefits` |
| 10 | Application Steps | `scheme_application_steps` |
| 11 | FAQs | `scheme_faqs` |
| 12 | Official Links | `scheme_official_links` |
| 13 | States | `states` |
| 14 | Languages | `languages` |
| 15 | Supported Regional Languages | `scheme_regional_languages` |
| 16 | Service Centres | `service_centres`, `service_centre_services` |
| 17 | User Saved Schemes | `user_saved_schemes` |
| 18 | User Eligibility Results | `user_eligibility_results` |
| 19 | Notifications | `notifications` |
| 20 | Feedback | `feedback` |
| 21 | Admin Users | `admin_users` |
| 22 | Audit Logs | `audit_logs` |

+ extensibility/storage tables: `languages`, `document_types` catalog,
`eligibility_filter_defs`, `localized_texts`, and the RAG + cache set.