# CiviServe — Database

Centralized PostgreSQL schema management for the monorepo. Alembic migrations
and seed data live here, **outside** the server package, so they can be run
independently of the API (CI, staging, local).

## Folder structure

```
database/
├── migrations/       # Alembic versions: 0001_initial, 0002_schemes, ...
│   ├── env.py        #   Alembic env (reads DATABASE_URL)
│   └── versions/     #   Ordered, immutable migration scripts
├── seeds/            # Idempotent seed data loaders
│   ├── states/       #   State-level scheme fixtures (per-state CSV/JSON)
│   ├── schemes/      #   Central + state scheme catalog
│   └── centers/      #   CSC / e-Sevai center fixtures
├── scripts/          # Ops tooling
│   ├── migrate.sh    #   run latest migrations
│   ├── seed.sh       #   load seed data (idempotent, dry-run flag)
│   ├── backup.sh     #   pg_dump helpers
│   └── reset_local.sh#   local dev: drop + migrate + seed
└── README.md
```

## Canonical stack

| Piece         | Choice                                        | Why                                        |
| ------------- | --------------------------------------------- | ------------------------------------------ |
| RDBMS         | PostgreSQL 16 (Neon for hosting)              | JSONB, robust geo, proven scale            |
| Migrations    | Alembic                                       | Async-friendly, ordered versions           |
| Driver        | psycopg3 / asyncpg (SQLAlchemy async)         | async I/O on FastAPI                       |
| Extensions    | `citext`, `pg_trgm`, `postgis`, `pgvector`    | locale-safe text, fuzzy search, geo, RAG   |
| Enum strategy | Postgres native enums via Alembic (`sa.Enum`) | referential integrity at DB level          |

> **No schema is generated yet (per Prompt 1).** The migration files, seeds, and
> extension setup are produced by later prompts. This folder defines *where*
> they live and *how* they are versioned.

## Conventions

- **One migration per logical change.** Never edit an applied migration; add a
  new version (schema is immutable once merged).
- **Seeds are idempotent** — safe to re-run (`ON CONFLICT` upserts). Seed data
  ships in code so environments converge.
- **`migrations/versions/` is append-only** and reviewed like code.
- Extensions enabled once at bootstrap: `CREATE EXTENSION IF NOT EXISTS
  citext, pg_trgm, postgis, vector;` — run in a dedicated initial migration.
- Sensitive state: **no PII in seeds**; use deterministic fake profiles only.
- Each migration is wrapped in a transaction and must be reversible
  (`upgrade` + `downgrade`).

## Commands

```bash
# Apply all pending migrations
cd database && alembic upgrade head

# Revert one step
cd database && alembic downgrade -1

# Generate a new migration after model changes
alembic revision --autogenerate -m "add scheme categories"

# Idempotent seed
bash database/scripts/seed.sh --env local
```
