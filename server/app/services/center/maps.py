"""Map provider service (maps/locator prompt).

Builds *directions links* (forwarding to an external map app) and keeps the
tile/provider choice behind one interface (docs/architecture/17 §Maps). The
app never renders its own turn-by-turn navigation; it only opens a browser-based
directions URL so the user retains control (and their precise location is never
sent to us or to any third party for this step).

Providers: ``osm`` (OpenStreetMap / OSRM) and ``google``.
"""

from __future__ import annotations

from typing import Literal

from app.core.config import get_settings

MapProvider = Literal["osm", "google"]

_GOOGLE_DIRECTIONS = "https://www.google.com/maps/dir/?api=1"
_OSM_DIRECTIONS = "https://www.openstreetmap.org/directions"


class MapProviderService:
    """Builds provider-specific directions URLs."""

    def __init__(self, provider: MapProvider | None = None) -> None:
        self.provider = provider or (get_settings().maps_provider or "osm")

    def directions_url(
        self, *, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
    ) -> str:
        """External directions link from the caller's anchor to a centre."""
        if self.provider == "google":
            return (
                f"{_GOOGLE_DIRECTIONS}&origin={origin_lat},{origin_lng}"
                f"&destination={dest_lat},{dest_lng}&travelmode=driving"
            )
        return f"{_OSM_DIRECTIONS}?from={origin_lat},{origin_lng}&to={dest_lat},{dest_lng}"

    def attribution_note(self) -> str:
        """UI footnote separating map data from official scheme information."""
        if self.provider == "google":
            return "Map data (c) Google. Centre details from official sources where marked."
        return (
            "Map data (c) OpenStreetMap contributors. "
            "Centre details from official sources where marked."
        )


__all__ = ["MapProviderService"]
