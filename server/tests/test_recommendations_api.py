"""Integration tests for the recommendations API (Prompt 10).

Covers /evaluate ranking + camelCase contract, state scoping, progressive
missing-fields, alternatives, and best-effort persistence for non-guest users.
Each request uses a unique X-Forwarded-For so the in-memory per-IP rate
limiter never interferes with other test modules.
"""

from __future__ import annotations

import itertools

from app.db.session import get_session_factory
from app.models.eligibility import UserEligibilityResult
from fastapi.testclient import TestClient
from sqlalchemy import func, select

PREFIX = "/api/v1/recommendations"

_ips = itertools.count(1)


def _ip() -> str:
    return f"203.0.113.{next(_ips)}"


def _headers(**extra: str) -> dict[str, str]:
    return {"X-Forwarded-For": _ip(), **extra}


def test_evaluate_senior_in_tamil_nadu(client: TestClient) -> None:
    payload = {"stateCode": "TN", "age": 68, "incomeBand": "below-poverty", "isSeniorCitizen": True}
    res = client.post(f"{PREFIX}/evaluate", json=payload, headers=_headers())
    assert res.status_code == 200
    body = res.json()
    assert {"recommendations", "missingFields"} <= body.keys()
    recs = body["recommendations"]
    assert 0 < len(recs) <= 10
    ignoaps = next((r for r in recs if r["scheme"]["code"] == "IGNOAPS"), None)
    assert ignoaps is not None
    assert ignoaps["status"] == "eligible"
    assert ignoaps["matchScore"] == 100.0
    assert ignoaps["fullyEligible"] is True
    assert any("Age 60" in reason for reason in ignoaps["reasons"])


def test_evaluate_empty_profile_asks_questions(client: TestClient) -> None:
    res = client.post(f"{PREFIX}/evaluate", json={}, headers=_headers())
    assert res.status_code == 200
    body = res.json()
    assert body["missingFields"], "empty profile must ask for fields"
    statuses = {rec["status"] for rec in body["recommendations"]}
    assert statuses <= {"eligible", "likely", "needs_more_info", "not_eligible"}


def test_evaluate_respects_requested_limit(client: TestClient) -> None:
    res = client.post(f"{PREFIX}/evaluate", json={"age": 30, "limit": 4}, headers=_headers())
    assert res.status_code == 200
    assert len(res.json()["recommendations"]) == 4


def test_evaluate_state_scoping_excludes_non_applicable(client: TestClient) -> None:
    res = client.post(
        f"{PREFIX}/evaluate", json={"stateCode": "KA", "isFarmer": True}, headers=_headers()
    )
    assert res.status_code == 200
    codes = {rec["scheme"]["code"] for rec in res.json()["recommendations"]}
    assert "TN-BC-EDU" not in codes
    assert "KA-RAITHA" in codes


def test_missing_fields_progressively_shrink(client: TestClient) -> None:
    empty = client.post(f"{PREFIX}/missing-fields", json={}, headers=_headers()).json()[
        "missingFields"
    ]
    assert empty
    partial = client.post(
        f"{PREFIX}/missing-fields",
        json={"age": 68, "incomeBand": "below-poverty"},
        headers=_headers(),
    ).json()["missingFields"]
    assert len(partial) < len(empty)


def test_alternatives_never_repeat_and_are_possible(client: TestClient) -> None:
    payload = {"stateCode": "TN", "isStudent": False}
    res = client.post(f"{PREFIX}/TN-BC-EDU/alternatives", json=payload, headers=_headers())
    assert res.status_code == 200
    alts = res.json()
    assert alts, "TN must offer non-student schemes"
    for rec in alts:
        assert rec["scheme"]["code"] != "TN-BC-EDU"
        assert rec["status"] != "not_eligible"


def test_alternatives_unknown_scheme_is_404(client: TestClient) -> None:
    res = client.post(f"{PREFIX}/NOPE-999/alternatives", json={}, headers=_headers())
    assert res.status_code == 404


async def test_evaluate_persists_for_authenticated_user(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post(
        f"{PREFIX}/evaluate",
        json={"stateCode": "TN", "age": 68, "incomeBand": "below-poverty", "isSeniorCitizen": True},
        headers=_headers(**auth_headers),
    )
    factory = get_session_factory()
    async with factory() as session:
        total = (await session.execute(select(func.count(UserEligibilityResult.id)))).scalar_one()
    assert total > 0


def test_evaluate_does_not_persist_for_guest(
    client: TestClient, guest_headers: dict[str, str]
) -> None:
    factory = get_session_factory()

    async def run() -> tuple[int, int]:
        async with factory() as before_session:
            before = (
                await before_session.execute(select(func.count(UserEligibilityResult.id)))
            ).scalar_one()
        response = client.post(f"{PREFIX}/evaluate", json={}, headers=_headers(**guest_headers))
        assert response.status_code == 200
        async with factory() as after_session:
            after = (
                await after_session.execute(select(func.count(UserEligibilityResult.id)))
            ).scalar_one()
        return int(before), int(after)

    import asyncio

    before, after = asyncio.run(run())
    assert before == after  # guests never persist verdicts
