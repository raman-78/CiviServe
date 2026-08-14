# Scripts

Reusable developer/ops helpers shared across the repo. Each script is idempotent
and documents its purpose at the top. Cross-platform: provide both `.sh` and `.ps1`
variants where teamwork on Windows + macOS/Linux requires it.

> DB-specific operations (migrate/seed/backup) live in `database/scripts/` — see
> `database/README.md`. This folder holds **repo-wide** helpers.

Planned scripts (added as needed in later prompts):

| Script | Purpose |
| ------ | ------- |
| `bootstrap` (`.sh`/`.ps1`) | One-shot setup: install JS + Python deps, copy environment templates, create venv |
| `gen-api-types` (`.sh`) | Run `openapi-typescript` on `server` → write `shared/contracts/generated/types.ts` (optional codegen path, doc 06) |
| `ci-verify` (`.sh`) | Lint + typecheck + test gate used by CI (`pnpm verify` + ruff + mypy + pytest) |
| `build` (`.sh`) | Repo-wide production build (client) for Vercel/diagnostics |

Keep `.sh` and `.ps1` behaviors identical; assert exit codes so they fail loudly in CI.