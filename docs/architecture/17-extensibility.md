# 17 — Future Extensibility

How the Prompt-1 foundation is engineered so every later prompt (and future
channels/states) slots in **without rework**. Each swap point is an interface,
not a hardcoded call.

## Swap points (interface → implementation)

| Capability | Interface (now) | MVP impl (later prompt) | Replaceable by |
| ---------- | --------------- | ----------------------- | -------------- |
| LLM | `LlmProvider` (`services/ai/provider.py`) | `GeminiProvider` | Claude/OpenAI/Llama self-host |
| Translation | `TranslationProvider` | `IndicTrans2Client` → `GoogleTranslateClient` | any MT engine |
| Speech-to-Text | `SpeechToTextAdapter` (`client/src/services/stt`) | `BrowserSpeechAdapter` | Google/Azure cloud STT |
| Text-to-Speech | `TextToSpeechAdapter` (`client/src/services/tts`) | `BrowserSynthesisAdapter` | Google/Azure cloud TTS |
| OCR | `OcrAdapter` (`client/src/services/ocr`) | `TesseractAdapter` (browser) | `PaddleOcrClient` (server) |
| Maps | `MapProvider` (`client/src/services/maps`) | `Leaflet/OSM` | Google Maps |
| Geo backend | `GeoProvider` (`services/geo/provider.py`) | OpenStreetMap client | Google Maps API |
| Auth | Firebase | — | OIDC providers (same verify slot) |

**Rule:** features depend on the *interface*. Replacing an engine is a new class +
a config value — zero changes in chat/scheme/center features.

## New languages

1. Add `i18n/locales/<code>.json` + UI resources.
2. Append `SUPPORTED_LANGUAGES` entry (`shared/src/domain/language.ts`).
3. Set capability flags (`stt/tts/indicTrans`); server translation handles the
   rest via the provider + fallback. Done — no code paths change.

## New states & schemes (all 28 states)

- `schemes.state_code` (or `central`) + `seeds/states/*` fixtures → catalog is
  **data-driven, not coded**. Adding Karnataka = new seed files + verification.
- Scheme content pipeline: `content-editor` role + verification workflow
  (`lastVerifiedAt`), which the AI cites.
- Centers: PostGIS bulk ingest from CSC/e-Sevai public data sets.

## New channels (WhatsApp / IVR / Telegram)

- The backend is **channel-agnostic**: routers → services already separate HTTP
  from logic. A channel adapter translates channel events → the same service
  calls; message responses render per-channel (chat UI today, templates tomorrow).
- Add a `channel` field to sessions; store render strategy in the registry.

## Retrieval-augmented answers (RAG)

- `pgvector` extension is enabled from migration 0001 → embeddings of scheme docs
  land in the same Postgres. `LlmProvider` gains a `retrieve()` hook so grounding
  upgrades without changing the chat pipeline.

## New AI features

- Recommendation engine is a **declarative rule evaluator** over
  `EligibilityRule` (`services/recommendation/`) — adding a rule type = a new
  operator implementation, not a rewrite.
- Sentiment/intent classifiers plug into the same intent registry.

## Team/code growth

- Feature-sliced frontend + layered backend keep feature teams isolated.
- ADRs capture irreversible choices (doc index → `docs/decisions`).

## What stays fixed

- `shared/src/domain/*.ts` = the contract (may grow, never silently rename).
- Layering rules + provider interfaces (docs 03/02).
- The error envelope, logging schema, and env-driven config.
