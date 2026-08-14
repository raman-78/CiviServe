"""Distance calculation for nearby-centre queries.

Haversine over WGS84 doubles. Postgres prod swaps the bbox scan for a GiST
``ST_DWithin`` (docs/database/06 §Geo); this module keeps one portable haversine
so tests and prod agree on the returned ``distanceKm``.
"""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres between two WGS84 points."""
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def format_distance_km(km: float) -> str:
    """Distance label: meters below 1 km, else km with one decimal."""
    if km < 1:
        meters = int(round(km * 1000))
        return f"{meters} m"
    return f"{km:.1f} km"


__all__ = ["EARTH_RADIUS_KM", "format_distance_km", "haversine_km"]
