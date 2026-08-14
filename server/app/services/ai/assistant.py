"""Orchestration: retrieve → analyse → prompt → LLM → format → ground.

Provides both a blocking ``reply`` and a streaming (SSE) path that share the
same pipeline, so non-stream and stream URLs behave identically modulo
transport.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User, UserProfile
from app.services.ai.formatter import ResponseFormatter
from app.services.ai.profile import profile_to_dict
from app.services.ai.prompt import build_prompt
from app.services.ai.providers import LLMProvider, ProviderRequest, get_llm_provider
from app.services.ai.query import QueryProcessor
from app.services.ai.recommendations import RecommendationService
from app.services.ai.retrieval import RetrievalService
from app.services.translation.service import TranslationService


class AIAssistantService:
    """Grounds and generates one assistant turn on top of the AI primitives."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: LLMProvider | None = None,
    ) -> None:
        self.retrieval = RetrievalService(session)
        self.recommendations = RecommendationService(session)
        self.queries = QueryProcessor()
        self.formatter = ResponseFormatter()
        self.translation = TranslationService()
        self.provider = provider or get_llm_provider()
        settings = get_settings()
        self.top_k = settings.rag_top_k
        self.history_limit = settings.chat_context_message_limit

    async def build_request(
        self,
        *,
        query: str,
        user: User,
        profile: UserProfile | None,
        history: list[tuple[str, str]],
        language: str = "en",
    ) -> ProviderRequest:
        """Assemble the prompt + retrieved refs (used by reply and stream).

        The user's message may be in any supported language: we detect it
        (preferring the declared ``language`` for romanized input), translate it
        to English so retrieval/intent/facts run on the catalog's language, and
        ask the model to reply in the detected language. ``ProviderRequest.query``
        carries the English working copy (recommendations search on it); the raw
        user text stays in the prompt for the model to see.
        """
        detection = self.translation.detect(query, preferred=language)
        working_language = detection.language
        analysis_query = query
        if working_language != "en":
            analysis_query = await self.translation.to_english(query, source=working_language)

        profile_dict = profile_to_dict(user, profile)
        refs = await self.retrieval.retrieve(analysis_query, profile=profile_dict, top_k=self.top_k)
        analysis = self.queries.analyse(analysis_query, profile=profile_dict, retrieved=refs)
        effective_profile = dict(profile_dict)
        effective_profile.update(analysis.extracted_facts)

        prompt = build_prompt(
            user_query=query,
            language=working_language,
            intent=analysis.intent,
            retrieved=refs,
            profile=effective_profile,
            missing_fields=analysis.missing_fields,
            history=history[-self.history_limit :],
            is_follow_up=analysis.is_follow_up,
        )
        return ProviderRequest(
            prompt=prompt,
            query=analysis_query,
            language=working_language,
            intent=analysis.intent,
            retrieved_schemes=list(refs),
            profile=effective_profile,
            missing_fields=analysis.missing_fields,
            follow_up=analysis.is_follow_up,
        )

    async def complete_turn(self, request: ProviderRequest) -> dict[str, Any]:
        """Fetch the provider output and resolve it into a client-ready payload."""
        raw = await self.provider.complete(request)
        return await self.resolve(raw, request)

    async def resolve(self, raw: str, request: ProviderRequest) -> dict[str, Any]:
        """Parse/validate/build the payload for one turn (shared sync + stream)."""
        refs_by_code = {ref.code: ref for ref in request.retrieved_schemes}
        parsed = self.formatter.parse(raw, list(request.retrieved_schemes))

        recommendations = list(parsed.recommendations)
        if not recommendations:
            recommendations = await self.recommendations.recommend(
                query=request.query,
                profile=request.profile,
                exclude_codes=parsed.referenced_codes,
                limit=3,
                language=request.language,
            )

        payload = parsed.to_payload(
            schemes_by_code=refs_by_code,
            verified=parsed.verified,
            note=parsed.note,
            source_codes=list(refs_by_code.keys()),
        )
        payload["recommendationFallbacks"] = [
            rec for rec in recommendations if rec.get("code") not in parsed.referenced_codes
        ][:3]
        payload["recommendations"] = recommendations
        payload["contentType"] = "text"
        payload["answer"] = parsed.answer
        payload["intent"] = parsed.intent
        return {
            "answer": parsed.answer,
            "intent": parsed.intent,
            "payload": payload,
            "referenced_codes": parsed.referenced_codes,
        }

    async def stream_answer(self, request: ProviderRequest) -> AsyncIterator[str]:
        """Yield raw provider tokens, then a terminal __end__ sentinel."""
        async for chunk in self.provider.stream(request):
            yield chunk
        yield "__end__"
