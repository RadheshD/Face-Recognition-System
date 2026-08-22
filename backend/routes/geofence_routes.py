"""
geofence_routes.py
Validates a user's GPS coordinates against a configured office geofence
using the Haversine formula.  No face-recognition logic is touched here.
"""

import math
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from config import settings  # type: ignore

logger = logging.getLogger("geofence")
router = APIRouter(tags=["Geofence"])


# ── Request / Response schemas ────────────────────────────────────────────────

class LocationPayload(BaseModel):
    latitude: float
    longitude: float
    accuracy: float | None = None   # metres — informational only


class LocationResult(BaseModel):
    location_verified: bool
    distance_meters: float
    allowed_radius: float
    message: str
    user_lat: float
    user_lon: float
    office_lat: float
    office_lon: float


# ── Haversine distance (metres) ───────────────────────────────────────────────

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in metres between two GPS points."""
    R = 6_371_000  # Earth's radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlam  = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/verify-location", response_model=LocationResult)
def verify_location(payload: LocationPayload):
    """
    Compare the user's GPS coordinates against the configured office location.
    Returns location_verified=True when inside the allowed radius.
    Face recognition logic is NOT referenced here.
    """
    distance = _haversine(
        payload.latitude, payload.longitude,
        settings.OFFICE_LAT, settings.OFFICE_LON,
    )

    inside = distance <= settings.GEOFENCE_RADIUS_METERS

    logger.info(
        "Geofence check — user=(%.6f, %.6f)  office=(%.6f, %.6f)  "
        "distance=%.1fm  radius=%.1fm  result=%s",
        payload.latitude, payload.longitude,
        settings.OFFICE_LAT, settings.OFFICE_LON,
        distance, settings.GEOFENCE_RADIUS_METERS,
        "INSIDE" if inside else "OUTSIDE",
    )

    return LocationResult(
        location_verified=inside,
        distance_meters=round(distance, 1),
        allowed_radius=settings.GEOFENCE_RADIUS_METERS,
        message=(
            "Location verified. You are inside the allowed area."
            if inside else
            f"You are {round(distance - settings.GEOFENCE_RADIUS_METERS, 1)} m outside "
            f"the allowed radius ({settings.GEOFENCE_RADIUS_METERS} m)."
        ),
        user_lat=payload.latitude,
        user_lon=payload.longitude,
        office_lat=settings.OFFICE_LAT,
        office_lon=settings.OFFICE_LON,
    )
