# 09 — State Management Strategy

**Two stores, no more:** TanStack Query v5 for **server state**, Zustand for
**client/UI state**. No Redux; no global "everything store".

## Server state → TanStack Query v5

| Domain      | Query keys                            | Cache strategy            |
| ----------- | ------------------------------------- | ------------------------- |
| Schemes     | `["schemes", {category, state, page}]`| `staleTime: 10min` (catalog) |
| Scheme      | `["schemes", code]`                   | `staleTime: 10min`        |
| Centers     | `["centers", {lat, lng, radius}]`     | `staleTime: 2min`, cache-bust on geolocation change |
| Messages    | `["chat", sessionId, "messages"]`     | Optimistic + refetch      |
| Sessions    | `["chat", "sessions"]`                | `staleTime: 1min`         |
| Profile     | `["profile"]`                         | `staleTime: 5min`         |
| Languages   | `["languages"]`                       | `staleTime: 1d` (static)  |

- Mutations: `useMutation` + `queryClient.invalidateQueries`. Chat send uses
  optimistic update with rollback on failure.
- Retry policy: `retry: 2` with exponential backoff; `retry: 0` for 4xx.
- `staleTime` mirrors data volatility — scheme catalog is stable, nearby centers
  are not.

## Client state → Zustand slices

```
store/
├── index.ts          # combined store (useStore = create(...))
├── chatSlice.ts      # draftInput, isRecording, streamingText, activeSessionId,
│                     #   pendingQuickReply, optimistic message list
├── uiSlice.ts        # theme, sidebar/mobile nav, toasts (or Sonner), loading flags
└── settingsSlice.ts  # language (persisted), voiceEnabled, textOnly,
                      #   highContrast, consent flags, profile fields draft
```

**Persistence:** only `settingsSlice` persists (`zustand/middleware.persist` →
`localStorage`), because it holds language/voice/accessibility preferences that
must survive reload. Nothing else is persisted client-side (session + message
history is server-owned).

## Where each concern lives (decision table)

| Concern                        | Owner                         |
| ------------------------------ | ----------------------------- |
| API data, caching, retries     | TanStack Query                |
| Optimistic mutations           | TanStack Query (+ chatSlice for transient state) |
| UI flags, modals, theme, toasts| Zustand `uiSlice`             |
| Chat draft/streaming cursor    | Zustand `chatSlice`           |
| Language, voice, a11y prefs    | Zustand `settingsSlice` + persist |
| Server-derived refetch triggers| Query keys (no duplication)   |

## Rules

1. **Never duplicate server data in Zustand.** If it comes from the API, it lives
   in a query. Zustand holds only ephemeral UI state.
2. **Selectors over whole-store subscription** — subscribe to slices to avoid
   re-rendering the app on every keystroke.
3. **One-way flow** — mutations write through TanStack; components read via hooks.
4. Auth state (Firebase) lives in `AuthProvider` context (not Zustand), fed to
   query keys for the authed/guest distinction.
