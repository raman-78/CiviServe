"""AI layer: provider, retrieval, query-analysis, prompting, formatting.

Sub-packages are deliberately small and dependency-light so the chat request
path stays readable:
- :mod:`providers`  — Gemini + deterministic rule-based fallback provider.
- :mod:`retrieval`  — ground the reply in the scheme catalog (RAG).
- :mod:`query`      — intent/profile-fact/missing-info/follow-up analysis.
- :mod:`prompt`     — system prompt + context assembly (incl. injection guard).
- :mod:`formatter`  — LLM JSON → structured ChatMessage payload.
- :mod:`recommendations` — rule-based "eligible or not-excluded" suggestions.
"""
