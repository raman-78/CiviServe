# CiviServe — Backend

FastAPI + SQLAlchemy 2 + PostgreSQL service for the multilingual citizen
service chatbot. Implements the full API: public scheme catalog + search,
Firebase auth, streaming Gemini chat with grounding, translation, document
uploads + OCR, centers, eligibility, and admin.

## Folder structure

```
server/
├── app/
│   ├── main.py                  # App factory: lifespan, middleware, router mount, docs
│   ├── api/
│   │   └── v1/
│   │       ├── routers/         # One router per resource:
│   │       │   ├── chat.py      #   POST /chat/message, /chat/sessions/...
│   │       │   ├── schemes.py   #   GET /schemes, GET /schemes/{code}
│   │       │   ├── centers.py   #   GET /centers/nearby
│   │       │   ├── documents.py #   document checklists + OCR upload (future)
│   │       │   ├── auth.py      #   Firebase token exchange (thin)
│   │       │   └── health.py    #   /healthz, /readyz, /metrics
│   │       └── dependencies.py  # get_db, get_current_user, get_rate_limiter
│   ├── core/
│   │   ├── config.py            # pydantic-settings (reads .env)
│   │   ├── logging.py           # structlog JSON config, request-id context
│   │   ├── security.py          # Firebase verification, token utils
│   │   ├── errors.py            # AppError hierarchy + exception handlers
│   │   └── rate_limit.py        # Redis token-bucket helpers
│   ├── db/
│   │   ├── base.py              # Declarative Base + metadata
│   │   ├── session.py           # async engine + session factory
│   │   └── redis.py             # redis client wrapper
│   ├── models/                  # SQLAlchemy ORM models (one file per aggregate)
│   ├── schemas/                 # Pydantic request/response contracts
│   ├── repositories/            # data-access layer (single responsibility)
│   ├── services/                # domain logic (no HTTP awareness)
│   │   ├── ai/                  #   GeminiProvider (LLM abstraction)
│   │   ├── translation/         #   IndicTrans2 client + Google fallback
│   │   ├── speech/              #   cloud STT/TTS (future)
│   │   ├── geo/                 #   OSM/Google geocoding + nearby query
│   │   ├── ocr/                 #   PaddleOCR client (future)
│   │   └── recommendation/      #   eligibility engine
│   ├── middleware/              # request-id, CORS, error, prometheus
│   └── utils/                   # helpers (caching, retries, idgen)
└── tests/
    ├── unit/                    # services, repositories (no network/DB)
    ├── integration/             # FastAPI TestClient + test DB
    └── fixtures/                # factories + sample scheme data
```

## Layering rules (enforced in review)

1. **`routers` → `services` → `repositories` → `db`.** Routers never touch
   SQLAlchemy sessions directly; repositories never import HTTP concerns.
2. **Pydantic schemas are the API boundary**; ORM models never cross it.
3. **Services are provider-agnostic.** `ai/`, `translation/`, `speech/` expose
   interfaces so Gemini/IndicTrans2/cloud STT can be swapped.
4. `core/` has no imports from `app` packages (dependency-inversion for config,
   logging, security).

## Development

```bash
python -m venv .venv && .venv\Scripts\Activate.ps1   # Windows
pip install -e .
pip install -r requirements-dev.txt

# Run with reload, hot-reload on change
python -m uvicorn app.main:app --reload --port 8000

# Quality gates
ruff check app tests
ruff format --check app tests
mypy app
pytest
```

## Conventions

- Python 3.11+, strict typing (`mypy`), `ruff` lint/format.
- All configuration via environment (12-factor) — see `app/core/config.py`;
  `.env.example` lists every variable.
- Errors propagate as a typed envelope `{ "error": { "code", "message",
  "details", "requestId" } }` (see `docs/architecture/13-error-handling.md`).
- Logging is structured JSON via structlog with a `requestId` correlation field
  (see `docs/architecture/14-logging.md`).
