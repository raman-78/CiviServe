# 19 — Git Branching Strategy

## Model: GitHub Flow (with a staging release train)

Trunk-based with `main` always deployable — best fit for a small hackathon team
with continuous deploy automation. Simpler than GitFlow, and the 15-prompt
sequence maps cleanly to feature branches.

```
main  ──────┬──────────────┬──────────────●──────────  (always green, deployable)
            │              │              │
feature/07-translation ──▶ │              │
            │              │              │
feature/08-auth  ──────────▶              │
                                          │
tag prompt-07 ────────────────────────────▶
```

## Branches

| Branch | Lifecycle | Rule |
| ------ | --------- | ---- |
| `main` | Permanent | Protected: 1+ approval, CI green, squash merge only |
| `staging` | Permanent | Release train; auto-deploy to staging env |
| `feature/<prompt>-<slug>` | Short-lived | One feature per PR; e.g. `feature/07-translation`, `feature/08-firebase-auth` |
| `fix/<slug>` | Short-lived | Bug fixes off `main` |
| `chore/<slug>` | Short-lived | Tooling/deps/refactor |
| `release/<ver>` | Temporary | Cut from staging, PR → main |

## Rules

1. **Never commit directly to `main`/`staging`.** PRs only.
2. **Branch from `main`**, keep it rebased (`git pull --rebase`) before PR.
3. **One logical change per PR**; prompt-aligned branches recommended.
4. **Squash-merge** feature PRs → clean history; release PRs use a merge commit.
5. **Tag milestones** (`prompt-07`, `v0.7.0`) for demo/recovery points.
6. CI is the gatekeeper: typecheck/lint/test/build + deployment previews
   (`.github/workflows/ci.yml`).
7. **Conventional commits** for squash messages:
   `feat(chat): …`, `fix(centers): …`, `refactor(api): …`, `chore(deps): …`.

## Hotfix path

1. `fix/<slug>` from `main` → PR with minimal diff → merge → auto-prod-deploy.
2. Cherry-pick into `staging` for the release train.

## Merge strategy cheat-sheet

| Situation | Action |
| --------- | ------ |
| Feature complete | squash merge → `main` |
| Release promotion | merge `staging` → `main` (merge commit) |
| Critical hotfix | branch `main`, PR, merge → deploy |
| Parallel prompts | separate feature branches, both merge when green |
