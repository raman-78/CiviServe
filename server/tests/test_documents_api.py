"""Integration tests for the document pipeline API (Prompt 11).

Covers the upload → OCR → detection → confirm → review → readiness workflow,
owner-scoping/security (guests rejected, cross-user isolation), the catalog,
and replace/delete. Uses a real temp dir storage; the app is seeded by the
TestClient lifespan.
"""

from __future__ import annotations

import io
from typing import Any, cast

from fastapi.testclient import TestClient

PREFIX = "/api/v1/documents"


def _png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64 + b"\xff" * 16


def _upload_kwargs(
    data: bytes | None = None,
    *,
    filename: str = "doc.png",
    content_type: str = "image/png",
    scheme: str | None = None,
    required_name: str | None = None,
) -> dict:
    files = {
        "file": (
            filename,
            io.BytesIO(data if data is not None else _png_bytes()),
            content_type,
        )
    }
    form: dict[str, str] = {}
    if scheme:
        form["scheme_code"] = scheme
    if required_name:
        form["required_name"] = required_name
    return {"files": files, "data": form}


def _create(
    client: TestClient,
    headers: dict[str, str],
    *,
    filename: str = "doc.png",
    content_type: str = "image/png",
    scheme: str | None = None,
    required_name: str | None = None,
) -> dict[str, Any]:
    kwargs = _upload_kwargs(
        filename=filename,
        content_type=content_type,
        scheme=scheme,
        required_name=required_name,
    )
    res = client.post(f"{PREFIX}/upload", headers=headers, **kwargs)  # type: ignore[arg-type]
    assert res.status_code == 200, res.text
    body = cast("dict[str, Any]", res.json())
    return cast("dict[str, Any]", body["document"])


def test_upload_and_ocr_flow(client: TestClient, auth_headers: dict[str, str]) -> None:
    upload = _create(client, auth_headers, filename="aadhaar.png")
    assert upload["status"] == "uploaded"
    assert upload["fileName"] == "aadhaar.png"
    assert upload["ocrConfidence"] is None
    assert upload["extractedFields"] == []

    ocr_text = (
        "Government of India Unique Identification Authority of India\n"
        "Aadhaar number 4123 4567 8901\nDate of Birth 15/08/1995  Female"
    )
    res = client.post(f"{PREFIX}/{upload['id']}/ocr", json={"text": ocr_text}, headers=auth_headers)
    assert res.status_code == 200, res.text
    ocr = res.json()
    assert ocr["detectedType"] == "AADHAAR"
    assert ocr["ocrConfidence"] == "high"
    assert {"aadhaar_no", "date_of_birth"} <= {f["key"] for f in ocr["extractedFields"]}
    # masked display value hides most of the number
    masked_aadhaar = next(f["masked"] for f in ocr["extractedFields"] if f["key"] == "aadhaar_no")
    assert masked_aadhaar and "8901" in masked_aadhaar

    res = client.get(f"{PREFIX}/{upload['id']}", headers=auth_headers)
    assert res.status_code == 200
    detail = res.json()
    assert detail["status"] == "processed"
    assert detail["detectedType"] == "AADHAAR"
    assert detail["detectionConfidence"] > 0


