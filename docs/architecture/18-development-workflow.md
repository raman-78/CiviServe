# 18 — Development Workflow

## Local setup (one-time)

```bash
# 0. Prereqs
#    Node >= 20.19, pnpm >= 9, Python >= 3.11, PostgreSQL 16 (or Neon)

# 1. JS toolchain
pnpm install

# 2. Python env
python -m venv server/.venv
server\.venv\Scripts\Activate.ps1        # Windows; source server/.venv/bin/activate on *nix
pip install -e server
pip install -r server/requirements-dev.txt

# 3. Environment files
cp client/.env.example client/.env.local
cp server/.env.example server/.env        # fill DATABASE_URL + keys
```

## Day-to-day loop

```bash
# Terminal 1 — frontend (HMR on :5173, proxies /api → :8000)
pnpm --filter @civiserve/client dev

# Terminal 2 — backend (reload on :8000)
python -m uvicorn app.main:app --reload --app-dir server

# Terminal 3 — DB (once per new migration)
cd database && alembic upgrade head
```

## Feature workflow (per prompt)

1. Create branch: `feature/<prompt>-<slug>` (doc 19).
2. Implement following the layering/feature-slice rules (docs 02/03).
3. Update `shared` contracts first when the API surface changes.
4. Add migrations + idempotent seeds for data changes (doc 05).
5. Run **quality gates** locally (below).
6. Push, open PR, CI re-runs gates, deploy previews (Vercel + Railway).
7. Merge with squash → production deploy on `main`.

## Quality gates (must pass before push)

```bash
# JS (client + shared)
pnpm verify                       # typecheck → lint → test

# Python
python -m ruff check server
python -m ruff format --check server
python -m mypy server
python -m pytest server/tests
```

> `AGENTS.md` records these exact commands for the orchestrator (opencode), so
> every future prompt can self-verify.

## Code review checklist

- [ ] No UI strings outside i18n resources.
- [ ] No provider implementation referenced by feature code (interface only).
- [ ] Server: no router→model import; schemas mirror `shared`.
- [ ] Migration reversible + append-only; seeds idempotent.
- [ ] `.env.example` updated for new vars; `docs/11` inventory synced.
- [ ] Security: no secrets; rate limits considered for new endpoints.
- [ ] Tests added/updated; `pnpm verify` + `pytest` green.

## Environments

| Env | Purpose | Deploy |
| --- | ------- | ------ |
| Local | dev loop, HMR, seeded DB | — |
| Preview | per-PR (Vercel preview + Railway) | CI on PR |
| Staging | release candidate, integration | manual promote |
| Production | `main` branch | CI on merge |

## Versioning & changelog

- Semver on the repo; prompt milestones tagged (`prompt-07`).
- CHANGELOG updated per merged feature batch.
