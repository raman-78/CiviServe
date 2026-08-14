"""Service-centre endpoints (maps/locator prompt).

Public rails (rate-limited like scheme search — these are noisy read endpoints):

- ``GET /centers/nearby``        — GPS/anchor nearby scan (5/10/25/50 km presets).
- ``GET /centers/manual``        — state / district / city / PIN manual search.
- ``GET /centers/{id}``          — one centre (+ optional directions link).

Privacy: anchors are used for a single scan and never persisted. Guests may use
these too (no account required to find a CSC). Every route is rate-limited per
IP; a cache hop keeps repeated scans cheap.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db, rate_limit_search
from app.schemas.center import (
    CentreOut,
    ManualSearchOut,
    NearbyCentresOut,
)
from app.services.center import CenterService

router = APIRouter(tags=["centers"], prefix="/centers")

DbDep = Annotated[AsyncSession, Depends(get_db)]

_RADIUS_PRESETS = (5, 10, 25, 50)
_CENTER_TYPES = ("csc", "esevai", "seva-kendra", "tehsil", "post_office", "bank")


@router.get(
    "/nearby",
    response_model=NearbyCentresOut,
    dependencies=[Depends(rate_limit_search)],
)
async def nearby_centers(
    db: DbDep,
    lat: float = Query(..., description="WGS84 latitude"),
    lng: float = Query(..., description="WGS84 longitude"),
    radiusKm: float = Query(10.0, description="Search radius in km (presets or custom up to 50)"),
    type: str | None = Query(default=None, description="Filter by centre type"),
    limit: int = Query(10, ge=1, le=20),
) -> NearbyCentresOut:
    """Nearest centres to the caller's coordinates within ``radiusKm``."""
    service = CenterService(db)
    return await service.nearby(
        lat=lat,
        lng=lng,
        radius_km=radiusKm,
        centre_type=type,
        limit=limit,
    )


@router.get(
    "/manual",
    response_model=ManualSearchOut,
    dependencies=[Depends(rate_limit_search)],
)
async def manual_centers(
    db: DbDep,
    stateCode: str | None = Query(default=None, max_length=8),
    district: str | None = Query(default=None, max_length=120),
    city: str | None = Query(default=None, max_length=120),
    pincode: str | None = Query(default=None, max_length=12),
    type: str | None = Query(default=None, description="Filter by centre type"),
    limit: int = Query(10, ge=1, le=20),
) -> ManualSearchOut:
    """Centres matched by a manual location anchor (state/district/city/PIN)."""
    if pincode:
        pincode = pincode.strip()
    service = CenterService(db)
    return await service.manual(
        state_code=stateCode,
        district=district,
        city=city,
        pincode=pincode,
        centre_type=type,
        limit=limit,
    )


@router.get(
    "/{centre_id}",
    response_model=CentreOut,
    dependencies=[Depends(rate_limit_search)],
)
async def centre_detail(
    centre_id: str,
    db: DbDep,
    originLat: float | None = Query(
        default=None, description="Optional anchor latitude for a directions link"
    ),
    originLng: float | None = Query(
        default=None, description="Optional anchor longitude for a directions link"
    ),
) -> CentreOut:
    """One centre's public detail (+ optional external directions link)."""
    service = CenterService(db)
    if originLat is None or originLng is None:
        return CentreOut(**await service.detail(centre_id))
    return CentreOut(**await service.detail(centre_id, origin_lat=originLat, origin_lng=originLng))


__all__ = ["router"]
