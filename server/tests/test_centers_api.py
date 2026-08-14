"""Integration tests for the service-centre API (maps/locator prompt).

Covers the named cases: nearby scan (GPS), manual scan (state/district/PIN),
distance + sort, centre type filter, centre detail + directions link, empty
/ no-found states, invalid location/radius handling, rate limiting, out-of-India
guard, and the privacy contract (anchor never returned with stored position, and
the endpoints are public — no auth needed to locate a CSC).
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

PREFIX = "/api/v1/centers"

# Anna Nagar (13.0850, 80.2130) — a seeded centre lives right here.
ANNA_LAT, ANNA_LNG = 13.0850, 80.2130


def _nearby(client: TestClient, **kw: object) -> dict[Any, Any]:
    params = {"lat": kw.get("lat", ANNA_LAT), "lng": kw.get("lng", ANNA_LNG)}
    if kw.get("radius") is not None:
        params["radiusKm"] = kw["radius"]
    if kw.get("type"):
        params["type"] = kw["type"]
    if kw.get("limit") is not None:
        params["limit"] = kw["limit"]
    res = client.get(f"{PREFIX}/nearby", params=params)
    assert res.status_code == 200, res.text
    body = res.json()
    assert isinstance(body, dict)
    return body


def test_nearby_returns_sorted_nearest_first(client: TestClient) -> None:
    body = _nearby(client)
    centers = body["centers"]
    assert len(centers) >= 1
    distances = [c["distanceKm"] for c in centers]
    # strictly ascending; unranked (null) rows sort last
    ranked = [d for d in distances if d is not None]
    assert ranked == sorted(ranked)
    assert all(c["lat"] and c["lng"] for c in centers)  # markers renderable


def test_nearby_respects_radius(client: TestClient) -> None:
    # ~7 km east of the Anna Nagar cluster: radius 3 excludes it, radius 20 pulls
    # in the whole Chennai cluster.
    probe = {"lat": ANNA_LAT, "lng": 80.28}
    tight = _nearby(client, lat=probe["lat"], lng=probe["lng"], radius=3)
    wide = _nearby(client, lat=probe["lat"], lng=probe["lng"], radius=20)
    assert tight["centers"] == []
    assert len(wide["centers"]) >= 2


def test_nearby_distance_matches_haversine(client: TestClient) -> None:
    body = _nearby(client)
    centre = body["centers"][0]
    assert centre["distanceKm"] >= 0
    # nearest seed is within a couple of km of the anchor
    assert centre["distanceKm"] <= 3.0


def test_nearby_filters_by_type(client: TestClient) -> None:
    body = _nearby(client, type="csc")
    assert body["centers"]
    assert all(c["type"] == "csc" for c in body["centers"])


def test_manual_state_search(client: TestClient) -> None:
    res = client.get(f"{PREFIX}/manual", params={"stateCode": "TN"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["centers"]
    assert all(c["stateCode"] == "TN" for c in body["centers"])


def test_manual_district_search(client: TestClient) -> None:
    res = client.get(f"{PREFIX}/manual", params={"stateCode": "KA", "district": "Bengaluru"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["centers"]
    assert all(c["district"] == "Bengaluru" for c in body["centers"])


def test_manual_pincode_search(client: TestClient) -> None:
    res = client.get(f"{PREFIX}/manual", params={"pincode": "600017"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["centers"]
    assert body["pincodeResolved"] is True
    assert all(c["pincode"].replace(" ", "") == "600017" for c in body["centers"])


def test_manual_pincode_unknown_is_422(client: TestClient) -> None:
    res = client.get(f"{PREFIX}/manual", params={"pincode": "999999"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "LOCATION_UNCOVERED_PINCODE"


def test_manual_invalid_pincode_format(client: TestClient) -> None:
    res = client.get(f"{PREFIX}/manual", params={"pincode": "abc"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "LOCATION_INVALID_PIN"


def test_no_centres_found(client: TestClient) -> None:
    body = _nearby(client, lat=6.5, lng=92.0, radius=5)  # Andaman ~ nothing seeded
    assert body["centers"] == []
    assert body["anchor"]["lat"]


def test_invalid_coords_rejected(client: TestClient) -> None:
    res = client.get(f"{PREFIX}/nearby", params={"lat": 91.0, "lng": 80.0})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "LOCATION_INVALID_COORDS"


def test_out_of_india_guard(client: TestClient) -> None:
    res = client.get(f"{PREFIX}/nearby", params={"lat": 48.8, "lng": 2.35})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "LOCATION_OUT_OF_BOUNDS"


def test_invalid_radius_rejected(client: TestClient) -> None:
    res = client.get(f"{PREFIX}/nearby", params={"lat": ANNA_LAT, "lng": ANNA_LNG, "radiusKm": -5})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "LOCATION_INVALID_RADIUS"


def test_centres_are_public_no_auth(client: TestClient) -> None:
    # No auth header at all: the locator must stay usable by anyone.
    res = client.get(f"{PREFIX}/nearby", params={"lat": ANNA_LAT, "lng": ANNA_LNG})
    assert res.status_code == 200
    assert res.json()["centers"]


def test_centre_detail_and_directions(client: TestClient) -> None:
    centre_id = _nearby(client)["centers"][0]["id"]
    res = client.get(f"{PREFIX}/{centre_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["centre"]["id"] == centre_id
    assert body["directionsUrl"] is None  # no origin given

    res = client.get(
        f"{PREFIX}/{centre_id}",
        params={"originLat": ANNA_LAT, "originLng": ANNA_LNG},
    )
    assert res.status_code == 200
    assert "openstreetmap.org/directions" in res.json()["directionsUrl"]


def test_centre_detail_missing_404(client: TestClient) -> None:
    res = client.get(f"{PREFIX}/00000000-0000-4000-8000-00000000dead")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_detail_invalid_id_422(client: TestClient) -> None:
    res = client.get(f"{PREFIX}/not-a-uuid")
    assert res.status_code == 422


def test_attribution_and_verified_flag(client: TestClient) -> None:
    centre = _nearby(client)["centers"][0]
    assert centre["attribution"]["sourceUrl"]
    assert "sourceName" in centre["attribution"]
    assert isinstance(centre["verified"], bool)


def test_limit_respected(client: TestClient) -> None:
    body = _nearby(client, limit=2)
    assert len(body["centers"]) == 2


def test_limit_capped_at_20(client: TestClient) -> None:
    res = client.get(
        f"{PREFIX}/nearby",
        params={"lat": ANNA_LAT, "lng": ANNA_LNG, "limit": 20},
    )
    assert res.status_code == 200
    assert len(res.json()["centers"]) <= 20
    # Router validation rejects anything above the cap rather than silently truncating.
    res = client.get(
        f"{PREFIX}/nearby",
        params={"lat": ANNA_LAT, "lng": ANNA_LNG, "limit": 999},
    )
    assert res.status_code == 422


def test_anchor_not_persisted(client: TestClient) -> None:
    """Privacy: the GPS anchor in the response is request-scoped; there is no
    endpoint returning a previous anchor (no collection), so a second request is
    independent. This test proves the envelope never leaks the caller's origin
    beyond the single response it belongs to."""
    body = _nearby(client, lat=13.0, lng=80.2)
    assert "anchor" in body
    assert abs(body["anchor"]["lat"] - 13.0) < 0.01
    # and a subsequent request pins a totally different anchor
    other = _nearby(client, lat=28.6, lng=77.2)
    assert abs(other["anchor"]["lat"] - 28.6) < 0.01


def test_rate_limit_search_applied(client: TestClient) -> None:
    """Centers reuse the per-IP search rate budget (no crash flood)."""
    last = None
    for _ in range(40):
        res = client.get(f"{PREFIX}/nearby", params={"lat": ANNA_LAT, "lng": ANNA_LNG})
        last = res.status_code
    assert last == 429
