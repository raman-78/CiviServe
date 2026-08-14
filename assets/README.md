# Assets

Non-code, non-secret project assets referenced by the repo.

```
assets/
├── brand/     # Logo source (SVG/PNG), favicon, color palette, fonts, brand guide
└── media/     # Screenshots, demo videos, presentation materials (HackElite 2026)
```

## Rules

- **Never commit user data, PII, or voice/audio samples** here — only brand/design media.
- Keep original vector sources (`.svg`, `.fig`) plus optimized web exports.
- Large binaries belong in a CDN/object store, not git (repo stays lean).
