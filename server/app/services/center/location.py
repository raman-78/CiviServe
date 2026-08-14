"""Location service: GPS anchor validation + manual-anchor resolution.

Maintains the locator's privacy contract: the GPS point from the browser is used
for one nearby scan, never stored, never logged, never sent to a third party;
manual anchors (state / district / city / PIN) are resolved to the same scan
and are always labelled approximate. The service computes distances and ranks;
it never retains an anchor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.core.errors import ValidationError_
from app.services.center.geocode import GeocodingService

#: Rough India bounding box — keeps the locator relevant and prevents nonsense
#: coords from running scans hundreds of km away.
_INDIA = (6.0, 37.0, 68.0, 98.0)
#: Coarse PIN-prefix → approximate point (offline fallback, labelled approx).
#: PINs not present here fall back to state search with a clear PRIN message.
_INDIA_PREFIX_POINTS: dict[str, tuple[float, float]] = {
    "11": (28.6, 77.1),  # Delhi region
    "20": (27.2, 78.0),  # UP west
    "40": (19.0, 72.8),  # Maharashtra
    "50": (17.3, 78.4),  # Telangana
    "60": (13.0, 80.2),  # Tamil Nadu
    "70": (22.5, 88.3),  # West Bengal
}


@dataclass(frozen=True)
class ResolvedAnchor:
    """Normalised scan origin (either real GPS or an approximation)."""

    lat: float | None
    lng: float | None
    place_name: str
    approximate: bool

    @property
    def has_coords(self) -> bool:
        return self.lat is not None and self.lng is not None


class LocationService:
    """Resolves anchors and bounds the scan range."""

    def __init__(self) -> None:
        self.geocoder = GeocodingService()

    def validate_coords(self, lat: float, lng: float) -> None:
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise ValidationError_("Invalid coordinates.", code="LOCATION_INVALID_COORDS")
        if not (_INDIA[0] <= lat <= _INDIA[1] and _INDIA[2] <= lng <= _INDIA[3]):
            raise ValidationError_(
                "This helper works within India. Please choose a location inside India.",
                code="LOCATION_OUT_OF_BOUNDS",
            )

    def gps_anchor(self, *, lat: float, lng: float) -> ResolvedAnchor:
        self.validate_coords(lat, lng)
        return ResolvedAnchor(
            lat=lat, lng=lng, place_name="Your current location", approximate=False
        )

    def pincode_anchor(self, pincode: str) -> ResolvedAnchor:
        if not pincode.isdigit() or len(pincode) != 6:
            raise ValidationError_(
                "Please enter a valid 6-digit PIN code.", code="LOCATION_INVALID_PIN"
            )
        point = _prefix_point(pincode)
        if point is None:
            raise ValidationError_(
                "This PIN code is not covered yet. Try state or district search instead.",
                code="LOCATION_UNCOVERED_PINCODE",
            )
        lat, lng = point
        return ResolvedAnchor(lat=lat, lng=lng, place_name=f"PIN {pincode}", approximate=True)

    def resolve_manual(
        self,
        *,
        state_code: str | None = None,
        district: str | None = None,
        city: str | None = None,
        matches: list | None = None,
    ) -> ResolvedAnchor:
        """Resolve a state/district/city anchor, using the narrowed catalog rows
        to derive a representative (approximate) point when possible."""
        resolved = self.geocoder.resolve_state(
            state_code=state_code or "",
            district=district or city,
            city=city,
            matches=matches or [],
        )
        return ResolvedAnchor(
            lat=resolved.lat,
            lng=resolved.lng,
            place_name=resolved.place_name,
            approximate=resolved.approximate,
        )

    def bbox(
        self, *, lat: float, lng: float, radius_km: float
    ) -> tuple[float, float, float, float]:
        """Approximate lat/lng box for a radius (labels the bbox prefilter)."""
        delta_lat = radius_km / 111.0
        delta_lng = radius_km / (111.0 * _cos_lat(lat))
        return lat - delta_lat, lat + delta_lat, lng - delta_lng, lng + delta_lng


def _cos_lat(lat: float) -> float:
    return max(math.cos(math.radians(lat)), 0.01)


def _prefix_point(pincode: str) -> tuple[float, float] | None:
    return _INDIA_PREFIX_POINTS.get(pincode[:2])


__all__ = ["LocationService", "ResolvedAnchor"]

# ruff: noqa: E501
