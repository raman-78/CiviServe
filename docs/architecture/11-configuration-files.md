# 11 — Configuration Files

Inventory of every config file and its role. All files listed here already exist
in the repo (Prompt 1).

## Root

| File | Purpose |
| ---- | ------- |
| `package.json` | pnpm workspace root; orchestrator scripts (`dev:*`, `verify`, `lint:server`, `test:server`) |
| `pnpm-workspace.yaml` | Declares `client`, `shared` workspaces |
| `.nvmrc` | Node 20.19.0 pin |
| `.editorconfig` | UTF-8, LF, 2-space (4-space for Python) |
| `.gitignore` | Node/Python/build/secrets/IDE excludes |
| `.prettierrc.mjs` | Prettier defaults + tailwind plugin |
| `AGENTS.md` | Agent/orchestrator guide |
| `CONTRIBUTING.md` | Contribution workflow + checklist |

## Client

| File | Purpose |
| ---- | ------- |
| `vite.config.ts` | Dev server + `/api` proxy, path aliases (`@`, `@civiserve/shared`), manual chunks |
| `tsconfig.json` | Solution file → app + node references |
| `tsconfig.app.json` | App TS config (strict, `@/*` alias, shared path) |
| `tsconfig.node.json` | Tooling TS config (vite.config) |
| `tailwind.config.ts` | shadcn theme tokens, animations, fonts (Indic font stack) |
| `postcss.config.js` | Tailwind + autoprefixer |
| `components.json` | shadcn/ui registry config (new-york style, lucide) |
| `eslint.config.js` | ESLint flat config (react-hooks, react-refresh, TS strict) |
| `.env.example` | Documented client env (doc 10) |

## Server

| File | Purpose |
| ---- | ------- |
| `pyproject.toml` | PEP 621 metadata, dependencies, `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest]`, `[tool.coverage]` |
| `requirements.txt` | Pinned mirror for Docker builds |
| `Dockerfile` | Builder + distroless-style runtime, non-root user |
| `.dockerignore` | Keep images lean (tests, venv, git) |
| `.env.example` | Documented server env (doc 10) |

## Database

| File | Purpose |
| ---- | ------- |
| `database/README.md` | Migrations/seeds/scripts conventions |

## Shared

| File | Purpose |
| ---- | ------- |
| `shared/tsconfig.json` | Strict TS, noEmit (pure type package) |
| `shared/eslint.config.js` | TS lint |
| `shared/schemas/scheme.schema.json` | Canonical contract (JSON Schema) |

## CI/CD

| File | Purpose |
| ---- | ------- |
| `.github/workflows/ci.yml` | PR/push gate: client + server checks |
| `.github/workflows/deploy-client.yml` | Vercel production deploy on `main` |
| `.github/workflows/deploy-server.yml` | Railway deploy on `main` |

## Change policy

- Any new runtime knob that affects behavior goes through **env vars**, and its
  default must be safe for `development`.
- Adding a config file to this list is a review criterion; keep the inventory
  updated in this doc.
