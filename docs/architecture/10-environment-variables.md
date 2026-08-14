# 10 — Environment Variables

## Principles

- **All config via environment** (12-factor). No hard-coded URLs, keys, or feature
  flags in code.
- Commit **only `.env.example`** files. Real values live in local `.env.local`
  (client) / `server/.env` (server) and in deploy-platform secrets.
- Client vars are prefixed `VITE_` (exposed to the browser bundle); server vars are
  plain uppercase.
- **Browser = untrusted.** Keys that must never reach the client (Gemini, Google
  translate, Firebase admin, DB) exist **only** on the server.

## Client — `client/.env.example`

| Variable | Example | Purpose |
| -------- | ------- | ------- |
| `VITE_API_BASE_URL` | `https://api.schemesathi.in` | Backend base URL (empty in dev → Vite proxy `/api`) |
| `VITE_FIREBASE_API_KEY` | `AIza…` | Firebase web SDK (public by design) |
| `VITE_FIREBASE_AUTH_DOMAIN` | `schemesathi.firebaseapp.com` | Firebase auth domain |
| `VITE_FIREBASE_PROJECT_ID` | `schemesathi` | Firebase project |
| `VITE_FIREBASE_STORAGE_BUCKET` | `schemesathi.appspot.com` | Firebase storage |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | `1234…` | Firebase messaging |
| `VITE_FIREBASE_APP_ID` | `1:…:web:…` | Firebase app id |
| `VITE_MAPS_PROVIDER` | `osm` \| `google` | Map provider switch (adapter) |
| `VITE_MAPS_API_KEY` | (google only) | Google Maps key if chosen |
| `VITE_STT_ENGINE` | `browser` \| `google` \| `azure` | STT adapter selector |
| `VITE_TTS_ENGINE` | `browser` \| `google` \| `azure` | TTS adapter selector |
| `VITE_TRANSLATION_FALLBACK_ENABLED` | `true` | Enable server-side Google translate fallback |
| `VITE_OCR_ENGINE` | `tesseract` \| `paddle` | OCR adapter selector |
| `VITE_GEOLOCATION_ENABLED` | `true` | Allow requesting location |
| `VITE_APP_ENV` | `development` \| `staging` \| `production` | Build context |
| `VITE_APP_VERSION` | `0.1.0` | Build stamp |

## Server — `server/.env.example`

| Variable | Purpose |
| -------- | ------- |
| `ENV`, `DEBUG`, `APP_NAME`, `VERSION`, `LOG_LEVEL` | App/runtime meta |
| `CORS_ORIGINS` | JSON array of allowed origins |
| `DATABASE_URL` | `postgresql+asyncpg://…` (Neon) |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE` | Pool tuning |
| `REDIS_URL` | Cache + rate-limit + queue |
| `FIREBASE_PROJECT_ID`, `FIREBASE_SERVICE_ACCOUNT_PATH` \| `…_JSON` | Server-side auth verify |
| `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_TEMPERATURE`, `GEMINI_MAX_OUTPUT_TOKENS`, `GEMINI_TIMEOUT_SECONDS` | AI provider |
| `GEMINI_CACHE_ENABLED`, `GEMINI_CACHE_TTL_SECONDS` | AI response cache |
| `INDICTRANS_ENABLED`, `INDICTRANS_ENDPOINT`, `INDICTRANS_MODEL_DIR` | Primary translation |
| `GOOGLE_TRANSLATE_API_KEY`, `TRANSLATION_CACHE_TTL_SECONDS` | Fallback translation |
| `GOOGLE_SPEECH_LANGUAGE_HINT` | Future cloud STT default |
| `PADDLEOCR_ENDPOINT` | Future server OCR |
| `GCS_BUCKET` | Future media/audio storage |
| `SENTRY_DSN`, `OTEL_EXPORTER_OTLP_ENDPOINT` | Observability |
| `RATE_LIMIT_*`, `AI_ENDPOINT_RATE_LIMIT_MAX_PER_MINUTE` | Abuse control |
| `NO_AI_PATH_PREFIXES` | Paths that skip AI (/healthz,/metrics) |

## Env lifecycle

- **Local:** copy `.env.example` → `.env.local` / `server/.env`, fill dev values.
- **CI:** secrets injected by GitHub; `.env` absent, code must not require files.
- **Vercel/Railway/Neon:** set via platform dashboards; `VITE_*` baked at build,
  server vars read at runtime. Config always validated at boot by
  `core/config.py` (pydantic-settings) and by zod in the client — fail fast with a
  clear message rather than crashing mid-request.
