# 01 — Complete Project Folder Structure

> Prompt 1 of 15. Deliverable: folder layout + configs. No feature code yet.

```
chatbot/
├── .github/
│   └── workflows/
│       ├── ci.yml                  # PR gate: typecheck/lint/test/build (JS + Python)
│       ├── deploy-client.yml       # Vercel deploy on main
│       └── deploy-server.yml       # Railway deploy on main
├── .gitignore
├── .editorconfig
├── .nvmrc                         # Node 20.19
├── .prettierrc.mjs
├── AGENTS.md                      # Agent/orchestrator guide (opencode)
├── CONTRIBUTING.md                # Workflow + checklist (summary of docs 18/19)
├── README.md                      # Project entry point
├── package.json                   # Root workspace + orchestrator scripts
├── pnpm-workspace.yaml            # packages: client, shared
├── .prettierignore                # prettier ignores (dist, coverage, venv, lockfiles)
│
├── scripts/                       # Reusable dev/ops scripts (bootstrap, migrate,
│   │                              #   seed, codegen, ci-verify) — see scripts/README.md
│   └── README.md
│
├── assets/                        # Brand + presentation media (no user data)
│   ├── brand/                     #   logos, favicon, fonts, palette
│   └── media/                     #   screenshots, demo videos
│
├── client/                        # React 19 SPA  (@schemesathi/client)
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── components.json            # shadcn/ui
│   ├── eslint.config.js
│   ├── .env.example
│   ├── public/
│   └── src/
│       ├── main.tsx               # entry (later prompt)
│       ├── vite-env.d.ts
│       ├── app/                   # <App/>, <Providers/>, ErrorBoundary
│       ├── components/
│       │   ├── ui/                #   shadcn primitives (button, card, dialog, …)
│       │   ├── layout/            #   AppLayout, Header, NavBar, Footer, LanguageSwitcher
│       │   ├── shared/            #   ErrorState, LoadingState, VoiceToggle, …
│       │   ├── chat/              #   ChatWindow, MessageList, MessageBubble, ChatInput
│       │   ├── schemes/           #   SchemeCard, SchemeGrid, SchemeDetail
│       │   ├── centers/           #   CenterMap, CenterCard, CenterList
│       │   ├── documents/         #   DocumentUpload, OcrPreview, Checklist
│       │   └── profile/           #   ProfileForm, ConsentBanner
│       ├── features/              # feature-sliced modules
│       │   ├── chat/              #   orchestration, intent→component map
│       │   ├── schemes/           #   queries + filters
│       │   ├── centers/           #   geolocation + nearby
│       │   ├── auth/              #   Firebase hooks + guards
│       │   └── i18n/              #   language provider + prefs
│       ├── hooks/                 # shared hooks
│       ├── lib/                   # api client, utils, formatters, errors
│       ├── services/              # ADAPTER INTERFACES (STT/TTS/translation/OCR/maps)
│       │   ├── stt/               #   + BrowserSpeechAdapter
│       │   ├── tts/               #   + BrowserSynthesisAdapter
│       │   ├── translation/       #   client of server translation
│       │   ├── ocr/               #   + TesseractAdapter
│       │   └── api/               #   typed HTTP client
│       ├── store/                 # Zustand: chatSlice, uiSlice, settingsSlice
│       ├── router/                # route table + guards
│       ├── pages/                 # route pages (Chat, Schemes, Centers, Profile, …)
│       ├── i18n/                  # i18next init + locales/{en,hi,ta,…}.json
│       ├── types/                 # local types + re-exports of shared
│       ├── config/                # env access + feature flags
│       ├── styles/                # globals.css (Tailwind + theme tokens)
│       ├── mocks/                 # MSW handlers + fixtures
│       └── test/                  # setup + render helpers
│
├── server/                        # FastAPI  (@ none, pip package)
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── pyproject.toml             # deps + ruff/mypy/pytest config
│   ├── .env.example
│   ├── app/
│   │   ├── main.py                # app factory (later prompt)
│   │   ├── api/v1/
│   │   │   ├── routers/           # chat, schemes, centers, documents, auth, health
│   │   │   └── dependencies.py    # get_db, get_current_user, rate limiters
│   │   ├── core/                  # config, logging, security, errors, rate_limit
│   │   ├── db/                    # base, session, redis
│   │   ├── models/                # SQLAlchemy ORM
│   │   ├── schemas/               # Pydantic contracts
│   │   ├── repositories/          # data-access layer
│   │   ├── services/              # ai/, translation/, speech/, geo/, ocr/, recommendation/
│   │   ├── middleware/            # request-id, CORS, error, prometheus
│   │   └── utils/                 # caching, retries, idgen
│   └── tests/                     # unit/, integration/, fixtures/
│
├── database/                      # DB-owned tooling, independent of server deploy
│   ├── migrations/                # Alembic versions (append-only)
│   ├── seeds/                     # idempotent state/scheme/center fixtures
│   ├── scripts/                   # migrate, seed, backup, reset_local
│   └── README.md
│
└── shared/                        # @schemesathi/shared — canonical contracts
    ├── package.json
    ├── tsconfig.json
    ├── eslint.config.js
    ├── README.md
    ├── schemas/                   # *.schema.json (language-neutral mirrors)
    └── src/
        ├── index.ts
        └── domain/                # user.ts, chat.ts, scheme.ts, centers.ts,
                                   # recommendation.ts, language.ts, common.ts
```

## Structural invariants

1. `shared/src/domain/*.ts` — single source of truth for the API surface.
2. `database/migrations/versions/` — append-only; migrations never edited once merged.
3. `server` is a pip package; `client`+`shared` are pnpm workspaces.
4. No `__init__.py`-less imports across service boundaries; layers documented in doc 03.
5. `.env*` are never committed (`.gitignore` allows only `.env.example`).
