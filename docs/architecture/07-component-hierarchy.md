# 07 — Component Hierarchy

Feature-sliced component tree. Nodes are grouped by ownership; **no arrow crosses
feature boundaries** (shared primitives are the only exception).

```
App
├── Providers                     (QueryClient, AuthProvider, ThemeProvider,
│                                  I18nProvider, ToastProvider)
└── RootErrorBoundary
    └── AppRouter                 (lazy routes + guards)
        ├── PublicLayout  ─── LandingPage, NotFoundPage
        ├── AuthLayout   ─── LoginPage, RegisterPage
        └── AppLayout            (requires auth-or-guest)
            ├── Header
            │   ├── LanguageSwitcher     ← global language
            │   ├── VoiceToggle           (enables/disables TTS replies)
            │   └── UserMenu
            ├── NavBar                    (Chat · Schemes · Centers · Documents · Profile)
            ├── Footer
            └── <Outlet>
                ├── ChatPage
                │   └── ChatWindow
                │       ├── SessionHeader        (language, clear/resume)
                │       ├── MessageList          (virtualized)
                │       │   └── MessageBubble
                │       │       ├── TextBubble
                │       │       ├── SchemeCard
                │       │       ├── SchemeListCard
                │       │       ├── EligibilityResultCard
                │       │       ├── DocumentListCard
                │       │       ├── CenterListCard
                │       │       ├── ApplicationLinkCard
                │       │       └── QuickReplies
                │       └── ChatInput
                │           ├── VoiceButton       (uses STT adapter)
                │           └── TextArea + MicStatusIndicator
                ├── SchemesPage
                │   ├── SchemeFilters         (category · state · search)
                │   └── SchemeGrid
                │       └── SchemeCard
                ├── SchemeDetailPage
                │   ├── SchemeHeader
                │   ├── EligibilityView        (rule-by-rule against profile)
                │   ├── DocumentsView          (+ "Upload & OCR" action)
                │   └── ApplicationLinksView
                ├── CentersPage
                │   ├── LocationBanner         (consent for geolocation)
                │   ├── CenterMap              (Leaflet adapter)
                │   └── CenterList
                │       └── CenterCard
                ├── DocumentsPage
                │   ├── DocumentUpload         (tesseract adapter)
                │   └── OcrPreview
                ├── ProfilePage
                │   ├── ProfileForm            (feeds recommendation engine)
                │   ├── ConsentBanner
                │   └── LanguagePreference
                └── SettingsPage
                    ├── AccessibilitySettings
                    └── PrivacySettings
```

## Shared primitives (`components/shared` + `components/ui`)

- `ui/*` — generated shadcn primitives (button, card, dialog, sheet, select,
  toast, tooltip, …). Never customized inline; extend via variants.
- `shared/ErrorState`, `shared/LoadingState`, `shared/EmptyState` — consistent
  async-UI fallbacks.
- `shared/VoiceToggle` — TTS on/off.
- `shared/MicButton` — STT on/off with permission states (idle/denied/recording).
- `shared/LanguageSwitcher` — dropdown, persists preference.

## Composition rules

1. **Pages compose features; features never import pages.**
2. Chat message rendering uses a **content-type → component registry**
   (`features/chat/messageRegistry.ts`): adding a new rich card type is one
   registration, not a chain of conditionals.
3. Feature components receive **props or hooks**, never sibling component refs.
4. All shared async states use `ErrorState`/`LoadingState` so error handling is
   uniform (doc 13).

## Data flow example (Chat)

`ChatInput` → `useSendMessage` (feature hook) → `services/api` (TanStack mutation)
→ server → streaming updates via `store/chatSlice` (Zustand) → `MessageList`
re-renders. STT output flows `MicButton` → `SpeechToTextAdapter` → `ChatInput`.
