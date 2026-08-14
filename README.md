# CiviServe — Multilingual Citizen Service Chatbot for Government Schemes

> HackElite 2026 · Full-stack demo (Prompt 15 of 15 — final integration).

An AI-powered multilingual assistant that helps Indian citizens discover
government welfare schemes, check eligibility, understand required documents,
locate nearby CSC / e-Sevai centers, and apply — in **text and voice**, across
**13 Indian languages**.

---

## Tech Stack

| Layer     | Stack                                                                  |
| --------- | ---------------------------------------------------------------------- |
| Frontend  | React 19 · TypeScript · Vite · Tailwind CSS · shadcn/ui · Framer Motion |
| Backend   | FastAPI · Python 3.11 · SQLAlchemy 2 · Pydantic v2                      |
| Database  | PostgreSQL 16 (Neon) + PostGIS + pgvector                               |
| Auth      | Firebase Authentication                                                 |
| AI        | Google Gemini (via server proxy — keys never ship to the browser)       |
| Translate | IndicTrans2 (preferred) → Google Translate fallback                     |
| Speech    | Browser Web Speech (MVP adapters; cloud-ready interfaces)               |
| OCR       | Tesseract.js (browser) → PaddleOCR (backend, future)                    |
| Maps      | Leaflet + OpenStreetMap (MVP; Google Maps adapter-ready)                |
| Deploy    | Vercel (client) · Railway/Render (server) · Neon (DB)                   |

---

## Monorepo Layout

```
chatbot/
├── client/          # React 19 SPA (Vite, Tailwind, shadcn/ui)
├── server/          # FastAPI service (app factory, layered architecture)
├── database/        # Alembic migrations, seeds, ops scripts (DB-agnostic of API)
├── shared/          # Canonical domain models (TS types + JSON Schema)
├── assets/          # Brand + presentation media (no user data)
├── docs/            # Architecture & decision records
├── .github/         # CI + deploy workflows
├── package.json     # pnpm workspaces + orchestrator scripts
└── pnpm-workspace.yaml
```

Full structure: [`docs/architecture/01-project-structure.md`](docs/architecture/01-project-structure.md)

---

## Quick Start (local dev)

Prereqs: Node ≥ 20, pnpm ≥ 9, Python ≥ 3.11.

```bash
# 1. Install client toolchain
pnpm install

# 2. Frontend
pnpm --filter @schemesathi/client dev        # http://localhost:5173

# 3. Backend (Python virtual environment)
python -m venv server/.venv
server\.venv\Scripts\Activate.ps1            # Windows
pip install -e server
pip install -r server/requirements-dev.txt
python -m uvicorn app.main:app --reload --app-dir server   # http://localhost:8000/docs

# 4. Environment (fill real values from .env.example)
cp client/.env.example client/.env.local     # Firebase web config, app meta
cp server/.env.example server/.env           # DATABASE_URL, Gemini key, Firebase SA
```

> The public scheme catalog (`/api/v1/schemes`) works with a local database and
> the seeded demo schemes (see `server/app/db/seeds.py`). Authentication,
> AI chat, and translation need the Firebase + Gemini credentials above.

---

## Documentation Map

| Area                        | Doc                                                                                  |
| --------------------------- | ------------------------------------------------------------------------------------ |
| Project structure           | [01-project-structure.md](docs/architecture/01-project-structure.md)                  |
| Frontend architecture       | [02-frontend-architecture.md](docs/architecture/02-frontend-architecture.md)          |
| Backend architecture        | [03-backend-architecture.md](docs/architecture/03-backend-architecture.md)            |
| API organization            | [04-api-organization.md](docs/architecture/04-api-organization.md)                    |
| Database organization       | [05-database-organization.md](docs/architecture/05-database-organization.md)          |
| Shared models               | [06-shared-models.md](docs/architecture/06-shared-models.md)                          |
| Component hierarchy         | [07-component-hierarchy.md](docs/architecture/07-component-hierarchy.md)              |
| Routing architecture        | [08-routing-architecture.md](docs/architecture/08-routing-architecture.md)            |
| State management            | [09-state-management.md](docs/architecture/09-state-management.md)                    |
| Environment variables       | [10-environment-variables.md](docs/architecture/10-environment-variables.md)          |
| Configuration files         | [11-configuration-files.md](docs/architecture/11-configuration-files.md)              |
| Dependencies                | [12-dependencies.md](docs/architecture/12-dependencies.md)                            |
| Error handling              | [13-error-handling.md](docs/architecture/13-error-handling.md)                        |
| Logging                     | [14-logging.md](docs/architecture/14-logging.md)                                      |
| Security                    | [15-security.md](docs/architecture/15-security.md)                                    |
| Scalability                 | [16-scalability.md](docs/architecture/16-scalability.md)                              |
| Future extensibility        | [17-extensibility.md](docs/architecture/17-extensibility.md)                          |
| Development workflow        | [18-development-workflow.md](docs/architecture/18-development-workflow.md)            |
| Git branching strategy      | [19-git-branching.md](docs/architecture/19-git-branching.md)                          |
| Decision records            | [ADR template](docs/decisions/README.md)                                              |

---

## Commands (root orchestrator)

```bash
pnpm dev:client       # run frontend dev server
pnpm dev:server       # run backend with reload
pnpm verify           # typecheck + lint + test (client & shared)
pnpm lint:server      # ruff check
pnpm test:server      # pytest
```

### Quality gates

```bash
pnpm verify                          # client & shared: tsc + eslint + vitest
python -m ruff check server          # Python lint
python -m ruff format --check server # Python formatting
python -m mypy server                # Python typecheck
python -m pytest server/tests        # Python tests
```

---

## Status

Complete: monorepo foundation, shared domain contracts, FastAPI backend
(schemes, auth, chat/SSE + Gemini RAG, translation, documents, centers,
eligibility, admin), React client (browse/search schemes, chat, profile,
documents, centers map, settings, admin dashboard), 13-language UI, voice
(click-only), and E2E-ready demo data.
