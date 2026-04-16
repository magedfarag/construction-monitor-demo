"""Dark ship detection REST API — P6-5.

POST /api/v1/dark-ships/detect   — run detection on a submitted event list
GET  /api/v1/dark-ships          — run detection against the live EventStore
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.models.canonical_event import CanonicalEvent, EventType
from src.services.dark_ship_detector import (
    DarkShipDetectionResponse,
    detect_dark_ships,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dark-ships", tags=["dark-ships"])

# Module-level EventStore reference — injected by app lifespan
_event_store: Any | None = None
# Module-level ConnectorRegistry reference — injected by app lifespan
_connector_registry: Any | None = None


def set_event_store(store: Any) -> None:
    """Inject the shared EventStore. Called from app lifespan."""
    global _event_store
    _event_store = store


def set_connector_registry(registry: Any) -> None:
    """Inject the shared V2 ConnectorRegistry. Called from app lifespan."""
    global _connector_registry
    _connector_registry = registry


# Default AoI for best-effort AIS live poll: Strait of Hormuz + surrounding waters.
# Used only when the EventStore has no ship_position events and no spatial context
# is available from the incoming request.
_HORMUZ_BBOX_GEOM: dict = {
    "type": "Polygon",
    "coordinates": [[
        [55.0, 22.0], [62.0, 22.0], [62.0, 28.0], [55.0, 28.0], [55.0, 22.0],
    ]],
}


_LIVE_POLL_TIMEOUT_S: float = 12.0


def _live_poll_ais() -> list[CanonicalEvent]:
    """Best-effort: poll AISStream for the Hormuz area and ingest into the store.

    Called only when the EventStore has no ship_position events.  Uses a
    fixed bounding box so the endpoint remains callable without a request body.
    """
    if _connector_registry is None or _event_store is None:
        return []
    connector = _connector_registry.get("ais-stream")
    if connector is None:
        log.debug("_live_poll_ais: ais-stream connector not available")
        return []
    now = datetime.now(UTC)
    try:
        with ThreadPoolExecutor(max_workers=1) as _pool:
            future = _pool.submit(
                connector.fetch_and_normalize,
                _HORMUZ_BBOX_GEOM,
                now - timedelta(hours=1),
                now,
            )
            try:
                events, warnings = future.result(timeout=_LIVE_POLL_TIMEOUT_S)
            except FuturesTimeoutError:
                log.warning("_live_poll_ais: timed out after %.0fs", _LIVE_POLL_TIMEOUT_S)
                return []
        if events:
            _event_store.ingest_batch(events)
            log.info("_live_poll_ais: ingested %d ship_position events (%d warnings)", len(events), len(warnings))
        return events
    except Exception as exc:  # noqa: BLE001
        log.warning("_live_poll_ais: fetch failed: %s", exc)
        return []


class DetectRequest(BaseModel):
    events: list[CanonicalEvent]


def list_demo_candidates() -> DarkShipDetectionResponse:
    """Return a fixed set of curated demo dark-ship candidates for testing / demo mode.

    These are drawn from known sanctioned/shadow-fleet vessels in the vessel registry
    and are NOT served by the live ``list_candidates()`` endpoint (which queries the
    EventStore). Use this function in tests and demo-mode fixtures only.
    """
    from src.services.dark_ship_detector import DarkShipCandidate, _event_id

    _candidates = [
        DarkShipCandidate(
            mmsi="422110600",
            vessel_name="WISDOM",
            gap_start="2024-01-10T06:00:00+00:00",
            gap_end="2024-01-11T02:30:00+00:00",
            gap_hours=20.5,
            last_known_lon=56.3,
            last_known_lat=26.5,
            reappear_lon=58.1,
            reappear_lat=24.9,
            position_jump_km=240.0,
            sanctions_flag=True,
            dark_ship_risk="high",
            confidence=0.92,
            event_id=_event_id("422110600", "2024-01-10T06:00:00+00:00"),
        ),
        DarkShipCandidate(
            mmsi="422110800",
            vessel_name="HORSE",
            gap_start="2024-01-14T18:00:00+00:00",
            gap_end="2024-01-16T04:00:00+00:00",
            gap_hours=34.0,
            last_known_lon=43.1,
            last_known_lat=12.4,
            reappear_lon=44.8,
            reappear_lat=11.7,
            position_jump_km=180.0,
            sanctions_flag=True,
            dark_ship_risk="high",
            confidence=0.87,
            event_id=_event_id("422110800", "2024-01-14T18:00:00+00:00"),
        ),
        DarkShipCandidate(
            mmsi="422111200",
            vessel_name="SEA ROSE",
            gap_start="2024-01-20T09:00:00+00:00",
            gap_end="2024-01-21T03:00:00+00:00",
            gap_hours=18.0,
            last_known_lon=50.8,
            last_known_lat=25.1,
            reappear_lon=51.9,
            reappear_lat=24.6,
            position_jump_km=120.0,
            sanctions_flag=True,
            dark_ship_risk="medium",
            confidence=0.78,
            event_id=_event_id("422111200", "2024-01-20T09:00:00+00:00"),
        ),
    ]
    return DarkShipDetectionResponse(
        candidates=_candidates,
        total=len(_candidates),
        events_analysed=0,
    )


@router.post(
    "/detect",
    response_model=DarkShipDetectionResponse,
    summary="Detect dark-ship candidates from a list of canonical AIS events",
)
def detect(req: DetectRequest) -> DarkShipDetectionResponse:
    if not req.events:
        raise HTTPException(status_code=422, detail="events list must not be empty")
    return detect_dark_ships(req.events)


@router.get(
    "",
    response_model=DarkShipDetectionResponse,
    summary="Detect dark-ship candidates from the live EventStore",
)
def list_candidates() -> DarkShipDetectionResponse:
    """Run dark-ship detection against ship_position events in the live EventStore.

    Returns an empty candidate list when no AIS data is available (e.g., no
    AISSTREAM_API_KEY configured or store not yet populated).
    """
    if _event_store is None:
        return DarkShipDetectionResponse(candidates=[], total=0, events_analysed=0)

    window_start = (datetime.now(UTC) - timedelta(days=90)).isoformat()
    window_end = datetime.now(UTC).isoformat()

    with _event_store._lock:
        ship_events = [
            e for e in _event_store._events.values()
            if e.event_type == EventType.SHIP_POSITION
            and window_start <= e.event_time <= window_end
        ]

    if not ship_events:
        log.debug("Dark ship detection: no ship_position events in 90-day window — attempting live AIS poll")
        ship_events = _live_poll_ais()

    if not ship_events:
        log.debug("Dark ship detection: still no ship_position events after live poll")
        return DarkShipDetectionResponse(candidates=[], total=0, events_analysed=0)

    log.info("Dark ship detection: analysing %d ship_position events", len(ship_events))
    return detect_dark_ships(ship_events)
