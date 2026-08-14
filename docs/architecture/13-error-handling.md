# 13 — Error Handling Architecture

## Contract: the error envelope

Every non-2xx response, from both client and server, is normalized into:

```json
{
  "error": {
    "code": "SCHEME_NOT_FOUND",
    "message": "No scheme found for code PM-KISAN",
    "details": {},
    "requestId": "a1b2c3d4"
  }
}
```

- `code` — machine-readable, namespaced (`CHAT_`, `SCHEME_`, `AUTH_`,
  `TRANSLATION_`, `AI_`, `GEO_`, `RATE_LIMIT_`, `VALIDATION_`).
- `message` — safe for end users (no stack traces, no internals), already
  **translatable**: the client looks up a localized string by `code`.
- `requestId` — correlation across client ↔ server ↔ logs (doc 14).
- `details` — field-level errors for forms (e.g. profile validation).

## Server-side

### Exception hierarchy (`core/errors.py`)

```
AppError (base)
├── NotFoundError           → 404
├── ValidationError         → 422 (Pydantic pre-validates)
├── ConflictError           → 409
├── AuthenticationError     → 401
├── ForbiddenError          → 403
├── RateLimitError          → 429 (+ Retry-After header)
├── ExternalServiceError    → 502/503 (AI, translation, geo down)
└── InternalError           → 500 (unexpected)
```

- **One global exception handler** (FastAPI `exception_handler`) converts
  `AppError` → envelope; pydantic `RequestValidationError` → `VALIDATION_*`;
  unknown exceptions → `500` + Sentry + `requestId`.
- Services **raise domain errors**, never HTTP statuses. Mapping to HTTP happens
  only in the handler — keeps layering clean.

### Resilience for external providers

- **Retries:** `tenacity` (exponential + jitter) for Gemini/translation/geo, on
  transient errors (5xx, timeout), NOT on 4xx.
- **Timeouts:** every outbound call has a timeout from config
  (`GEMINI_TIMEOUT_SECONDS`, etc.).
- **Circuit breaker** (planned, Redis-backed): after N consecutive provider
  failures, fail fast for a window instead of hammering a dead service.
- **Fallbacks:** translation `IndicTrans2` → Google → return source text with a
  `TRANSLATION_FALLBACK` warning message. STT/TTS on the client degrade to
  text-only mode with an explanatory chip.
- **Graceful degradation:** if Gemini is down, chat still answers from the local
  scheme catalog (rule-based eligibility) — never a hard 500 for the citizen.

## Client-side

### Layers

1. **Fetch wrapper** (`lib/api.ts`) — throws typed `ApiError` (parses envelope).
2. **TanStack Query** — `onError` at the query/mutation; `retry` policy
   (network only). 4xx → no retry; 5xx/timeout → retry with backoff.
3. **Route-level error boundaries** (`router/errorElement.tsx`) — catch render
   crashes; show `ErrorState` with Reload + Home.
4. **Root `ErrorBoundary`** — last resort, user-friendly full-page fallback.
5. **Toast system** — transient errors (rate limit, network) via toast, not full
   screens.

### Error → user copy

- `client/src/i18n/locales/*/errors.json` maps `error.code` → localized string.
- Guidance chips: rate-limited → "please wait a moment"; AI down →
  "I'll answer from the offline catalog for now".

## Monitoring hooks

- Every envelope includes `requestId`; the client surfaces it on the
  "Report problem" dialog so support can trace the exact request.
- `sentry` captures server 5xx + client render errors automatically.
