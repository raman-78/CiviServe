# 02 — Frontend Architecture

## Overview

Single-page application, **feature-sliced by domain** (chat, schemes, centers,
documents, auth, i18n). React 19, TypeScript strict, Vite 6, Tailwind 3.4 +
shadcn/ui, React Router 7, TanStack Query v5 (server state), Zustand (client
state), i18next (translations), Framer Motion (animation).

```
┌──────────────────────────────────────────────────────────┐
│  App (root)                                               │
│  ├─ <Providers/>   QueryClient · Auth · Theme · I18n     │
│  ├─ <ErrorBoundary/>  (root fallback)                    │
│  └─ <AppRouter>     lazy routes + guards                 │
│      └─ <AppLayout>  Header( LangSwitcher, VoiceToggle ) │
│          └─ <Outlet/> → Pages → Feature components        │
└──────────────────────────────────────────────────────────┘
```

## Design principles

1. **Feature-sliced, not folder-typed.** A feature owns its UI, hooks, and queries
   under `src/features/<feature>/`. Cross-feature pieces go to
   `src/components/shared` / `src/hooks`. This keeps chat, schemes, and centers
   independently changeable — critical when later prompts grow each feature.
2. **Unidirectional data flow.** Page → feature components → hooks → TanStack
   Query / Zustand. No component reaches into another's internals.
3. **Adapters isolate browsers APIs.** STT/TTS/translation/OCR/maps are interfaces
   in `src/services/*` with a concrete browser implementation. Feature code
   imports the interface only (see client README). This is the replacement point
   promised by the MVP architecture.
4. **Every string is an i18n key.** No hard-coded UI copy → multilingual is a
   resource-file problem, not a code problem.
5. **Accessibility + low-bandwidth first.** The citizen audience may use
   low-end devices / slow networks: code-split aggressively, lazy-load routes,
   prefer text-first UI, support high-contrast and larger fonts, and provide
   text-only mode (no auto-TTS).

## Module map

| Module | Responsibility |
| ------ | -------------- |
| `app/` | Bootstrap, provider composition, root error boundary |
| `router/` | Route table, guards, lazy config (doc 08) |
| `pages/` | One component per route; composes features |
| `features/chat` | Chat orchestration, intent → component mapping, streaming text |
| `features/schemes` | Catalog, filters, scheme detail, eligibility rendering |
| `features/centers` | Geolocation, nearby list + map |
| `features/auth` | Firebase sign-in, token refresh, guards |
| `features/i18n` | Language provider, preference persistence |
| `services/` | STT/TTS/translation/OCR/maps adapters + API client |
| `store/` | Zustand slices (chat, ui, settings) |
| `lib/` | `cn()`, formatters, error normalization, typed API helpers |
| `config/` | Env access + feature flags (typed) |
| `hooks/` | Shared hooks (`useSpeechRecognition`, `useGeolocation`, …) |

## Data fetching

- TanStack Query v5 owns **server state**: schemes, centers, sessions/messages,
  profile. Keys are `feature + id`.
- Cache invalidation on mutations (`invalidateQueries(["schemes"])`).
- Retries with exponential backoff for flaky networks; `staleTime` tuned per
  resource (scheme catalog long, nearby centers short).
- Optimistic updates only where the UI must feel instant (chat send).

## Performance budget

- Route-level code splitting (`React.lazy`) — chat engine + Tesseract are heavy and
  load on demand.
- Manual chunks in `vite.config.ts` (react, query, speech, maps).
- Virtualized long chat lists and center lists (future) — defer heavy lists.
- Font subsetting for Indic scripts; system font stack fallback.

## Testing strategy

- Vitest + Testing Library: unit for services/utils, RTL for components,
  Storybook for the component library, MSW for API mocking. (Setup in later prompt.)