def test_upload_rejects_bad_extension(client: TestClient, auth_headers: dict[str, str]) -> None:
    res = client.post(
        f"{PREFIX}/upload",
        headers=auth_headers,
        files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
        data={},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "DOCUMENT_UNSUPPORTED_FORMAT"


def test_upload_rejects_empty_file(client: TestClient, auth_headers: dict[str, str]) -> None:
    res = client.post(
        f"{PREFIX}/upload",
        headers=auth_headers,
        files={"file": ("empty.png", io.BytesIO(b""), "image/png")},
        data={},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "DOCUMENT_EMPTY_FILE"


def test_documents_require_real_user(client: TestClient, guest_headers: dict[str, str]) -> None:
    res = client.get(PREFIX, headers=guest_headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_UNAUTHENTICATED"


def test_list_documents(client: TestClient, auth_headers: dict[str, str]) -> None:
    _create(client, auth_headers)
    res = client.get(PREFIX, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 1
    assert "url" not in res.json()["items"][0]  # private file never exposed


def test_catalog_lists_ocr_support(client: TestClient, auth_headers: dict[str, str]) -> None:
    res = client.get(f"{PREFIX}/catalog", headers=auth_headers)
    assert res.status_code == 200
    catalog = {c["code"]: c for c in res.json()}
    assert "AADHAAR" in catalog
    assert catalog["AADHAAR"]["ocrSupported"] is True
    assert catalog["AADHAAR"]["acceptedFormats"] == ["pdf", "jpg", "jpeg", "png"]


def test_readiness_precheck(client: TestClient, auth_headers: dict[str, str]) -> None:
    _create(client, auth_headers, scheme="PM-KISAN", required_name="AADHAAR")
    res = client.get(f"{PREFIX}/readiness/PM-KISAN", headers=auth_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["schemeCode"] == "PM-KISAN"
    assert body["disclaimer"]
    assert body["requiredCount"] > 0
    by_name = {item["required"]["name"]: item for item in body["items"]}
    assert by_name["AADHAAR"]["status"] == "uploaded"
    assert by_name["AADHAAR"]["isMissing"] is False
    assert by_name["LAND_RECORD"]["isMissing"] is True


def test_readiness_unknown_scheme_is_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    res = client.get(f"{PREFIX}/readiness/NOPE-999", headers=auth_headers)
    assert res.status_code == 404


def test_cross_user_isolation(client: TestClient, auth_headers: dict[str, str]) -> None:
    other_headers = {"X-Dev-User-Id": "other-user-999"}
    created = _create(client, auth_headers)
    res = client.get(f"{PREFIX}/{created['id']}", headers=other_headers)
    assert res.status_code == 404  # never leak another user's document


def test_other_user_cannot_download(client: TestClient, auth_headers: dict[str, str]) -> None:
    other_headers = {"X-Dev-User-Id": "other-user-998"}
    created = _create(client, auth_headers)
    res = client.get(f"{PREFIX}/{created['id']}/file", headers=other_headers)
    assert res.status_code == 404


def test_owner_can_download(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = _create(client, auth_headers)
    res = client.get(f"{PREFIX}/{created['id']}/file", headers=auth_headers)
    assert res.status_code == 200
    assert res.content.startswith(b"\x89PNG")


def test_confirm_type_manual(client: TestClient, auth_headers: dict[str, str]) -> None:
    upload = _create(client, auth_headers)
    res = client.post(
        f"{PREFIX}/{upload['id']}/confirm-type",
        json={"documentType": "VOTER_ID"},
        headers=auth_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["detectedType"] == "VOTER_ID"
    assert res.json()["status"] == "processed"

    bad = client.post(
        f"{PREFIX}/{upload['id']}/confirm-type",
        json={"documentType": "NOPE"},
        headers=auth_headers,
    )
    assert bad.status_code in (422, 404)


def test_replace_updates_file_and_metadata(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = _create(client, auth_headers, content_type="image/png", filename="card.png")
    doc_id = created["id"]
    replace = client.post(
        f"{PREFIX}/{doc_id}/replace",
        headers=auth_headers,
        files={"new_file": ("voter.png", io.BytesIO(_png_bytes()), "image/png")},
        data={},
    )
    assert replace.status_code == 200, replace.text
    assert replace.json()["fileName"] == "voter.png"
    assert replace.json()["status"] == "uploaded"


def test_delete_removes_document(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = _create(client, auth_headers)
    doc_id = created["id"]
    res = client.delete(f"{PREFIX}/{doc_id}", headers=auth_headers)
    assert res.status_code == 200
    assert client.get(f"{PREFIX}/{doc_id}", headers=auth_headers).status_code == 404


def test_review_corrects_extraction(client: TestClient, auth_headers: dict[str, str]) -> None:
    upload = _create(client, auth_headers)
    client.post(
        f"{PREFIX}/{upload['id']}/ocr",
        json={"text": "Permanent Account Number\nABCDE1234F\nIncome Tax Department"},
        headers=auth_headers,
    )
    res = client.post(
        f"{PREFIX}/{upload['id']}/review",
        json={
            "fields": [
                {"key": "pan_no", "label": "PAN Number", "value": "ABCDE1234F", "reliable": True},
                {"key": "full_name", "label": "Name", "value": "Priya Sharma", "reliable": True},
            ],
            "note": "Looks correct",
        },
        headers=auth_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "user_confirmed"
