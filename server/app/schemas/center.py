"""Service-centre API DTOs (maps/locator prompt).

All responses are camelCase via the shared ``APIModel``. Attribution fields let
the UI render "official source + last updated" and the "not every centre handles
every scheme" disclaimer separately from map/location data.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel


class CentreAttributionOut(APIModel):
    source_name: str | None = None
    source_url: str | None = None
    last_verified_at: datetime | None = None


class ServiceCentreOut(APIModel):
    """Public view of a service centre (map + official info separated)."""

    id: str
    type: str
    name: str
    state_code: str
    district: str | None = None
    pincode: str | None = None
    address: str
    lat: float
    lng: float
    services: list[str] = Field(default_factory=list)
    timings: str | None = None
    phone: str | None = None
    languages: list[str] = Field(default_factory=list)
    verified: bool = False
    distanceKm: float | None = None
    attribution: CentreAttributionOut | None = None


class NearbyCentresOut(APIModel):
    """Envelope for nearby/manual results."""

    anchor: dict = Field(default_factory=dict)
    radiusKm: float = 10.0
    centers: list[ServiceCentreOut] = Field(default_factory=list)
    attributionNote: str = ""


class ManualSearchOut(APIModel):
    """Envelope for a manual-location search."""

    anchor: dict = Field(default_factory=dict)
    centers: list[ServiceCentreOut] = Field(default_factory=list)
    attributionNote: str = ""
    pincodeResolved: bool = False


class CentreOut(APIModel):
    """One centre with an optional directions link computed for the anchor."""

    centre: ServiceCentreOut
    directionsUrl: str | None = None


__all__ = [
    "CentreAttributionOut",
    "CentreOut",
    "ManualSearchOut",
    "NearbyCentresOut",
    "ServiceCentreOut",
]
