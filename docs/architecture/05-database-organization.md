# 05 — Database Folder Organization

## Ownership

The `database/` directory owns **everything about the database** — migrations,
seeds, and operational scripts — so that:
- DB changes are **reviewed and versioned independently** of server code,
- the same migrations run against local, staging, and Neon production,
- a deploy of the API never silently assumes schema drift.

```
database/
├── README.md
├── migrations/          # Alembic project
│   ├── env.py           #   reads DATABASE_URL, imports app.models metadata
│   ├── alembic.ini      #   config (script_location etc.)
│   └── versions/        #   append-only: 0001_initial.py, 0002_*.py, ...
├── seeds/               # idempotent data loaders
│   ├── states/          #   per-state scheme + center fixtures (CSV/JSON)
│   ├── schemes/         #   central + state scheme catalog
│   └── centers/         #   CSC / e-Sevai centers (CSV, geocoded)
└── scripts/
    ├── migrate.sh       #   alembic upgrade head
    ├── seed.sh          #   idempotent seed load (--dry-run flag)
    ├── backup.sh        #   pg_dump + restore helpers
    └── reset_local.sh   #   drop → migrate → seed for local dev
```

## Planned schema shape (later prompts — NOT implemented now)

Aggregates derived from `shared/src/domain/*.ts`:

| Table                  | Purpose                             | Key notes |
| ---------------------- | ----------------------------------- | --------- |
| `user_profiles`        | Minimal citizen profile             | firebase_uid unique; JSONB consent |
| `chat_sessions`        | Conversation root                   | FK user; language; status |
| `chat_messages`        | Turns (rich payloads)               | payload JSONB; canonical + rendered text |
| `schemes`              | Scheme catalog (bilingual at rest)  | `state_code` nullable → central |
| `scheme_eligibility_rules` | Declarative rules               | JSONB conditions |
| `scheme_documents`     | Required documents                  | ocr_supported flag |
| `service_centers`      | CSC/e-Sevai/Seva Kendra             | `geometry(Point,4326)` PostGIS |
| `translations_cache`   | Language-pair cache                 | (text_hash, src, tgt) unique |
| `ai_responses_cache`   | Cached Gemini/eligibility outputs   | keyed by profile+query hash |

## Conventions

- **One migration per logical change**, never edit an applied one.
- **Append-only `versions/`**; each migration is transactional + reversible.
- **Seeds are idempotent** (`ON CONFLICT ... DO UPDATE`) so CI/local re-runs converge.
- **Extensions bootstrap** in `0001`: `citext`, `pg_trgm` (search),
  `postgis` (geo), `vector` (future embeddings/RAG).
- **No PII in seeds.** Deterministic fake profiles only.
- `state_code` uses a small lookup or free text; central schemes use `NULL` +
  a `scope` column (`central | state`) rather than magic `"*"` inside the DB.

## Operations

```bash
cd database
alembic upgrade head                       # apply
alembic revision --autogenerate -m "…"     # new migration (after model edits)
bash scripts/seed.sh --env local           # idempotent
bash scripts/backup.sh --env prod          # pg_dump
```

## Why migrations live outside the server

Deploy pipelines (Railway) run the server image; migrations run as a **release
phase** step pointing at the same `database/` directory, and can be retried/rolled
back without redeploying the API. Prevents "code ahead of schema" incidents.
