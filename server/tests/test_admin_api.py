"""Admin dashboard API tests (Prompt 15): RBAC, lifecycle, reviews, import,
feedback, users, audit, health."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _admin(headers: dict | None = None) -> dict[str, str]:
    return {"X-Dev-User-Id": "admin-api-1", "X-Dev-User-Role": "admin", **(headers or {})}


def _staff(headers: dict | None = None) -> dict[str, str]:
    return {"X-Dev-User-Id": "editor-api-1", "X-Dev-User-Role": "content_editor", **(headers or {})}


def _citizen(headers: dict | None = None) -> dict[str, str]:
    return {"X-Dev-User-Id": "citizen-api-1", "X-Dev-User-Role": "citizen", **(headers or {})}


def _scheme_payload(code: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code,
        "name": {"en": f"Scheme {code}", "native": ""},
        "summary": {"en": f"Summary for {code}.", "native": ""},
        "description": {"en": f"Description for {code}.", "native": ""},
        "category": "education",
        "sub_category": "scholarship",
        "ministry": "Ministry of Test",
        "department": "Department of Scholarships",
        "scope": "central",
        "scheme_status": "draft",
    }
    payload.update(overrides)
    return payload


def _valid_rules() -> list[dict[str, Any]]:
    return [
        {"field": "age", "operator": "gte", "value": 18},
        {"field": "income_band", "operator": "eq", "value": "low"},
    ]


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


def test_admin_requires_auth(client: TestClient) -> None:
    res = client.get("/api/v1/admin/overview")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_UNAUTHENTICATED"


def test_admin_requires_admin_role(client: TestClient) -> None:
    # citizen → 403
    res = client.get("/api/v1/admin/overview", headers=_citizen())
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "AUTH_FORBIDDEN"

    # staff (content_editor) → 403 for admin-only overview
    res2 = client.get("/api/v1/admin/overview", headers=_staff())
    assert res2.status_code == 403


def test_admin_button_masks_server_enforcement(client: TestClient) -> None:
    # A citizen cannot approve reviews even with the right URL.
    res = client.post("/api/v1/admin/reviews/not-a-uuid/decision", headers=_citizen())
    assert res.status_code == 403


def test_admin_overview(client: TestClient) -> None:
    res = client.get("/api/v1/admin/overview", headers=_admin())
    assert res.status_code == 200, res.text
    body = res.json()
    assert "stats" in body
    assert body["stats"]["schemeTotal"] >= 11  # seeded catalog


# ---------------------------------------------------------------------------
# Scheme lifecycle (create → submit → review → approve/publish)
# ---------------------------------------------------------------------------


def test_scheme_create_draft_and_list_admin(client: TestClient) -> None:
    payload = _scheme_payload("ADM-ALPHA", scheme_status="draft", eligibility_rules=_valid_rules())
    res = client.post("/api/v1/admin/schemes", json=payload, headers=_staff())
    assert res.status_code == 201, res.text
    assert res.json()["schemeStatus"] == "draft"

    listed = client.get("/api/v1/admin/schemes", params={"q": "ADM-ALPHA"}, headers=_admin())
    assert listed.status_code == 200, listed.text
    codes = [item["code"] for item in listed.json()["items"]]
    assert "ADM-ALPHA" in codes


def test_scheme_create_rejects_invalid_rules(client: TestClient) -> None:
    payload = _scheme_payload(
        "ADM-BADRULE",
        scheme_status="draft",
        eligibility_rules=[{"field": "nope_field", "operator": "eq", "value": "x"}],
    )
    res = client.post("/api/v1/admin/schemes", json=payload, headers=_staff())
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_scheme_publish_gate_blocks_missing_fields(client: TestClient) -> None:
    payload = _scheme_payload("ADM-GATE", scheme_status="draft", summary={"en": "", "native": ""})
    created = client.post("/api/v1/admin/schemes", json=payload, headers=_staff())
    assert created.status_code == 201
    code = created.json()["code"]

    # Go through the review pipeline so the scheme reaches "verified" first
    # (draft → published is not a valid transition).
    client.post(f"/api/v1/admin/schemes/{code}/submit-for-review", headers=_staff())
    queue = client.get("/api/v1/admin/reviews", headers=_admin())
    review_id = [r for r in queue.json()["items"] if r["schemeCode"] == code][0]["id"]
    approved = client.post(
        f"/api/v1/admin/reviews/{review_id}/decision",
        params={"approve": "true"},
        headers=_admin(),
    )
    assert approved.status_code == 200, approved.text

    res = client.patch(
        f"/api/v1/admin/schemes/{code}/status", params={"status": "published"}, headers=_admin()
    )
    assert res.status_code == 422
    assert "summary_en" in res.json()["error"]["message"]


def test_full_review_lifecycle(client: TestClient) -> None:
    payload = _scheme_payload("ADM-FLOW", scheme_status="draft", eligibility_rules=_valid_rules())
    created = client.post("/api/v1/admin/schemes", json=payload, headers=_staff())
    assert created.status_code == 201, created.text
    code = created.json()["code"]

    # 1. submit for review
    sub = client.post(f"/api/v1/admin/schemes/{code}/submit-for-review", headers=_staff())
    assert sub.status_code == 200, sub.text
    assert sub.json()["status"] == "pending"

    # 2. show up in the queue
    queue = client.get("/api/v1/admin/reviews", headers=_admin())
    assert queue.status_code == 200
    queued = [r for r in queue.json()["items"] if r["schemeCode"] == code]
    assert len(queued) == 1
    review_id = queued[0]["id"]

    # 3. reject first
    rejected = client.post(
        f"/api/v1/admin/reviews/{review_id}/decision",
        params={"approve": "false", "note": "needs more docs"},
        headers=_admin(),
    )
    assert rejected.status_code == 200
    assert rejected.json()["schemeStatus"] == "draft"  # rejected → back to from_status

    # 4. re-submit, then approve (→ verified)
    client.post(f"/api/v1/admin/schemes/{code}/submit-for-review", headers=_staff())
    queue2 = client.get("/api/v1/admin/reviews", headers=_admin())
    review_id2 = [r for r in queue2.json()["items"] if r["schemeCode"] == code][0]["id"]
    approved = client.post(
        f"/api/v1/admin/reviews/{review_id2}/decision",
        params={"approve": "true"},
        headers=_admin(),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["schemeStatus"] == "verified"

    # 5. admin publishes straight from verified
    published = client.patch(
        f"/api/v1/admin/schemes/{code}/status",
        params={"status": "published"},
        headers=_admin(),
    )
    assert published.status_code == 200, published.text
    assert published.json()["schemeStatus"] == "published"

    # 6. archive so the published catalog stays as-seeded for other tests
    archived = client.patch(
        f"/api/v1/admin/schemes/{code}/status", params={"status": "archived"}, headers=_admin()
    )
    assert archived.status_code == 200, archived.text


def test_review_approve_requires_admin(client: TestClient) -> None:
    payload = _scheme_payload("ADM-NOAUTHUSER", scheme_status="draft")
    created = client.post("/api/v1/admin/schemes", json=payload, headers=_staff())
    assert created.status_code == 201, created.text
    code = created.json()["code"]
    client.post(f"/api/v1/admin/schemes/{code}/submit-for-review", headers=_staff())

    queue = client.get("/api/v1/admin/reviews", headers=_admin())
    review_id = [r for r in queue.json()["items"] if r["schemeCode"] == code][0]["id"]

    # content_editor cannot approve (admin-only)
    res = client.post(
        f"/api/v1/admin/reviews/{review_id}/decision",
        params={"approve": "true"},
        headers=_staff(),
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Versions + audit
# ---------------------------------------------------------------------------


def test_scheme_versions_and_audit(client: TestClient) -> None:
    payload = _scheme_payload("ADM-VER", scheme_status="draft")
    created = client.post("/api/v1/admin/schemes", json=payload, headers=_staff())
    assert created.status_code == 201, created.text
    code = created.json()["code"]

    versions = client.get(f"/api/v1/admin/schemes/{code}/versions", headers=_admin())
    assert versions.status_code == 200
    assert len(versions.json()) == 1

    updated = client.put(
        f"/api/v1/admin/schemes/{code}",
        json={"benefits": ["Stipend"], "name": {"en": "Scheme ADM-VER", "native": ""}},
        headers=_staff(),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["benefits"] == ["Stipend"]

    versions2 = client.get(f"/api/v1/admin/schemes/{code}/versions", headers=_admin())
    assert len(versions2.json()) == 2
    assert versions2.json()[0]["changes"]

    audit = client.get("/api/v1/admin/audit-logs", headers=_admin())
    assert audit.status_code == 200
    assert any(log["entityCode"] == code for log in audit.json()["items"])


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


def test_duplicate_detection(client: TestClient) -> None:
    client.post("/api/v1/admin/schemes", json=_scheme_payload("ADM-DUP"), headers=_staff())
    # same normalized name, different code
    dup = _scheme_payload("ADM-DUP2")
    dup["name"] = {"en": "scheme ADM-DUP", "native": ""}
    created = client.post("/api/v1/admin/schemes", json=dup, headers=_staff())
    assert created.status_code == 201, created.text

    detail = client.get("/api/v1/admin/schemes/ADM-DUP2/detail", headers=_admin())
    assert detail.status_code == 200, detail.text
    assert "ADM-DUP" in detail.json()["duplicateIds"] or detail.json()["duplicateIds"] != []


# ---------------------------------------------------------------------------
# Bulk import
# ---------------------------------------------------------------------------


def test_import_preview_and_apply(client: TestClient) -> None:
    payload = [
        {"code": "IMP-100", "name": "Import Scheme", "ministry": "Ministry of Import"},
        {"code": "BAD", "name": "no ministry"},
    ]
    import json

    preview = client.post(
        "/api/v1/admin/import/preview",
        params={"payload": json.dumps(payload)},
        headers=_staff(),
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["totalRows"] == 2
    assert body["validRows"] == 1
    assert body["invalidRows"] == 1

    applied = client.post(
        "/api/v1/admin/import/apply",
        params={"payload": json.dumps([payload[0]])},
        headers=_staff(),
    )
    assert applied.status_code == 200, applied.text
    a = applied.json()
    assert a["importedRows"] == 1
    assert a["failedRows"] == 0

    jobs = client.get("/api/v1/admin/import/jobs", headers=_admin())
    assert jobs.status_code == 200
    assert jobs.json()["items"]


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


def test_feedback_submission_and_admin_flow(client: TestClient) -> None:
    # Citizen submits feedback.
    fb = client.post(
        "/api/v1/admin/feedback",
        json={
            "rating": 4,
            "category": "content",
            "comment": "Great scheme info.",
            "language": "en",
            "schemeCode": "PM-KISAN",
        },
        headers=_citizen(),
    )
    assert fb.status_code == 200, fb.text
    fb_id = fb.json()["id"]

    listed = client.get("/api/v1/admin/feedback", headers=_admin())
    assert listed.status_code == 200
    items = [i for i in listed.json()["items"] if i["id"] == fb_id]
    assert len(items) == 1
    assert items[0]["rating"] == 4

    resolved = client.patch(
        f"/api/v1/admin/feedback/{fb_id}", params={"status": "resolved"}, headers=_admin()
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def test_users_management(client: TestClient) -> None:
    # ensure a few users exist
    client.get("/api/v1/auth/me", headers=_citizen())
    client.get("/api/v1/auth/me", headers=_staff())

    listed = client.get("/api/v1/admin/users", headers=_admin())
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["total"] >= 3

    # Promote citizen-1 to content_editor
    citizen_uid = "citizen-api-1"
    user_row = next(u for u in body["items"] if u.get("firebaseUid") == citizen_uid)
    updated = client.put(
        f"/api/v1/admin/users/{user_row['id']}/role",
        params={"role": "content_editor"},
        headers=_admin(),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["role"] == "content_editor"

    suspended = client.put(
        f"/api/v1/admin/users/{user_row['id']}/status",
        params={"status": "suspended"},
        headers=_admin(),
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"


def test_users_admin_requires_admin(client: TestClient) -> None:
    res = client.get("/api/v1/admin/users", headers=_staff())
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_probe(client: TestClient) -> None:
    res = client.get("/api/v1/admin/health", headers=_admin())
    assert res.status_code == 200, res.text
    body = res.json()
    assert "checks" in body
    assert "overall" in body
    components = {c["component"] for c in body["checks"]}
    assert "database" in components
    assert "ai" in components
