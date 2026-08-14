# 07 — RAG Knowledge Base Architecture

Retrieval-Augmented Generation done **right for government schemes**: the LLM
answers only from retrieved official content, with citations. The data layer is
fully designed now; **embeddings are not implemented yet** — this doc is the
contract later prompts implement against.

## 1. Knowledge source planning

| Source type | Examples | Priority | Trust |
| ----------- | -------- | -------- | ----- |
| Official scheme portals | pmkisan.gov.in, dbtwbiculture.gov.in | high | primary |
| Ministry/state department sites | dbt, agriculture, social-justice | high | primary |
| Gazette notifications & PDFs | eligibility/format PDFs | high | primary |
| MyGov / scheme aggregator pages | mygov.in, states' sevak portals | med | cross-check |
| Scheme docs (acts, guidelines) | PDS, PMAY guidelines | high | primary |
| FAQ/help pages | portal help, CSC guides | med | secondary |

`knowledge_sources` records each: `source_uri` (unique), `source_type`,
`official_body`, `state_code`, `language`, `content_hash`, `status`
(`discovered → downloaded → parsed → chunked → embedded → failed → skipped`),
`last_crawled_at`, `source_metadata` (JSONB: published date, gazette no., PDF
page count, portal section).

**Trust policy:** only `official_body` in an allowlist seeds the KB; aggregator
content is marked `secondary` and never used as a sole citation.

## 2. Chunking strategy

- **Unit = section.** Scheme content is chunked along its natural structure:
  description, eligibility, benefits, application steps, FAQ, documents,
  renewal. Each `scheme_application_step` and each `scheme_faqs` row is a chunk
  by itself (small, high-value).
- **Budget:** 200–500 tokens/chunk; headers kept with the chunk; ≤10% overlap
  across section boundaries for continuity.
- `knowledge_chunks` stores `section`, `seq_no`, `chunk_type`
  (`text | faq | table | heading`), `metadata` (JSONB: heading path, FAQ id, step
  no, source URL, publish date), `token_count`, and `chunk_hash` (unique) so the
  same official text never duplicates.
- FAQ question + answer = one chunk (retrieval hits both).

## 3. Metadata design (the "hard filters")

Every chunk carries metadata that turns generic vector search into **gated
retrieval**:

```
scheme_id        → hard filter: answer only about that scheme
state_code       → hard filter: state-specific schemes
language         → language of the chunk text
section          → type-aware retrieval (eligibility vs documents vs steps)
publish_date     → freshness ranking + "scheme revised" signals
source_uri       → citation + verification back-link
```

Retrieval **always** filters `scheme_id`/`state`/`language` before scoring — this
prevents cross-scheme hallucination and is the single biggest accuracy win.

## 4. Embedding storage planning (schema ready, not implemented)

| Table | Purpose |
| ----- | ------- |
| `embedding_models` | model registry: `name` (unique), `provider`, `dimensions`, `is_active` |
| `embeddings` | `chunk_id` → model_id → `vector` (pgvector), `created_at` |

- **Model versioning:** embeddings are keyed by `model_id`; a model upgrade
  writes a new embedding set, old stays queryable until migration completes
  (zero-downtime swap).
- **Index:** HNSW (`vector_cosine_ops`) when enabled; `ivfflat` fallback for
  smaller corpora. Dimension fixed per model (`text-embedding-004`=768,
  multilingual-e5-large=1024, etc.); `VECTOR(n)` created by the migration that
  enables embeddings.
- **Language:** use a **multilingual embedding model** so Tamil/English queries
  and chunks live in one space; keep `chunks.language` as metadata regardless.

## 5. Retrieval pipeline

```
user message (canonical language)
   │  1. intent + filters: scheme/state/language/category from context
   ▼
2. Candidate generation (HYBRID):
   ├─ vector: embed query → HNSW top-K per language model
   ├─ keyword: tsvector/trigram on knowledge_chunks.content (+ localized_texts)
   └─ structured: eligibility_rules, scheme_documents, service_centres (exact)
   ▼
3. Hard-filter (scheme_id, state, language, section)
   ▼
4. Rerank: weighted(cosine, bm25/ts_rank, recency, filter exactness);
      optional cross-encoder rerank on top-K (future)
   ▼
5. Ground: assemble context with source URIs → prompt to LLM
   ▼
6. Cite: save retrieved chunks to citations (per chat_message)
   ▼
answer rendered (translated to user's language)
```

## 6. Ranking strategy

`score = w1·vector_cos + w2·ts_rank + w3·recency_decay + w4·filter_boost`
- filter exactness (scheme/state/section match) weighs highest — a perfect
  eligibility chunk for the right scheme beats a vague similarity.
- `knowledge_chunks.metadata.publish_date` drives recency decay for "scheme
  changed last month" sensitivity.
- LLM re-rank happens only on top-8 (cost control).

## 7. Citation support

`citations` links each grounded answer to the chunks used:
`chat_message_id → chunk_id → source_id → scheme_id`, with `rank`,
`relevance_score`, `snippet`, and `span_json` (character offsets in rendered
text). The UI renders "Sources: pmkisan.gov.in" per answer, satisfying the
transparency requirement and the audit trail.

## 8. Future synchronization from official sources

- **Scheduler** (background worker) polls `knowledge_sources.status =
  'discovered'` → download → parse → chunk → hash → diff.
- **Change detection:** `content_hash` per source; unchanged → skip; changed →
  re-chunk that source only, mark old chunks `status='superseded'`, keep them for
  audit, update `schemes.content_hash` + `schemes.last_verified_at`.
- **Review gate:** content-editor approves new chunks (`knowledge_chunks.status =
  'draft' → 'published'`) before they feed retrieval; `audit_logs` records the
  action.
- **Deactivation:** an official page's removal flags the scheme
  `verification_status='pending'` and queues a content-editor review — the
  chatbot then answers "this scheme is under review" instead of stale facts.

## 9. Interaction with the scheme catalog

`knowledge_chunks.scheme_id` keeps RAG content attached to `schemes`, so the
chat can (a) answer from structured data (eligibility engine, documents,
centres) and (b) ground narrative answers in official chunks — a
**hybrid structured + unstructured** design where each answer picks its best
source.
