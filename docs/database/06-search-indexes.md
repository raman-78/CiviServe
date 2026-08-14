# 06 — Search & Index Strategy

## Index catalogue (by purpose)

| Purpose | Index | Type | Table |
| ------- | ----- | ---- | ----- |
| Lookup by identity | `firebase_uid`, `email`, `phone` | btree UQ | users |
| Conversation list | `(user_id, updated_at DESC)`, `(user_id, status)` | btree | chat_sessions |
| Timeline | `(session_id, created_at)`, `(created_at)` | btree | chat_messages |
| Scheme lookup/filter | `code` UQ, `(status)`, `(scope)`, `(primary_category_id)` | btree | schemes |
| Keyword/English search | `search_document_en` | GIN tsvector | schemes |
| Fuzzy/typo search | `name`, `name_native`, `localized_texts.value` | GIN pg_trgm | schemes / localized_texts |
| Regional-language search | per-language tsvector (see below) | GIN | search alias |
| Tag search | `tag` (btree UQ composite) + GIN keywords | btree/GIN | scheme_tags / scheme_faqs |
| Eligibility fast-path | `(filter_key, operator)` partial on required; `schemes(scope, category)` | btree | eligibility_rules / schemes |
| Geo "near me" | `geom` | **GiST** | service_centres |
| District browse | `(state_code, district)`, `(centre_type)` | btree | service_centres |
| Notifications | `(user_id, status)`, partial `(scheduled_for)` | btree | notifications |
| Audit | `(entity_type, entity_id)`, `(created_at)`, `(action)` | btree | audit_logs |
| RAG | `source_uri` UQ, `(scheme_id, section)`, GIN `metadata`, `chunk_hash` UQ | btree/GIN | knowledge_sources/chunks |
| Vector (future) | HNSW on `vector` | pgvector | embeddings |

> Index budget rules: every FK gets an index; partial indexes where a predicate
> always applies (`WHERE is_required`, `WHERE active`); never index low-cardinality
> booleans on their own.

## Search strategy (six requirements)

### 1. Keyword search
PostgreSQL full-text on `schemes.search_document_en` (English weight) and
per-language vectors. tsvector is maintained by trigger on publish.

### 2. Semantic search (future, architected now)
`embeddings` + HNSW vector index (pgvector). Query embedding → cosine neighbors →
merge with keyword candidates (hybrid, doc 07). Enabled when embeddings ship;
schema and extension are already prepared.

### 3. Category search
`scheme_categories` hierarchy + `scheme_category_links`; category filter is a
btree join, plus `schemes.primary_category_id` fast path.

### 4. Voice query support
Voice → STT → text (same pipeline). The search text is already normalized; a
`chat_messages.audio_ref` column preserves the audio for future server-side STT
fallback. No separate search path — voice is a text-input adapter.

### 5. Misspelled words
**pg_trgm** `similarity()`/`%` on `schemes.name`, `name_native`, and
`localized_texts.value` (with language predicate). Query side uses a tokenizer
that also strips diacritics and normalizes Devanagari/Tamil forms
(via `unaccent` + language normalizer). Suggestion endpoint: top-5 trigram
matches with score.

### 6. Regional-language search
- Primary: `localized_texts.value` trigram-indexed (per-language queries filter
  `language = $lang`).
- Secondary: a maintained **per-language tsvector alias** (`scheme_search_lang`)
  with `to_tsvector` configs for Indic languages (custom dictionaries where
  available; otherwise trigram covers it).
- Future: multilingual embeddings make regional search cross-language
  (query in Tamil → English content) with one model.

## Result ranking (SQL-level baseline)

Score = weighted blend of:
- full-text rank (`ts_rank`) on the query language vector,
- trigram `similarity()` for fuzzy/typo signals,
- category/state filter match boost,
- `matchScore` from the eligibility engine when profile context is present,
- recency (`last_verified_at`) as a tie-breaker.

The chat uses the same ranking but re-ranks top-K via the LLM with RAG
grounding (doc 07). Ranking is **language-aware**: scores are computed per
language and never mixed across scripts.

## Search correctness guards

- `content_hash` triggers re-indexing when content changes.
- Search indexes are rebuilt via `scripts/` (refresh `search_document_en`, the
  language alias, and trigram metadata) as a background maintenance job, not in
  the request path.
- `explain` budgets: target `< 50 ms` for keyword/category, `< 150 ms` for fuzzy
  on the full catalog at 10k+ schemes.
