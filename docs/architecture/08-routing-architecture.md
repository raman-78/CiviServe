# 08 — Routing Architecture

React Router v7, **lazy-loaded routes** with nested layouts and route guards.
All route config lives in `client/src/router/` (declarative table → routes).

```
/                      PublicLayout → LandingPage
/login                 PublicLayout → LoginPage
/register              PublicLayout → RegisterPage
/chat                  AppLayout   → ChatPage            (default after auth)
/chat/:sessionId       AppLayout   → ChatPage            (resume conversation)
/schemes               AppLayout   → SchemesPage
/schemes/:code         AppLayout   → SchemeDetailPage
/centers               AppLayout   → CentersPage
/documents             AppLayout   → DocumentsPage
/profile               AppLayout   → ProfilePage
/settings              AppLayout   → SettingsPage
/help                  AppLayout   → HelpPage
*                      → NotFoundPage (within current layout)
```

## Layout nesting

```
AppRouter
├── PublicLayout   (landing/auth: no chrome, brand-focused)
├── AuthLayout     (login/register: centered card)
└── AppLayout      (Header + NavBar + Footer + <Outlet/>)   ← guard: authed or guest
```

## Guards (`router/guards.ts`)

| Guard        | Behavior |
| ------------ | -------- |
| `requireAuth` | Redirect `/login` if no Firebase user. |
| `allowGuest`  | Anonymous users proceed with a guest token (chat is usable pre-login). |
| `requireProfile` | Ask the user to complete profile before *eligibility* screens if missing. |
| `roleAdmin`   | Future: content/admin areas. |

## Lazy loading & code splitting

```ts
// router/routes.tsx (shape)
const ChatPage = lazy(() => import("@/pages/ChatPage"));
const SchemeDetailPage = lazy(() => import("@/pages/SchemeDetailPage"));
```
- Each route is a chunk; heavy deps (Tesseract, Leaflet) are isolated further by
  the `manualChunks` in `vite.config.ts`.
- `<Suspense fallback={<LoadingState/>}>` wraps the routed `<Outlet/>`.

## State restoration & deep links

- Language + voice prefs are persisted (doc 09) and rehydrated before first route.
- `?lang=ta` query parameter overrides UI language for shareable deep links.
- Chat deep links (`/chat/:sessionId`) restore history from the server.
- Scroll restoration via `ScrollRestoration` on AppLayout.

## Error handling in routes

- `router/errorElement.tsx` — route-level `ErrorBoundary` showing
  `ErrorState` with a "Reload" action and a "Back home" link.
- A 404 returns `NotFoundPage` (HTTP-equivalent client nav), not a blank screen.
