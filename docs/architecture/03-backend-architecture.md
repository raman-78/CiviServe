# 03 — Backend Architecture

## Overview

FastAPI service, **clean/hexagonal-inspired layering**: routers (HTTP) → services
(domain) → repositories (data) → db. Every external capability (AI, translation,
speech, geo, OCR) is behind a **provider interface** so implementations are swappable.

```
HTTP request
   │
   ▼
Middleware ── request-id · CORS · error envelope · Prometheus
   │
   ▼
Router (api/v1/routers)     ← validates input via Pydantic schemas
   │
   ▼
Dependencies                 ← auth (Firebase), rate limiter, db session
   │
   ▼
Service (app/services)       ← business logic, provider-agnostic
   │        │        │
   │    Provider interfaces:
   │   GeminiProvider · TranslationProvider · GeoProvider · OcrProvider · SpeechProvider
   │
   ▼
Repository (app/repositories) ← data access, one per aggregate
   │
   ▼
SQLAlchemy async session → PostgreSQL (Neon) + Redis (cache/limits/queues)
```

## Layers & rules (enforced in review + mypy/ruff)

| Layer        | Import rules                                              | Notes |
| ------------ | --------------------------------------------------------- | ----- |
| `api/routers` | → services, dependencies, schemas                        | Never touches ORM/session |
| `dependencies`| → core security, db session, schemas                     | DI via FastAPI `Depends` |
| `services`   | → repositories, providers (interfaces), core, schemas    | No HTTP/request awareness |
| `repositories` | → models, db                                            | One class per aggregate |
| `models`     | → db.base                                                 | SQLAlchemy only, no Pydantic |
| `schemas`    | → none (pydantic)                                        | API contracts (mirror `shared`) |
| `core`       | → none from `app` (config, logging, security, errors)    | Imported by everyone, imports nothing internal |

**Absolute rules**
- Routers never import `models` directly; they exchange `schemas` only.
- `schemas` serialize to the exact field names in `shared/src/domain/*.ts`.
- Services never read `os.environ`; they read `core.config` (pydantic-settings).
- Provider implementations live in `services/<domain>/providers/` and are selected
  by config (`app.core.config`), enabling mock/stub swapping in tests.

## Provider interfaces (MVP = thin implementations)

```python
# services/ai/provider.py (design contract, code comes in a later prompt)
class LlmProvider(Protocol):
    async def generate(self, *, messages, schema=None) -> LlmResponse: ...
# Implementations: GeminiProvider (prod), MockProvider (tests)

# services/translation/provider.py
class TranslationProvider(Protocol):
    async def translate(self, text, *, src, tgt) -> str: ...
# Implementations: IndicTrans2Client (preferred), GoogleTranslateClient (fallback)

# services/geo/provider.py
class GeoProvider(Protocol):
    async def geocode(self, query) -> GeoPoint | None: ...
    async def nearby(self, *, point, radius_km) -> list[ServiceCenter]: ...
# Implementations: OpenStreetMapClient (MVP), GoogleMapsClient (future)

# services/speech/, services/ocr/ — cloud STT/TTS + PaddleOCR (future prompts)
```

## Async execution model

- **Async I/O everywhere** (SQLAlchemy async + asyncpg, httpx for outbound).
- **Heavy/blocking work** (IndicTrans2 batch translation, OCR on large images,
  long Gemini runs) is deferred to a task queue (Redis + arq/Celery) rather than
  blocking a request worker — designed in now, wired in a later prompt.
- Background jobs: translation warm-cache, scheme-verification crawler,
  center-data refresh.

## Module map

| Module      | Contents |
| ----------- | -------- |
| `core/config.py` | pydantic-settings singleton reading `.env` |
| `core/logging.py`| structlog JSON config + request-id binding |
| `core/security.py`| Firebase ID-token verification, role guards |
| `core/errors.py` | `AppError` hierarchy + global handlers |
| `core/rate_limit.py` | Redis token bucket |
| `middleware/` | RequestID, CORS, ErrorEnvelope, Prometheus |
| `services/` | ai, translation, speech, geo, ocr, recommendation |
| `repositories/` | user_repo, session_repo, message_repo, scheme_repo, center_repo |

## Testing

- **Unit** — services with MockProviders; no network/DB.
- **Integration** — FastAPI TestClient against a test DB; provider stubs.
- **Contract** — response JSON validated against JSON Schema in `shared/schemas`.
