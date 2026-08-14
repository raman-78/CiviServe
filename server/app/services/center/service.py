"""Centre orchestration (maps/locator prompt): DTO mapping + scan envelopes."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.center import ServiceCentre
from app.schemas.center import (
    CentreAttributionOut,
    ManualSearchOut,
    NearbyCentresOut,
    ServiceCentreOut,
)
from app.services.center.maps import MapProviderService
from app.services.center.search import CenterSearchService


class CenterService:
    """Converts catalog rows to API DTOs and runs the two scans."""

    def __init__(self, session: AsyncSession) -> None:
        self.search = CenterSearchService(session)
        self.maps = MapProviderService()

    # -- DTO ----------------------------------------------------------------

    def to_out(
        self,
        centre: ServiceCentre,
        distance_km: float | None = None,
    ) -> ServiceCentreOut:
        return ServiceCentreOut(
            id=str(centre.id),
            type=centre.centre_type,
            name=centre.name,
            state_code=centre.state_code,
            district=centre.district,
            pincode=centre.pincode,
            address=centre.address,
            lat=centre.lat,
            lng=centre.lng,
            services=centre.services or [],
            timings=centre.timings,
            phone=centre.phone,
            languages=centre.languages or [],
            verified=bool(centre.verified),
            distanceKm=distance_km,
            attribution=CentreAttributionOut(
                source_name=_source_label(centre.source),
                source_url=centre.source_url,
                last_verified_at=centre.last_verified_at,
            ),
        )

    async def nearby(
        self,
        *,
        lat: float,
        lng: float,
        radius_km: float,
        centre_type: str | None = None,
        limit: int = 10,
    ) -> NearbyCentresOut:
        scored = await self.search.nearby(
            lat=lat, lng=lng, radius_km=radius_km, centre_type=centre_type, limit=limit
        )
        return NearbyCentresOut(
            anchor={"lat": lat, "lng": lng},
            radiusKm=min(radius_km, 50.0),
            centers=[self.to_out(c, d) for c, d in scored],
            attributionNote=self.maps.attribution_note(),
        )

    async def manual(
        self,
        *,
        state_code: str | None = None,
        district: str | None = None,
        city: str | None = None,
        pincode: str | None = None,
        centre_type: str | None = None,
        limit: int = 10,
    ) -> ManualSearchOut:
        scored = await self.search.manual(
            state_code=state_code,
            district=district,
            city=city,
            pincode=pincode,
            centre_type=centre_type,
            limit=limit,
        )
        return ManualSearchOut(
            anchor=_anchor_dict(state_code, district, city, pincode),
            centers=[self.to_out(c, d) for c, d in scored],
            attributionNote=self.maps.attribution_note(),
            pincodeResolved=bool(pincode),
        )

    async def detail(
        self, centre_id: str, *, origin_lat: float | None = None, origin_lng: float | None = None
    ) -> dict[str, Any]:
        centre = await self.search.get_one(centre_id)
        directions = None
        if origin_lat is not None and origin_lng is not None:
            directions = self.search.directions_for(
                origin_lat=origin_lat, origin_lng=origin_lng, centre=centre
            )
        return {
            "centre": self.to_out(centre),
            "directionsUrl": directions,
        }


def _source_label(source: str) -> str | None:
    labels = {
        "manual": "Manual entry",
        "import": "Bulk import",
        "api": "Official sync",
    }
    return labels.get(source)


def _anchor_dict(
    state_code: str | None,
    district: str | None,
    city: str | None,
    pincode: str | None,
) -> dict[str, Any]:
    anchor: dict[str, Any] = {}
    if state_code:
        anchor["stateCode"] = state_code
    if district:
        anchor["district"] = district
    if city:
        anchor["city"] = city
    if pincode:
        anchor["pincode"] = pincode
    return anchor


__all__ = ["CenterService"]
