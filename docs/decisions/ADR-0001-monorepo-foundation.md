# ADR-0001 — Monorepo structure

- Status: Accepted
- Date: 2026-08-06 (Prompt 1 of 15)
- Deciders: Architecture team

## Context

HackElite 2026 project: an AI multilingual citizen service chatbot. We must ship
a foundation that supports a React 19 frontend, a FastAPI backend, a PostgreSQL
database, and shared contracts — while keeping the door open for 14 more feature
prompts and multi-state scalability.

## Decision

Single **monorepo** with pnpm workspaces for JavaScript and an in-tree Python
package:

```
client/    React 19 + TS + Vite (pnpm package @civiserve/client)
server/    FastAPI + SQLAlchemy (Python package, pip-installable)
shared/    Canonical domain contracts (pnpm package @civiserve/shared + JSON Schema)
database/  Alembic migrations + seeds (independent of the API package)
docs/      Architecture + ADRs
assets/    Brand/presentation media
```

- `shared/` is the single source of truth for the API surface (TS types) and a
  language-neutral JSON Schema mirror.
- The server owns no migrations; `database/` does (decoupled deploy).
- Environments via `.env` (client) / `server/.env`; never committed.

## Consequences

+ One contract, one review, shared CI.
+ DB migrations run independently of API deploys.
− Two toolchains to install (Node/pnpm + Python).
− Requires discipline to keep `shared/` canonical (enforced by typecheck in client).

## Supersedes
None.
