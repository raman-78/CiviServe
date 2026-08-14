# CiviServe — Frontend

React 19 + TypeScript + Vite + Tailwind CSS + shadcn/ui client for the
**Multilingual Citizen Service Chatbot for Government Schemes** (HackElite 2026).

## Tech stack

| Concern            | Choice                                    | Notes                                   |
| ------------------ | ----------------------------------------- | --------------------------------------- |
| Framework          | React 19 + TypeScript                     | Strict TS, `verbatimModuleSyntax`       |
| Build tool         | Vite 6                                    | Proxy `/api` → backend in dev           |
| Styling            | Tailwind CSS 3.4 + shadcn/ui              | `components.json` configured             |
| Animation          | Framer Motion                             | Guided, accessible animation only        |
| Routing            | React Router 7                            | Lazy routes + route guards               |
| Server state       | TanStack Query v5                         | Cache, retries, mutation helpers         |
| Client state       | Zustand                                   | Chat + UI slices only                    |
| i18n               | i18next + react-i18next                   | Indic language resources                 |
| Speech (STT/TTS)   | Browser Web Speech (MVP)                  | Adapter interface → cloud later          |
| OCR                | tesseract.js                              | Adapter interface → PaddleOCR later      |
| Maps               | Leaflet + OpenStreetMap (MVP)             | Google Maps adapter swappable            |
| Testing            | Vitest + Testing Library + Storybook      | Unit + component + visual                |

## Folder structure

```
client/
├── public/                      # Static assets (favicon, manifests, scheme logos)
└── src/
    ├── main.tsx                 # Entry point — mounts <App />
    ├── vite-env.d.ts            # Typed import.meta.env
    ├── app/                     # App root: <App/>, <Providers/>, ErrorBoundary
    ├── components/
    │   ├── ui/                  # shadcn/ui primitives (button, dialog, card, …)
    │   ├── layout/              # AppLayout, Header, NavBar, Footer, LanguageSwitcher
    │   ├── shared/              # Cross-cutting: LoadingState, ErrorState, VoiceToggle, ...
    │   ├── chat/                # ChatWindow, MessageList, MessageBubble, ChatInput, QuickActions
    │   ├── schemes/             # SchemeCard, SchemeGrid, SchemeDetail, EligibilityView
    │   ├── centers/             # CenterMap, CenterCard, CenterList
    │   ├── documents/           # DocumentUpload, OcrPreview, DocumentChecklist
    │   └── profile/             # ProfileForm, ConsentBanner, LanguagePreference
    ├── features/                # Feature modules (feature-sliced):
    │   ├── chat/                #   chat orchestration, intent→component mapping
    │   ├── schemes/             #   scheme queries + filters
    │   ├── centers/             #   geolocation + nearby centers
    │   ├── auth/                #   Firebase auth hooks + guards
    │   └── i18n/                #   language provider + preferences
    ├── hooks/                   # Shared hooks (useLocalStorage, useMediaQuery, useVoice)
    ├── lib/                     # api client, utils (cn), formatters, errors
    ├── services/                # SPEECH / TRANSLATION / OCR ADAPTERS (see below)
    │   ├── stt/                 #   SpeechRecognitionAdapter interface + BrowserAdapter
    │   ├── tts/                 #   SpeechSynthesisAdapter interface + BrowserAdapter
    │   ├── translation/         #   TranslationProvider (IndicTrans2 via server, Google fallback)
    │   ├── ocr/                 #   OcrAdapter interface + TesseractAdapter
    │   └── api/                 #   typed HTTP client wrapping fetch + TanStack Query
    ├── store/                   # Zustand stores (chatSlice, uiSlice, settingsSlice)
    ├── router/                  # route table, guards, lazy loading config
    ├── pages/                   # Route-level pages (Chat, Schemes, Centers, Profile, …)
    ├── i18n/                    # i18next init + locales/{en,hi,ta,...}.json
    ├── types/                   # Local types + re-exports of @schemesathi/shared
    ├── config/                  # env access, feature flags, constants
    ├── styles/                  # globals.css (Tailwind + shadcn theme tokens)
    └── test/                    # test setup + shared render helpers
```

## Adapter architecture (the key extensibility point)

Every external capability behind an interface so the MVP browser implementation
can be swapped without touching feature code:

```
SpeechToTextAdapter { start(), stop(), onResult, onError, supported() }
TextToSpeechAdapter { speak(text, lang), stop(), cancel(), supported() }
TranslationAdapter  { translate(text, from, to) -> Promise<string> }
OcrAdapter          { recognize(image) -> Promise<OcrResult> }
MapProvider         { render(container, opts), locate(...) }
```

- `services/stt/BrowserSpeechAdapter.ts` implements `SpeechToTextAdapter` using the Web
  Speech API. Swap in a `GoogleSpeechAdapter`/`AzureSpeechAdapter` later.
- The chat feature depends on the interface **only** — this is the replacement point
  promised by the MVP architecture.

## Commands

```bash
pnpm install              # from repo root (workspaces)
pnpm --filter @schemesathi/client dev      # dev server on :5173
pnpm --filter @schemesathi/client build    # typecheck + production build
pnpm --filter @schemesathi/client test     # Vitest
pnpm --filter @schemesathi/client storybook
```

## Conventions

- **Feature-sliced** layout inside `src/features/*` — each feature owns its UI,
  queries, and hooks. Shared code lives in `src/components/shared` + `src/hooks`.
- Components use shadcn/ui primitives; new UI primitives are added via the CLI
  (`pnpm dlx shadcn@latest add <component>`).
- All user-facing copy goes through i18n keys; no hard-coded strings in components.
- Server state lives in TanStack Query; local UI state in Zustand (see
  `docs/architecture/09-state-management.md`).
