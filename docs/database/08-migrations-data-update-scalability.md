# 08 — Migrations, Data Update & Scalability

## Migration strategy (Alembic, in `database/`)

One migration per logical change; append-only `versions/`; each wrapped in a
transaction and reversible. Bootstrapping order:

| Rev | Contents |
| --- | -------- |
| `0001_initial` | Extensions (`citext`, `pg_trgm`, `pgvector`, `postgis`, `pgcrypto`), enums |
| `0002_identity` | `users`, `user_profiles`, `admin_users`, `audit_logs`, `notifications` |
| `0003_conversation` | `chat_sessions`, `chat_messages` (+ idempotency partial index) |
| `0004_reference` | `states`, `languages` (seed catalog) |
| `0005_schemes` | `schemes`, `scheme_categories`, links/states/tags, child content |
| `0006_eligibility` | `eligibility_filter_defs` (seed), `eligibility_rules`, fast-path indexes |
| `0007_documents_centres` | `document_types` (seed), `scheme_documents`, `user_documents`, `service_centres`, `service_centre_services` |
| `0008_user_features` | `user_saved_schemes`, `user_eligibility_results`, `feedback` |
| `0009_multilingual` | `localized_texts`, `scheme_regional_languages`, `translations_cache`, `ai_responses_cache` |
| `0010_rag` | `knowledge_sources`, `knowledge_chunks`, `embedding_models`, `embeddings` (column; vector index **only** when enabled), `citations` |
| `0011_*…` | future filters, columns, or new feature sets (append-only) |

Guards:
- Add nullable column → backfill → `ALTER … SET NOT NULL` in separate steps.
- Never mutate an already-applied migration; new state is a new revision.
- `alembic check` + `alembic upgrade head --sql` dry-run in CI and the release
  phase (see `docs/architecture/05`).
- Custom type changes (enum) use a new enum + check-migrate-dir pattern.

## Data update strategy (the *living* knowledge base)

### Pipelines

1. **Reference data** (`languages`, `states`, `scheme_categories`,
   `document_types`, `eligibility_filter_defs`) — idempotent seeds shipped in
   code; `ON CONFLICT … DO UPDATE`.
2. **Scheme catalog** — authoritative import from official sources via
   `knowledge_sources` + content-editor workflow; writers don't hand-edit prod.
   Each edit bumps `version`, recomputes `content_hash` (deploy change detection),
   adds an `audit_logs` row, and enqueues translations.
3. **Service centres** — `source = 'api'` sync CSV/API dumps via
   `database/scripts` (idempotent upsert on `service_centre_id`/uri), geocoding
   before insert.
4. **Translations** — scheduled worker translating new/changed content to
   `scheme_regional_languages` targets, writing `localized_texts`, updating
   `ai_responses_cache`/`translations_cache`.
5. **RAG sync** — doc 07 §8: crawl → parse → chunk → hash-diff → review →
   publish.

### Verification & freshness
- Every published scheme carries `verification_status` + `last_verified_at`; a
  periodic auditor flags stale schemes (`> N months`) for re-verify.
- `notifications` ("scheme updated") fire on `verification_status`/content
  changes for `user_saved_schemes` subscribers.
- `audit_logs` records every mutation with `before/after` JSONB for rollback.

### Rollback & private keys
- Data safety: pg_dump via `database/scripts/backup.sh`; migrations reversible;
  soft-delete everywhere content-shaped.
- All secrets remain in env/CI secrets (doc 15); migrations never embed them.

## Scalability strategy (all states · thousands of schemes · millions of users)

### Tier-1 (MVP, single Neon PG)
- Connection pooling (`pgbouncer`), async sessions, request-bound.
- Index fast-paths (doc 06) keep catalog read-friendly at 10k schemes.
- `chat_messages` bigint PK + `(session_id, created_at)` for linear history reads.

### Tier-2 (growth)
- **Read replicas** for scheme catalog, centers, RAG retrieval (read-heavy).
- **Partitioning** on hot append-only tables:
  - `chat_messages`, `audit_logs`, `user_eligibility_results` by month
    (range partitioning on `created_at`); partition pruning keeps index small.
  - `user_documents` by user prefix (or hash) when file volume grows.
- **Caching** of schemes/translations/eligibility/AI in Redis; catalog version key
  (`scheme_catalog_version`) invalidates cleanly.
- **Search index** on a dedicated search replica (or pgvector index there) so
  FTS/vector load never competes with OLTP.

### Tier-3 (very large, optional)
- Async ETL/OCR/translation on a worker pool (Redis/arq) — never in request path.
- Sharding direction: per-state logical partitions or id-hash for chat + results;
  the UUID v7 PKs make cross-region/shard keys easy.
- Geo centers: partition `service_centres` by `region` (north/south/east/west)
  with per-region GiST indexes; global `near me` still hits the region list first.

### Mobile / OCR / voice / AI support
- All external IDs are `uuid` → safe for mobile sync and object-store refs.
- `chat_messages.channel`, `audio_ref`, `user_documents.file_ref + ocr_text`
  are the extension points for app/OCR/voice — no schema churn when those
  prompts arrive.
- RAG + hybrid structured retrieval scales answer quality without re-architecting
  the store (doc 07).

## Cost & size controls

- Token budgets per session; AI cache keyed by (profile_hash, query_hash).
- Translation & embedding caches with TTL to bound compute (docs 05/07).
- `audit_logs` + `chat_messages` retention job (after compliance window) keeps
  the hot tables lean.