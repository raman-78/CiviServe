"""Geocoding service for manual-location anchors.

The app never relies on the map being on as the only path: a citizen can pick a
state / district / city / PIN. This service resolves such a manual anchor to an
approximate WGS84 point so the nearby scan can rank by distance. Approximate
points are labelled as such and never sent to a third party.

The provider swap for Nominatim/OSM or Google Geocoding keeps the same
``resolve()`` interface (docs/architecture/17 §Maps). The built-in table only
covers the seeded states; unknowns fall back to ``approximate=True`` centroids
derived from the matching catalog rows when possible.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.center import ServiceCentre

#: Approximate state centroids (lat, lng) for the seeded states. Not a precise
#: geocoder; used only to turn a ``state`` anchor into a scorable point.
_STATE_CENTROIDS: dict[str, tuple[float, float]] = {
    "AP": (15.9, 79.9),
    "KA": (15.0, 76.0),
    "TN": (11.1, 78.6),
    "UP": (26.8, 80.9),
    "WB": (24.0, 88.7),
    "MH": (19.6, 76.3),
    "DL": (28.6, 77.2),
    "GJ": (22.7, 71.6),
    "RJ": (26.6, 74.2),
    "KL": (10.2, 76.5),
    "TS": (17.5, 79.0),
    "PB": (30.8, 75.8),
    "HR": (29.0, 76.1),
    "OD": (20.5, 84.7),
    "CG": (21.5, 82.0),
    "JH": (23.5, 86.5),
}


@dataclass(frozen=True)
class ResolvedPlace:
    """A manual anchor reduced to a scannable point (approximate if derived)."""

    lat: float | None
    lng: float | None
    place_name: str
    kind: str
    approximate: bool


def _centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    if not points:
        raise ValueError("no points to centroid")
    avg_lat = sum(p[0] for p in points) / len(points)
    avg_lng = sum(p[1] for p in points) / len(points)
    return avg_lat, avg_lng


class GeocodingService:
    """Resolves manual location anchors to scan points (offline fallback)."""

    def __init__(self) -> None:
        self._state_centroids = _STATE_CENTROIDS

    def state_point(self, state_code: str) -> tuple[float, float] | None:
        return self._state_centroids.get(state_code.upper())

    def resolve_state(
        self,
        *,
        state_code: str,
        district: str | None = None,
        city: str | None = None,
        matches: list[ServiceCentre] | None = None,
    ) -> ResolvedPlace:
        """Resolve a state/district/city anchor, preferring match-derived points.

        ``matches`` are the catalog rows already narrowed by the manual search;
        when present their mean coordinate is the most representative anchor for
        the neighbourhood. Otherwise we fall back to the state centroid.
        """
        matches = matches or []
        named_parts = [district or city, state_code.upper()]
        place_name = ", ".join(p for p in named_parts if p)

        if matches:
            pts = [(m.lat, m.lng) for m in matches if m.lat and m.lng]
            if pts:
                lat, lng = _centroid(pts)
                return ResolvedPlace(
                    lat=lat,
                    lng=lng,
                    place_name=place_name or state_code.upper(),
                    kind="district",
                    approximate=True,
                )
        state_pt = self.state_point(state_code)
        if state_pt is None:
            return ResolvedPlace(
                lat=None,
                lng=None,
                place_name=place_name or state_code.upper(),
                kind="state",
                approximate=True,
            )
        return ResolvedPlace(
            lat=state_pt[0],
            lng=state_pt[1],
            place_name=place_name or state_code.upper(),
            kind="state",
            approximate=True,
        )


__all__ = ["GeocodingService", "ResolvedPlace", "_centroid"]
