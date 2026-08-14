"""Service-centre persistence (maps/locator prompt).

The catalog is public by design (no user scoping). The repository stays a thin
layer; distance ranking lives in the center service (haversine in Python) so
SQLite tests and Postgres prod share the same semantics with a GiST
``ST_DWithin`` swap-in for Postgres later.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import func, or_, select

from app.models.center import ServiceCentre
from app.repositories.base import BaseRepository


class CenterRepository(BaseRepository[ServiceCentre]):
    model = ServiceCentre

    async def list_by_state(self, state_code: str) -> list[ServiceCentre]:
        stmt = select(ServiceCentre).where(
            ServiceCentre.state_code == state_code, ServiceCentre.active.is_(True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_manual(
        self,
        *,
        state_code: str | None = None,
        district: str | None = None,
        city: str | None = None,
        pincode: str | None = None,
        centre_type: str | None = None,
    ) -> list[ServiceCentre]:
        """Match by any combination of manual-location fields (all optional)."""
        stmt = select(ServiceCentre).where(ServiceCentre.active.is_(True))
        if state_code:
            stmt = stmt.where(ServiceCentre.state_code == state_code.upper())
        if district:
            stmt = stmt.where(func.lower(ServiceCentre.district) == district.strip().lower())
        if city:
            stmt = stmt.where(
                or_(
                    func.lower(ServiceCentre.district) == city.strip().lower(),
                    ServiceCentre.name.ilike(f"%{city.strip()}%"),
                )
            )
        if pincode:
            stmt = stmt.where(ServiceCentre.pincode == pincode.strip())
        if centre_type:
            stmt = stmt.where(ServiceCentre.centre_type == centre_type)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_public(self, centre_id: Any) -> ServiceCentre | None:
        if isinstance(centre_id, str):
            centre_id = _uuid.UUID(centre_id)
        stmt = select(ServiceCentre).where(
            ServiceCentre.id == centre_id, ServiceCentre.active.is_(True)
        )
        return await self._scalar_one(stmt)

    # -- Nearby-scan primitives ---------------------------------------------

    async def within_bbox(
        self, *, lat_min: float, lat_max: float, lng_min: float, lng_max: float
    ) -> Iterable[ServiceCentre]:
        """Coarse bounding box prefilter, then haversine precision in Python."""
        stmt = (
            select(ServiceCentre)
            .where(
                ServiceCentre.active.is_(True),
                ServiceCentre.lat >= lat_min,
                ServiceCentre.lat <= lat_max,
                ServiceCentre.lng >= lng_min,
                ServiceCentre.lng <= lng_max,
            )
            .order_by(ServiceCentre.name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


__all__ = ["CenterRepository"]
