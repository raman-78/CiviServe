# Architecture Decision Records (ADRs)

Significant, irreversible, or cross-cutting decisions are captured as ADRs so
future prompts and contributors know *why* the architecture is shaped this way.

## Status of decisions

| ADR | Title | Status |
| --- | ----- | ------ |
| ADR-0001 | Monorepo structure (pnpm workspaces + Python server) | Accepted (Prompt 1) |

## Index

- [ADR-0001](ADR-0001-monorepo-foundation.md)

## Guidelines

- **Add an ADR** when a decision affects multiple modules, the API surface, or is
  hard to reverse (e.g. "adopt Google Maps", "switch to PaddleOCR").
- Number sequentially. Filename: `ADR-<NNNN>-<kebab-title>.md`.
- Statuses: *Proposed → Accepted | Superseded*. Never delete a superseded ADR —
  reference the replacement.
