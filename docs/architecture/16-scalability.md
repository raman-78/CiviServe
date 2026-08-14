# 16 — Scalability Considerations

Design for **multi-state, high-concurrency, multilingual** use — including
celebrity announcements that spike scheme lookups 100x.

## Stateless API → horizontal scale

- FastAPI app is **stateless**; sessions live in Postgres, cache/limits in Redis.
- Deploy more replicas (Railway/Render horizontal scale) behind a load balancer;
  `/healthz` + `/readyz` for orchestration probes.
- Uvicorn workers per CPU; **background jobs off the request path** via
  Redis-backed queue (arq/Celery) for heavy AI/translation/OCR — a request never
  blocks on batch work.

## Database (PostgreSQL on Neon)

- **Connection pooling:** `DB_POOL_SIZE`/`MAX_OVERFLOW` + `pgbouncer` for Neon
  (low connection budget); async sessions bound per-request.
- **Index strategy:** indexes on `schemes(state_code, category)`,
  `scheme_eligibility_rules(scheme_id)`, `chat_sessions(user_id, updated_at)`,
  GIN on `schemes(tags)` via `pg_trgm`; PostGIS spatial index on
  `service_centers.geometry` for `ST_DWithin` nearby queries.
- **Read replicas** (future) for the catalog/messages read-heavy endpoints.
- Migrations run in **release phase**, never from a worker, so N replicas
  never race schema changes.

## Caching layers (by volatility)

| Data | Cache | TTL |
| ---- | ----- | --- |
| Scheme catalog | Redis (+ client query cache) | hours |
| Translated scheme text | Redis `translations_cache` | 7d |
| AI responses | Redis `ai_responses_cache` (profile+query hash) | 1d |
| Nearby centers | Redis + client `staleTime` | minutes |
| Supported languages | static in `shared` | N/A |

Invalidation: content edits bump a `scheme_catalog_version` key; clients revalidate.

## AI budget & latency

- **Tiering:** cheap model for intent/classification, better model for generation
  (configurable). Cache hits short-circuit Gemini entirely.
- **Prompt compression:** send only eligibility-relevant profile fields + fetched
  catalog rows, not raw DB dumps.
- **Batching:** bulk translation processed in the queue; language warm-cache job
  pre-translates top-N schemes nightly.

## Frontend & CDN

- Static assets on Vercel edge/CDN; aggressive long-lived cache for hashed assets.
- Route-level code splitting keeps the chat page light; heavy libs (Tesseract,
  Leaflet) isolated chunks.
- PWA/offline cache for the scheme catalog (future) to serve low-bandwidth users.

## Multilingual scale-out

- Translation cache keyed by `(text_hash, src, tgt)` — repeated user queries
  reuse translations.
- IndicTrans2 deployment (GPU) behind the translation provider; fallback to
  Google keeps SLO if IndicTrans2 saturates.
- Adding a language = resource files + `SUPPORTED_LANGUAGES` entry + capability
  flags — no code change.

## Observability gates

- Latency SLOs (chat P95), error budget, AI cost per session, translation
  hit-rate, rate-limit counters — dashboards + alerts (doc 14).
- Load tests per feature prompt (scheme spike simulation) with `locust` (future).
