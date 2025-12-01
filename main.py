# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime, timezone
import math
import logging

# ---------------------
# Logging configuration
# ---------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("geofence-service")

# ---------------------
# FastAPI app
# ---------------------
app = FastAPI(
    title="Geofence Event Processing Service",
    description="Tracks vehicle locations and detects geofence enter/exit events.",
    version="1.0.0",
)

# Allow CORS for testing tools like Postman / web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------
# Models
# ---------------------
class LocationEvent(BaseModel):
    vehicleId: str = Field(..., description="Unique ID of the vehicle")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timestamp: Optional[datetime] = Field(
        None, description="Event timestamp (ISO 8601). Defaults to server time if omitted."
    )

    @validator("timestamp", pre=True, always=True)
    def default_timestamp(cls, v):
        return v or datetime.now(timezone.utc)


class GeofenceZone(BaseModel):
    id: str
    center_lat: float
    center_lng: float
    radius_m: float  # radius in meters


class VehicleStatus(BaseModel):
    vehicleId: str
    currentZone: Optional[str]
    lastLatitude: float
    lastLongitude: float
    lastUpdated: datetime


class ZoneEvent(BaseModel):
    eventType: str  # "enter" or "exit"
    vehicleId: str
    zoneId: str
    timestamp: datetime
    fromZone: Optional[str] = None
    toZone: Optional[str] = None


class LocationResponse(BaseModel):
    status: VehicleStatus
    generatedEvents: List[ZoneEvent]


# ---------------------
# In-memory state
# ---------------------
# Hardcoded zones (can be loaded from config/DB in real system)
ZONES: List[GeofenceZone] = [
    GeofenceZone(
        id="airport",
        center_lat=12.9611,
        center_lng=77.6387,
        radius_m=3000,
    ),
    GeofenceZone(
        id="downtown",
        center_lat=12.9716,
        center_lng=77.5946,
        radius_m=5000,
    ),
    GeofenceZone(
        id="suburb",
        center_lat=12.9956,
        center_lng=77.7000,
        radius_m=4000,
    ),
]

# vehicleId -> VehicleStatus-like dict
VEHICLE_STATE: Dict[str, VehicleStatus] = {}

# simple in-memory event log (would be DB / stream in real system)
EVENT_LOG: List[ZoneEvent] = []


# ---------------------
# Geospatial helpers
# ---------------------
def haversine_distance_m(lat1, lon1, lat2, lon2) -> float:
    """
    Calculate distance in meters between two lat/lng points using Haversine formula.
    """
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def find_zone_for_point(lat: float, lng: float) -> Optional[str]:
    """
    Return the ID of the first zone that contains the point, or None.
    For overlapping zones, the first match is returned. This is a simplification.
    """
    for zone in ZONES:
        distance = haversine_distance_m(lat, lng, zone.center_lat, zone.center_lng)
        if distance <= zone.radius_m:
            return zone.id
    return None


# ---------------------
# API Endpoints
# ---------------------
@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/location", response_model=LocationResponse, tags=["location"])
def ingest_location(event: LocationEvent):
    """
    Accept a vehicle GPS location update and detect geofence enter/exit events.
    """
    vehicle_id = event.vehicleId
    lat = event.latitude
    lng = event.longitude
    ts = event.timestamp

    logger.info(
        f"Received location update: vehicle={vehicle_id}, lat={lat}, lng={lng}, ts={ts.isoformat()}"
    )

    # Determine current zone based on this location
    current_zone = find_zone_for_point(lat, lng)

    # Fetch previous state (if any)
    prev_state: Optional[VehicleStatus] = VEHICLE_STATE.get(vehicle_id)
    prev_zone = prev_state.currentZone if prev_state else None

    generated_events: List[ZoneEvent] = []

    # Detect transitions
    if prev_zone != current_zone:
        # Vehicle entered a zone
        if prev_zone is None and current_zone is not None:
            event_obj = ZoneEvent(
                eventType="enter",
                vehicleId=vehicle_id,
                zoneId=current_zone,
                timestamp=ts,
                fromZone=None,
                toZone=current_zone,
            )
            EVENT_LOG.append(event_obj)
            generated_events.append(event_obj)
            logger.info(f"Vehicle {vehicle_id} ENTERED zone {current_zone}")

        # Vehicle exited a zone
        elif prev_zone is not None and current_zone is None:
            event_obj = ZoneEvent(
                eventType="exit",
                vehicleId=vehicle_id,
                zoneId=prev_zone,
                timestamp=ts,
                fromZone=prev_zone,
                toZone=None,
            )
            EVENT_LOG.append(event_obj)
            generated_events.append(event_obj)
            logger.info(f"Vehicle {vehicle_id} EXITED zone {prev_zone}")

        # Vehicle switched from one zone to another
        elif prev_zone is not None and current_zone is not None:
            exit_event = ZoneEvent(
                eventType="exit",
                vehicleId=vehicle_id,
                zoneId=prev_zone,
                timestamp=ts,
                fromZone=prev_zone,
                toZone=current_zone,
            )
            enter_event = ZoneEvent(
                eventType="enter",
                vehicleId=vehicle_id,
                zoneId=current_zone,
                timestamp=ts,
                fromZone=prev_zone,
                toZone=current_zone,
            )
            EVENT_LOG.extend([exit_event, enter_event])
            generated_events.extend([exit_event, enter_event])
            logger.info(
                f"Vehicle {vehicle_id} MOVED from zone {prev_zone} to zone {current_zone}"
            )

    # Update current vehicle state
    new_state = VehicleStatus(
        vehicleId=vehicle_id,
        currentZone=current_zone,
        lastLatitude=lat,
        lastLongitude=lng,
        lastUpdated=ts,
    )
    VEHICLE_STATE[vehicle_id] = new_state

    return LocationResponse(status=new_state, generatedEvents=generated_events)


@app.get("/status/{vehicle_id}", response_model=VehicleStatus, tags=["status"])
def get_vehicle_status(vehicle_id: str):
    """
    Get the current zone and last known location of a vehicle.
    """
    state = VEHICLE_STATE.get(vehicle_id)
    if not state:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return state


@app.get("/events", response_model=List[ZoneEvent], tags=["events"])
def list_events(vehicleId: Optional[str] = None, limit: int = 100):
    """
    List recent zone enter/exit events.
    Optional filter by vehicleId. 'limit' controls how many most recent events are returned.
    """
    events = EVENT_LOG
    if vehicleId:
        events = [e for e in events if e.vehicleId == vehicleId]
    return events[-limit:]


@app.get("/zones", response_model=List[GeofenceZone], tags=["zones"])
def list_zones():
    """
    List configured geofence zones.
    """
    return ZONES
