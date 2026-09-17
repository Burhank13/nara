from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from app.models.location import Location

EARTH_RADIUS_M = 6_371_008.8


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres (haversine)."""
    phi1, phi2 = radians(lat1), radians(lat2)
    delta_phi = phi2 - phi1
    delta_lambda = radians(lng2 - lng1)

    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


@dataclass(frozen=True)
class ZoneCheck:
    location: Location
    distance_m: float
    inside: bool


def check_zones(locations: list[Location], lat: float, lng: float) -> ZoneCheck | None:
    """Nearest zone containing the point; if none contains it, the nearest zone overall.

    Returns None only when the business has no active zones yet.
    """
    checks = [
        ZoneCheck(
            location=location,
            distance_m=(measured := distance_m(lat, lng, location.latitude, location.longitude)),
            inside=measured <= location.radius_m,
        )
        for location in locations
    ]
    if not checks:
        return None

    inside = [check for check in checks if check.inside]
    return min(inside or checks, key=lambda check: check.distance_m)
