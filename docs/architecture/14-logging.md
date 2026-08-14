# 14 — Logging Architecture

## Goal

Structured, correlatable, low-noise logs. Human-friendly during development,
JSON + machine-parseable in production, and always tied to a `requestId`.

## Server (structlog)

### Format by environment

| Env | Output |
| --- | ------ |
| `development` | Pretty console with colors, human-readable timestamps |
| `staging` / `production` | Single-line JSON per event, `zstandard`-compressed when file-backed |

### Mandatory fields on every event

```
timestamp, level, logger, event, requestId, service=scheme-sathi-server,
method, path, status, duration_ms, user_id (if authed), language
```

### Correlation

- A `RequestIDMiddleware` assigns `X-Request-Id` (or reuses the client's) at
  request start, binds it to the structlog context, and echoes it in the response
  header + error envelope.
- Client sends `X-Request-Id` on retries → a whole user journey is traceable.

### What to log (and what NOT to)

| Log | Detail |
| --- | ------ |
| Access | method, path, status, duration, requestId — no payloads |
| AI calls | provider, model, latency, token usage, cache hit/miss — **no prompt content in prod** (cost + PII) |
| Translation | src/tgt langs, latency, provider used, fallback flag |
| DB slow query | query + duration when > threshold |
| Rate limiting | uid/ip hash, bucket, limit |
| Errors | stack (dev), error code, requestId |
| **Never** | **speech transcripts, full user messages, Aadhaar-like identifiers, raw Firebases tokens** |

Redaction pipeline strips PAN/Aadhaar-like patterns and any value under a
`SENSITIVE` marker before emitting.

### Instrumentation

- `prometheus-client` exposes `/metrics` (latency histograms, error rates, AI
  token usage, translation hit-rate).
- `sentry` for 5xx + exceptions; `OTEL_EXPORTER_OTLP_ENDPOINT` reserved for
  distributed tracing later.

## Client

- Structured console logging via a tiny `lib/logger.ts` (level-gated, JSON in
  prod, no-op in tests).
- **Never log voice transcripts or chat content by default** — only
  session/request metadata and `requestId`.
- Frontend errors are also sent to Sentry with `requestId` attached.

## Alerting (future)

- 5xx rate spike, P95 latency breach, AI error-rate threshold, translation
  fallback rate > X%, rate-limit 429 spikes. Dashboards per service.
