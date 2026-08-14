"""Prompt 8 — multilingual: detection, translation, preservation, chat wiring.

These cover the required scenarios: auto language detection (Hindi/Tamil/etc.),
mixed/romanized input, query translation before retrieval, AI response language,
session language persistence, multilingual scheme search, terminology
preservation (scheme codes / URLs / currency) and graceful fallback when no
translation provider is configured.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from app.services.ai.providers import ProviderRequest, RuleFallbackProvider, SchemeRef
from app.services.translation.detect import detect, effective_language
from app.services.translation.service import TranslationService
from app.services.translation.terminology import normalise_query, protect
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("नमस्ते, मैं किसान हूँ", "hi"),
        ("मी शेतकरी आहे", "mr"),  # Marathi marker "आहे"
        ("வணக்கம், நான் ஒரு விவசாயி", "ta"),
        ("నమస్కారం, నేను రైతును", "te"),
        ("ನಮಸ್ಕಾರ, ನಾನು ರೈತ", "kn"),
        ("എനിക്ക് പെൻഷൻ വേണം", "ml"),
        ("नમસ્તે હું ખેડૂત છું", "gu"),
        ("ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਮੈਂ ਕਿਸਾਨ ਹਾਂ", "pa"),
        ("ମୁଁ ଜଣେ ଚାଷୀ", "or"),
        ("আমি একজন কৃষক", "bn"),
        ("আপুনি অসমৰ কৃষক নেকি?", "as"),  # Assamese marker "আপুনি"
        ("سلام میں کسان ہوں", "ur"),
        ("I am a farmer in Maharashtra", "en"),
    ],
)
def test_detect_script_to_language(text: str, expected: str) -> None:
    assert detect(text).language == expected


def test_detect_prefers_declared_language_for_romanized_input() -> None:
    # Latin script but romanized Hinglish → the declared preference wins.
    assert effective_language("Mujhe PM Kisan ke baare mein batao", preferred="hi") == "hi"
    # Declared "hi" but real Devanagari → detection wins.
    assert effective_language("मुझे किसान योजना बताओ", preferred="en") == "hi"


def test_detect_mixed_language_flag() -> None:
    mixed = detect("தமிழ் schemes for farmers")
    assert mixed.mixed is True


# ---------------------------------------------------------------------------
# Terminology preservation
# ---------------------------------------------------------------------------


def test_protect_roundtrip_preserves_codes_urls_and_money() -> None:
    original = "Check PM-KISAN and IGNOAPS at https://pmkisan.gov.in — benefit ₹2,50,000/yr."
    protected = protect(original)
    assert protected.restore() == original
    # Protected text keeps no raw code / URL / money.
    assert "PM-KISAN" not in protected.text
    assert "https://" not in protected.text
    assert "₹" not in protected.text


def test_normalise_query_loanwords() -> None:
    assert "farmer" in normalise_query("किसान योजना")
    assert "pension" in normalise_query("पेंशन स्कीम")


# ---------------------------------------------------------------------------
# Translation service (identity + fake provider)
# ---------------------------------------------------------------------------


async def test_translate_identity_returns_text() -> None:
    service = TranslationService()
    assert await service.to_english("hello", source="hi") == "hello"
    assert await service.translate("नमस्ते", source="hi", target="en") == "नमस्ते"


class _FakeProvider:
    """Deterministic fake: uppercases and tags input, preserving placeholders."""

    name = "fake"
    capable = True

    async def translate(self, text: str, *, source: str, target: str) -> str:
        return f"TR:{text}:{target}"


async def test_translate_preserves_protected_spans() -> None:
    service = TranslationService(provider=_FakeProvider())
    result = await service.translate(
        "Apply to PM-KISAN at https://pmkisan.gov.in for ₹2,50,000.",
        source="en",
        target="hi",
    )
    assert "PM-KISAN" in result
    assert "https://pmkisan.gov.in" in result
    assert "₹2,50,000" in result


async def test_translate_answer_skips_when_already_in_target() -> None:
    service = TranslationService(provider=_FakeProvider())
    # Detected as Tamil, target Tamil → no translation round-trip.
    assert await service.translate_answer("வணக்கம் நண்பரே", target="ta") == "வணக்கம் நண்பரே"


# ---------------------------------------------------------------------------
# Deterministic fallback provider localizes its copy
# ---------------------------------------------------------------------------


def _scheme(code: str = "PM-KISAN") -> SchemeRef:
    return SchemeRef(
        id="1",
        code=code,
        name_en="PM Kisan Samman Nidhi",
        category="agriculture",
        sub_category=None,
        summary_en="Direct income support for farmers.",
        benefits=("₹2,50,000",),
        eligibility_rules=(),
        required_documents=(),
        application_steps=(),
        official_website="https://pmkisan.gov.in",
    )


def _request(language: str, intent: str, schemes: list[SchemeRef]) -> ProviderRequest:
    return ProviderRequest(
        prompt="",
        query="",
        language=language,
        intent=intent,
        retrieved_schemes=schemes,
    )


def test_fallback_greeting_localized_to_tamil() -> None:
    import asyncio

    answer = json.loads(
        asyncio.run(RuleFallbackProvider().complete(_request("ta", "greeting", [_scheme()])))
    )
    assert "வணக்கம்" in answer["answer"]
    assert answer["followUpQuestions"] == []


def test_fallback_english_when_language_en() -> None:
    import asyncio

    answer = json.loads(
        asyncio.run(RuleFallbackProvider().complete(_request("en", "greeting", [_scheme()])))
    )
    assert answer["answer"].startswith("Hello!")
    assert answer["followUpQuestions"] == []


def test_fallback_docs_localized() -> None:
    import asyncio

    answer = json.loads(
        asyncio.run(
            RuleFallbackProvider().complete(_request("hi", "document_guidance", [_scheme()]))
        )
    )
    assert "आधार" in answer["answer"] or "दस्तावेज़" in answer["answer"]


# ---------------------------------------------------------------------------
# Chat wiring: detection → translation → reply language → session persistence
# ---------------------------------------------------------------------------


class _RecordingLLM:
    """Fake LLM that records every ProviderRequest (prompt, query, language)."""

    model_name = "fake"

    def __init__(self, calls: list[dict[str, Any]]) -> None:
        self.calls = calls

    def is_ai(self) -> bool:
        return True

    async def complete(self, req: ProviderRequest) -> str:
        self.calls.append({"prompt": req.prompt, "query": req.query, "language": req.language})
        code = req.retrieved_schemes[0].code if req.retrieved_schemes else "PM-KISAN"
        return json.dumps(
            {
                "intent": "scheme_discovery",
                "answer": f"Here is {code}.",
                "referencedSchemes": [code],
                "recommendations": [],
                "followUpQuestions": [],
                "needsMoreInfo": False,
            }
        )

    def stream(self, req: ProviderRequest) -> AsyncIterator[str]:
        async def _gen() -> AsyncIterator[str]:
            yield await self.complete(req)
            yield "__end__"

        return _gen()


def _install_recording_llm(monkeypatch: Any, calls: list[dict[str, Any]]) -> None:
    import app.services.ai.assistant as assistant_mod

    def factory() -> Any:
        return _RecordingLLM(calls)

    monkeypatch.setattr(assistant_mod, "get_llm_provider", factory)


class _FixedProvider:
    """Translation stub: teaches the service a couple of phrase mappings."""

    name = "fixed"
    capable = True
    _MAP = {
        ("hi", "en"): {
            "किसान के लिए योजनाएँ कौन सी हैं": "which schemes are for farmers",
        },
    }

    async def translate(self, text: str, *, source: str, target: str) -> str:
        return self._MAP.get((source, target), {}).get(text, text)


def _install_fixed_provider(monkeypatch: Any) -> None:
    import app.services.translation.service as service_mod

    def factory() -> Any:
        return _FixedProvider()

    monkeypatch.setattr(service_mod, "get_translation_provider", factory)


def test_chat_tamil_query_replies_in_tamil(client: TestClient, monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []
    _install_recording_llm(monkeypatch, calls)
    headers = {"X-Dev-User-Id": "ml-user"}
    session_id = client.post("/api/v1/chat/sessions", json={}, headers=headers).json()["id"]

    res = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"text": "எனக்கு பணம் உதவி திட்டம் சொல்லுங்கள்", "language": "en"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["role"] == "assistant"
    assert body["language"] == "ta"

    prompt = calls[0]["prompt"]
    assert "LANGUAGE: ta" in prompt
    # The raw user text stays in the prompt; the model is asked to reply in Tamil.
    assert "எனக்கு" in prompt

    # Session language follows the detected language (not recreated).
    session = client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers).json()
    assert session["language"] == "ta"

    # The stored user message is also tagged Tamil.
    history = client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=headers).json()
    user_msg = next(m for m in history["items"] if m["role"] == "user")
    assert user_msg["language"] == "ta"


def test_chat_translates_query_before_retrieval(client: TestClient, monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []
    _install_recording_llm(monkeypatch, calls)
    _install_fixed_provider(monkeypatch)
    headers = {"X-Dev-User-Id": "ml-translate-user"}
    session_id = client.post("/api/v1/chat/sessions", json={}, headers=headers).json()["id"]

    res = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"text": "किसान के लिए योजनाएँ कौन सी हैं", "language": "hi"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    assert res.json()["language"] == "hi"

    request = calls[0]
    assert request["language"] == "hi"
    assert request["query"] == "which schemes are for farmers"
    assert "LANGUAGE: hi" in request["prompt"]


def test_chat_mixed_language_query(client: TestClient, monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []
    _install_recording_llm(monkeypatch, calls)
    headers = {"X-Dev-User-Id": "ml-mixed-user"}
    session_id = client.post("/api/v1/chat/sessions", json={}, headers=headers).json()["id"]

    res = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"text": "தமிழ் schemes for farmers please", "language": "ta"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    assert res.json()["language"] == "ta"
    assert "LANGUAGE: ta" in calls[0]["prompt"]


# ---------------------------------------------------------------------------
# Multilingual scheme search
# ---------------------------------------------------------------------------


def test_search_localizes_indic_query(client: TestClient, monkeypatch: Any) -> None:
    class _SearchProvider:
        name = "search-fake"
        capable = True

        async def translate(self, text: str, *, source: str, target: str) -> str:
            return "kisan" if source == "hi" else text

    monkeypatch.setattr(
        "app.services.translation.service.get_translation_provider",
        lambda: _SearchProvider(),
    )
    res = client.get("/api/v1/schemes/search", params={"q": "किसान"})
    assert res.status_code == 200, res.text
    codes = {item["code"] for item in res.json()["items"]}
    assert "PM-KISAN" in codes
