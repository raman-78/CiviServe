# Contributing — CiviServe

## Development workflow (summary)

Full workflow details: [`docs/architecture/18-development-workflow.md`](docs/architecture/18-development-workflow.md)
Branching strategy: [`docs/architecture/19-git-branching.md`](docs/architecture/19-git-branching.md)

1. **Branch** from `main`: `feature/<prompt>-<slug>` (e.g. `feature/07-translation`).
2. **Develop** in small, focused commits. Run quality gates locally before pushing.
3. **Open a PR** to `main`. CI runs typecheck/lint/test/build automatically.
4. **Review** — at least one approval, all checks green.
5. **Merge** with squash; CI deploys to preview/staging, then production on `main`.

## Quality gates (run before every push)

```bash
# JS workspace (client + shared)
pnpm install --frozen-lockfile
pnpm verify

# Python (server)
pip install -e server
pip install -r server/requirements-dev.txt
ruff check server
ruff format --check server
mypy server
pytest server/tests
```

## Conventions

- **No comments unless they explain "why".** Follow existing style; the repo uses
  Prettier (TS) and Ruff (Python) defaults.
- **Feature-sliced frontend**: code that belongs to a feature lives in
  `client/src/features/<feature>/`, not scattered in `components/`.
- **Shared contracts** live in `shared/src/domain/` and are the source of truth.
  When a contract changes, update the TS types *and* the JSON Schema, and keep the
  future Pydantic/DB layers in lockstep.
- **One migration per change**; never edit an applied Alembic migration.
- **No secrets**: commit `.env.example` only. Real keys live in CI/Vercel/Railway
  secrets. Never commit `firebase-service-account.json`.
- **Layering (server)**: routers → services → repositories → db. No exceptions.
- **Commits**: conventional-ish, imperative, ≤ 72 chars subject
  (e.g. `feat(chat): wire Gemini provider interface`).

## Pull request checklist

- [ ] Branch is up to date with `main`.
- [ ] `pnpm verify` passes (JS) and `ruff`/`mypy`/`pytest` pass (Python).
- [ ] Migration included for DB changes; seed data idempotent.
- [ ] Shared contracts updated where the API surface changed.
- [ ] `.env.example` updated for any new environment variable.
- [ ] ADR added for significant architectural decisions.
