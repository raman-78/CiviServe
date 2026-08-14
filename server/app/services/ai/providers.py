"""LLM providers behind a small protocol.

Production talks to Gemini through ``google-genai``; development/demo without a
key uses the deterministic :class:`RuleFallbackProvider` (grounded in the exact
scheme catalog the request already retrieved) so the whole chat pipeline works
end-to-end without a paid API key. The protocol is 2 methods (``complete`` /
``stream``) over a :class:`ProviderRequest` that carries both the assembled
prompt and the retrieved scheme refs the fallback needs to answer.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.config import get_settings
from app.core.errors import ExternalServiceError
from app.core.logging import get_logger
from app.services.recommendation.engine import evaluate_scheme
from app.services.translation.glossary import localize

logger = get_logger(__name__)


@dataclass(frozen=True)
class SchemeRef:
    """Compact, JSON-safe projection of a scheme used for grounding + payloads."""

    id: str
    code: str
    name_en: str
    category: str
    sub_category: str | None
    summary_en: str
    benefits: tuple[str, ...]
    eligibility_rules: tuple[dict[str, Any], ...]
    required_documents: tuple[dict[str, Any], ...]
    application_steps: tuple[dict[str, Any], ...]
    official_website: str | None
    last_verified_at: Any = None


@dataclass
class ProviderRequest:
    """Everything the provider needs for one assistant turn."""

    prompt: str
    query: str
    language: str
    intent: str
    retrieved_schemes: list[SchemeRef]
    profile: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    follow_up: bool = False


class LLMProvider(Protocol):
    """Minimal surface every provider (Gemini or fallback) must implement."""

    model_name: str

    def is_ai(self) -> bool: ...

    async def complete(self, request: ProviderRequest) -> str: ...

    def stream(self, request: ProviderRequest) -> AsyncIterator[str]: ...


class GeminiProvider:
    """Gemini client via the official ``google-genai`` SDK with retry+timeout."""

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        key = api_key or settings.gemini_api_key
        if not key:
            raise ExternalServiceError("Gemini API key is not configured.")
        from google import genai

        self.model = settings.gemini_model
        self.model_name = f"gemini/{settings.gemini_model}"
        self.temperature = settings.gemini_temperature
        self.max_output_tokens = settings.gemini_max_output_tokens
        self.timeout_seconds = settings.gemini_timeout_seconds
        self.retry_attempts = settings.gemini_retry_attempts
        self.retry_min_delay = settings.gemini_retry_min_delay_seconds
        self._client = genai.Client(api_key=key)
        self._settings = settings

    def is_ai(self) -> bool:
        return True

    def _config(self) -> Any:
        from google.genai import types as genai_types

        return genai_types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            response_mime_type="application/json",
        )

    async def complete(self, request: ProviderRequest) -> str:
        """Generate the full response text (cached when enabled)."""
        if self._settings.gemini_cache_enabled:
            cached = self._cache_lookup(request)
            if cached is not None:
                return cached
        text = "".join([chunk async for chunk in self.stream(request)])
        if self._settings.gemini_cache_enabled:
            self._cache_store(request, text)
        return text

    def _cache_key(self, request: ProviderRequest) -> str:
        prompt_fingerprint = str(len(request.prompt)) + request.prompt[:240]
        return f"gemini:{prompt_fingerprint}:{request.language}"

    def _cache_lookup(self, request: ProviderRequest) -> str | None:
        from app.core.cache import get_cache

        return get_cache().get(self._cache_key(request))

    def _cache_store(self, request: ProviderRequest, text: str) -> None:
        from app.core.cache import get_cache

        get_cache().set(self._cache_key(request), text)

    def stream(self, request: ProviderRequest) -> AsyncIterator[str]:
        """Stream raw tokens from Gemini. A generator so callers control pacing."""
        return self._stream_impl(request.prompt, request)

    async def _stream_impl(self, prompt: str, request: ProviderRequest) -> AsyncIterator[str]:
        attempts = self.retry_attempts + 1
        for attempt in range(attempts):
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    stream = await self._client.aio.models.generate_content_stream(
                        model=self.model, contents=prompt, config=self._config()
                    )
                    async for chunk in stream:
                        piece = getattr(chunk, "text", None)
                        if piece:
                            yield piece
                return
            except ExternalServiceError:
                raise
            except Exception as exc:  # noqa: BLE001 — any SDK/network error retries
                if attempt < self.retry_attempts:
                    await asyncio.sleep(self.retry_min_delay * (attempt + 1))
                    continue
                logger.warning("gemini_stream_failed", exc=str(exc)[:200])
                raise ExternalServiceError(
                    "The assistant's model provider is unavailable. Please try again."
                ) from exc


class RuleFallbackProvider:
    """Deterministic, fully-grounded answers for dev/test when no API key is set.

    Returns the same JSON contract the formatter expects; ``referencedSchemes``
    come directly from the retrieved catalog so the client cards stay accurate.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.model = f"rule-fallback.{settings.env}"
        self.model_name = self.model

    def is_ai(self) -> bool:
        return False

    async def complete(self, request: ProviderRequest) -> str:
        body = self._answer(request)
        return json.dumps(body, ensure_ascii=False)

    def stream(self, request: ProviderRequest) -> AsyncIterator[str]:
        async def _gen() -> AsyncIterator[str]:
            text = await self.complete(request)
            for piece in _chunk_text(text, size=64):
                yield piece
                await asyncio.sleep(0.001)

        return _gen()

    def _answer(self, request: ProviderRequest) -> dict[str, Any]:
        language = request.language or "en"
        schemes = list(request.retrieved_schemes)
        referenced = [s.code for s in schemes[:3]]
        if not schemes:
            answer = "\n".join(
                (localize("no_schemes", language), localize("not_verified", language))
            )
            return {
                "intent": request.intent or "general",
                "answer": answer,
                "referencedSchemes": [],
                "recommendations": [],
                "followUpQuestions": [localize("q_state", language)],
                "needsMoreInfo": True,
            }

        intent = request.intent or "scheme_discovery"
        lines: list[str] = []
        if intent == "greeting":
            lines.append(localize("greeting", language))
        elif intent == "document_guidance":
            top = schemes[0]
            docs = [str(d.get("name")) for d in top.required_documents if d.get("name")]
            lines.append(
                localize(
                    "docs_typical",
                    language,
                    scheme=f'**{top.name_en}** ("{top.code}")',
                    docs=", ".join(docs) or localize("docs_default", language),
                )
            )
            lines.append(localize("docs_available", language))
        elif intent == "application_help":
            top = schemes[0]
            steps = [
                (s.get("title") or {}).get("en") or s.get("step") for s in top.application_steps[:4]
            ]
            lines.append(
                localize("apply_steps", language, scheme=f'**{top.name_en}** ("{top.code}")')
                + " ".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
            )
            if top.official_website:
                lines.append(localize("apply_online", language, url=top.official_website))
        elif intent == "eligibility_check":
            lines.append(localize("relevant_schemes", language))
            for s in schemes[:3]:
                verdict = evaluate_scheme(s.eligibility_rules, request.profile)
                detail = verdict.reasons[0] if verdict.reasons else s.summary_en
                lines.append(f"- **{s.name_en}** ({s.code}) — {detail}")
            if request.missing_fields:
                lines.append(localize("need_more_info", language))
        else:
            for s in schemes[:3]:
                lines.append(f"- **{s.name_en}** ({s.code}) — {s.summary_en}")
            lines.append(localize("tell_me_more", language))

        questions = [
            localize(_FIELD_TO_KEY[f], language)
            for f in (request.missing_fields or [])
            if f in _FIELD_TO_KEY
        ]
        return {
            "intent": intent,
            "answer": "\n".join(lines),
            "referencedSchemes": referenced,
            "recommendations": [],
            "followUpQuestions": questions,
            "needsMoreInfo": bool(questions),
        }


#: missing-info field → localized-message id (see translation/glossary.py).
_FIELD_TO_KEY: dict[str, str] = {
    "age": "q_age",
    "income_band": "q_income_band",
    "annual_income": "q_income_band",
    "state": "q_state",
    "gender": "q_gender",
    "occupation": "q_occupation",
    "education": "q_education",
    "is_farmer": "q_is_farmer",
    "is_student": "q_is_student",
    "is_disabled": "q_is_disabled",
    "is_minority": "q_is_minority",
    "is_widow": "q_is_widow",
    "is_self_employed": "q_is_self_employed",
}


async def build_fall_answer(request: ProviderRequest) -> str:
    """Public shim used by tests to mimic a real LLM call."""
    return await RuleFallbackProvider().complete(request)


def _chunk_text(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


def get_llm_provider() -> LLMProvider:
    """Factory: real Gemini when a key is set; grounded fallback elsewhere.

    ``None`` env (production) without a key is a hard configuration error so we
    never silently serve a demo answer in a real deployment.
    """
    settings = get_settings()
    if settings.gemini_api_key:
        return GeminiProvider()
    if not settings.is_production:
        return RuleFallbackProvider()
    raise ExternalServiceError("GEMINI_API_KEY is not configured for this environment.")
