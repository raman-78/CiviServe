# Agent guide for this repository (opencode)

## Environment

- Windows (win32), PowerShell 5.1 shell. Use `cmd1; if ($?) { cmd2 }` to chain.
- `git`/`node` may not be on PATH in this shell — check with
  `Get-Command git` before relying on them.

## Commands

Quality gates for the JS workspace and Python server:

```bash
pnpm verify                        # typecheck + lint + test (client & shared)
python -m ruff check server        # lint Python
python -m ruff format --check server
python -m mypy server
python -m pytest server/tests      # Python tests
```

## Project facts

- Monorepo: pnpm workspaces (`client`, `shared`) + Python `server/`.
- Prompt 1 of 15: **architecture + foundation only**. Do not implement UI,
  backend logic, DB schema, APIs, AI, auth, translation, or speech unless a
  later prompt explicitly asks.
- Canonical domain contracts live in `shared/src/domain/*.ts` and are the source
  of truth for the API surface.
- No `git` repo initialized yet; do not init/commit unless the user asks.
