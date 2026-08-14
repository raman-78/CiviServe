"""Centre search service (maps/locator prompt).

Runs the two scan shapes on top of the repository:

- ``nearby`` — real coordinates → bbox prefilter → haversine → radius clamp →
  sort (nearest default) → limit.
- ``manual`` — state / district / city / PIN filter over the catalog → resolve
  an anchor → rank by distance where a point exists, else name.

Neither path stores the anchor (privacy). Distances are returned as ``km`` and
never fabricated; centres with no available detail are returned as-is with
``available: false`` so the UI shows "Information not available" instead of
inventing phone/timings/services.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError_
from app.models.center import ServiceCentre
from app.repositories.center_repo import CenterRepository
from app.services.center.distance import haversine_km
from app.services.center.location import LocationService
from app.services.center.maps import MapProviderService

#: Radius presets mirrored from shared (km). Anything else is rejected.
_RADIUS_PRESETS = (5, 10, 25, 50)
_MAX_LIMIT = 20
_DEFAULT_LIMIT = 10
_DEFAULT_RADIUS = 10

#: centre → distance in km, or None when the anchor lacks coordinates.
ScoredCentre = tuple[ServiceCentre, float | None]


class CenterSearchService:
    """Nearby + manual scans; no HTTP awareness."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = CenterRepository(session)
        self.location = LocationService()
        self.maps = MapProviderService()

    async def nearby(
        self,
        *,
        lat: float,
        lng: float,
        radius_km: float,
        centre_type: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[ScoredCentre]:
        """Centres within ``radius_km`` of (lat, lng), nearest first."""
        anchor = self.location.gps_anchor(lat=lat, lng=lng)
        radius = self._clamp_radius(radius_km)
        lat_min, lat_max, lng_min, lng_max = self.location.bbox(
            lat=anchor.lat or lat,
            lng=anchor.lng or lng,
            radius_km=radius,
        )
        candidates = await self.repo.within_bbox(
            lat_min=lat_min, lat_max=lat_max, lng_min=lng_min, lng_max=lng_max
        )
        origin_lat, origin_lng = anchor.lat or lat, anchor.lng or lng
        scored: list[ScoredCentre] = []
        for centre in candidates:
            if centre_type and centre.centre_type != centre_type:
                continue
            if not centre.lat or not centre.lng:
                scored.append((centre, None))
                continue
            distance = haversine_km(origin_lat, origin_lng, centre.lat, centre.lng)
            if distance > radius:
                continue
            scored.append((centre, distance))
        scored.sort(
            key=lambda item: (item[1] is None, item[1] if item[1] is not None else float("inf"))
        )
        return scored[: self._clamp_limit(limit)]

    async def manual(
        self,
        *,
        state_code: str | None = None,
        district: str | None = None,
        city: str | None = None,
        pincode: str | None = None,
        centre_type: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[ScoredCentre]:
        """Manual-location search. Pincode path uses the PIN prefix fallback."""
        if pincode:
            anchor = self.location.pincode_anchor(pincode)
            matches = await self.repo.search_manual(
                state_code=state_code,
                district=district,
                city=city,
                pincode=pincode,
                centre_type=centre_type,
            )
        else:
            matches = await self.repo.search_manual(
                state_code=state_code,
                district=district,
                city=city,
                pincode=None,
                centre_type=centre_type,
            )
            anchor = self.location.resolve_manual(
                state_code=state_code, district=district, city=city, matches=list(matches)
            )
        scored: list[ScoredCentre] = []
        for centre in matches:  # type: ignore[union-attr]
            distance = None
            if anchor.has_coords and centre.lat and centre.lng:
                distance = haversine_km(anchor.lat, anchor.lng, centre.lat, centre.lng)  # type: ignore[arg-type]
            scored.append((centre, distance))
        scored.sort(
            key=lambda item: (
                item[1] is None,
                item[1] if item[1] is not None else float("inf"),
                item[0].name,
            )
        )
        return scored[: self._clamp_limit(limit)]

    async def get_one(self, centre_id: str) -> ServiceCentre:
        from uuid import UUID

        try:
            UUID(centre_id)
        except ValueError as exc:
            raise ValidationError_("Invalid centre id.", code="CENTRE_INVALID_ID") from exc
        centre = await self.repo.get_public(centre_id)
        if centre is None:
            raise NotFoundError("Centre not found.")
        return centre

    def directions_for(
        self,
        *,
        origin_lat: float,
        origin_lng: float,
        centre: ServiceCentre,
    ) -> str:
        return self.maps.directions_url(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=centre.lat,
            dest_lng=centre.lng,
        )

    @staticmethod
    def _clamp_radius(radius_km: float) -> float:
        if radius_km <= 0:
            raise ValidationError_(
                "Search radius must be positive.", code="LOCATION_INVALID_RADIUS"
            )
        return min(radius_km, max(_RADIUS_PRESETS))

    @staticmethod
    def _clamp_limit(limit: int) -> int:
        return max(1, min(limit, _MAX_LIMIT))


__all__ = ["CenterSearchService", "ScoredCentre"]
