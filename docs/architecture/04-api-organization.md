# 04 — API Folder Organization

## Convention

Versioned REST under `server/app/api/v1/`. One **router per resource**, a shared
`dependencies.py` for DI, and no business logic in the router layer.

```
server/app/api/
└── v1/
    ├── __init__.py          # APIRouter aggregator → mounted in main.py under /api/v1
    ├── dependencies.py      # get_db, get_current_user, get_rate_limiter,
    │                        #   get_translation_provider, get_llm_provider, ...
    └── routers/
        ├── health.py        # GET /healthz, /readyz, /metrics (public, no auth)
        ├── auth.py          # POST /auth/guest (anonymous), GET /auth/me
        ├── chat.py          # POST /chat/sessions, POST /chat/sessions/{id}/messages,
        │                    #   GET /chat/sessions/{id}/messages, DELETE /chat/sessions/{id}
        ├── schemes.py       # GET /schemes, GET /schemes/{code},
        │                    #   GET /schemes/recommendations
        ├── centers.py       # GET /centers/nearby, GET /centers/{id}
        ├── documents.py     # GET /schemes/{code}/documents,
        │                    #   POST /documents/ocr (future upload)
        └── translation.py   # POST /translate (bulk, cache-backed)
```

## Naming & response conventions

- **Resources are nouns, plural**; actions are either REST sub-resources or a
  single verb path (e.g. `GET /schemes/recommendations`).
- **Pagination** envelope: `{ items, page, pageSize, total }` — matches
  `Paginated<T>` in `shared`.
- **Error envelope** (every non-2xx):
  ```json
  { "error": { "code": "SCHEME_NOT_FOUND", "message": "…", "details": {}, "requestId": "…" } }
  ```
- **Versioning** via URL prefix `/api/v1`. When v2 arrives, `v2/` mirrors the
  structure; `v1` stays frozen for a deprecation window.

## Authentication model (future prompt wiring)

- All `/api/v1` routes except `health.py` verify a Firebase ID token (Bearer) via
  `dependencies.get_current_user`.
- **Anonymous users** (common for a public chatbot) get a signed guest token to
  enable sessions without login; profiles stay minimal until consent.
- Role guards: `citizen` (default), `admin`, `content-editor` via Firebase
  custom claims.

## Provider selection in dependencies

Routers ask dependencies for providers, never instantiate implementations:

```python
async def get_llm_provider(request, config=Depends(get_settings)) -> LlmProvider:
    return resolve_provider(config.ai_provider)   # "gemini" | "mock"
```

This is how tests stub AI/translation without changing routers.

## OpenAPI

- FastAPI auto-generates `openapi.json` at `/docs`.
- `shared/schemas/*.schema.json` are the canonical contracts; a contract test in a
  later prompt diffs the generated OpenAPI against them to catch drift.
