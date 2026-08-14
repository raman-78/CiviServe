# 12 — Dependency List

Rationale for every third-party dependency. Pinned ranges live in
`client/package.json`, `server/pyproject.toml`, `server/requirements.txt`.

## Frontend — runtime

| Package | Why |
| ------- | --- |
| `react`, `react-dom` ^19 | Required by spec; concurrent features + strict TS |
| `react-router-dom` ^7 | Declarative nested routes, guards, lazy loading (doc 08) |
| `@tanstack/react-query` ^5 | Server-state cache, retries, mutations (doc 09) |
| `zustand` ^5 | Minimal client state, persist middleware |
| `framer-motion` ^11 | Guided UI animation; respect `prefers-reduced-motion` |
| `tailwindcss` ^3.4, `tailwindcss-animate` | Styling + shadcn animations |
| `class-variance-authority`, `clsx`, `tailwind-merge` | shadcn/ui `cn()` + variants |
| `@radix-ui/*` (dialog, select, slot, toast, …) | Accessible primitives backing shadcn/ui |
| `sonner` | Toast/notification system (used by the error-handling layer) |
| `lucide-react` | Icons |
| `@fontsource-variable/inter`, `@fontsource-variable/noto-sans-devanagari` | UI + Indic-script typography (subsetted, self-hosted) |
| `@schemesathi/shared` (workspace) | Canonical domain types |
| `firebase` ^10 | Client auth SDK (also future push/storage) |
| `i18next`, `react-i18next` ^15/^24 | Multilingual UI resources |
| `leaflet`, `react-leaflet` ^5 | OSM map MVP behind MapProvider adapter |
| `tesseract.js` ^5 | Browser OCR behind OcrAdapter |
| `date-fns` ^4 | Locale-aware date formatting |
| `zod` ^3 | Runtime validation of env + payloads |

## Frontend — dev

| Package | Why |
| ------- | --- |
| `vite` ^5, `@vitejs/plugin-react` | Build tooling |
| `typescript` ^5.6 | Strict typing |
| `eslint` ^9 + `typescript-eslint` + `eslint-plugin-react-hooks`/`react-refresh` | Lint |
| `prettier`, `prettier-plugin-tailwindcss` | Format |
| `vitest` ^2, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom` | Unit/component tests |
| `storybook` ^8 | Component library workspace |
| `@types/react`, `@types/react-dom`, `@types/node`, `@types/leaflet` | Types |

## Backend — runtime

| Package | Why |
| ------- | --- |
| `fastapi` >=0.115 | Async web framework, OpenAPI auto-docs |
| `uvicorn[standard]` | ASGI server |
| `pydantic` ^2, `pydantic-settings` | Schema validation + env config |
| `sqlalchemy` ^2 (async), `psycopg[binary]` / `asyncpg` | ORM + PostgreSQL drivers |
| `alembic` | DB migrations (in `database/`) |
| `orjson` | Fast JSON serialization |
| `httpx` | Async outbound calls (AI, translation, geo) |
| `python-multipart` | Uploads (OCR, voice) |
| `tenacity` | Retry with backoff for flaky providers |
| `firebase-admin` | Verify Firebase ID tokens server-side |
| `google-genai` | Gemini LLM provider |
| `google-cloud-translate` | Translation fallback (Google) |
| `google-cloud-speech`, `google-cloud-texttospeech` | Future cloud STT/TTS |
| `google-cloud-storage` | Future audio/OCR blob storage |
| `redis` | Cache + rate limiting + task queue broker |
| `structlog` | Structured JSON logging (doc 14) |
| `prometheus-client` | /metrics scraping |
| `sentry-sdk[fastapi]` | Error reporting (optional) |
| `zstandard` | Log/response compression |

## Backend — dev

`pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`, `types-psycopg`.

## Versioning & supply-chain policy

- Ranges are conservative; **lockfiles** (`pnpm-lock.yaml`, `pip freeze`) pin
  exact builds for reproducibility.
- `dependabot` enabled for JS + Python → keeps CVEs patched.
- Review new deps against: license, maintenance, bundle size (client), native
  wheels (server), and whether the adapter layer could replace it.
