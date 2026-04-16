"""Event search router — P1-4.

POST /api/v1/events/search     — AOI + time + source + type filter
GET  /api/v1/events/:event_id  — single event detail
GET  /api/v1/events/timeline   — aggregated event counts by time bucket
GET  /api/v1/events/sources    — list active source families

P5-1.5: When a search returns more than ``DENSITY_THRESHOLD`` events,
server-side uniform subsampling is applied before the response is returned.
The ``was_reduced`` field in the response signals that reduction occurred.

Best-effort live poll: when a search for telemetry event types (ship_position,
aircraft_position) returns 0 results and a geometry is present, the router
directly polls the relevant V2 connector (AISStream, OpenSky) and ingests the
fresh events before re-running the search.  This makes the endpoints work with
only AISSTREAM_API_KEY set — no Celery worker required.
"""
from __future__ import annotations

import logging
import random
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.aois import get_aoi_store
from src.models.canonical_event import CanonicalEvent, EventType
from src.models.event_search import (
    EventSearchRequest,
    EventSearchResponse,
    SourceSummary,
    TimelineResponse,
)
from src.services.event_store import EventStore, get_default_event_store

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])

# ── P5-1.5: Density reduction threshold (can be overridden via AppSettings) ───
_DENSITY_THRESHOLD: int = 500
_DENSITY_MAX_RESULTS: int = 200

# ── Connector registry (injected by app lifespan for best-effort live poll) ───
_connector_registry: Any | None = None


def set_connector_registry(registry: Any) -> None:
    """Inject the shared V2 ConnectorRegistry. Called from app lifespan."""
    global _connector_registry
    _connector_registry = registry


# Event types that can be fetched live from a connector when the store is empty.
# Maps EventType value → connector_id registered in the V2 registry.
_LIVE_POLL_MAP: dict[str, str] = {
    EventType.SHIP_POSITION.value: "ais-stream",
    EventType.AIRCRAFT_POSITION.value: "opensky",
}


# Per-connector live-poll timeout (seconds).  Keeps HTTP response latency bounded.
# AISStream WebSocket has open_timeout=10 + collect_timeout_s=10 by default, so
# we cap the whole call at 12 s to stay within a typical 20 s HTTP gateway timeout.
_LIVE_POLL_TIMEOUT_S: float = 12.0


def _live_poll_and_ingest(req: EventSearchRequest, store: EventStore) -> int:
    """Best-effort on-demand poll for telemetry connectors.

    Called when a search returns 0 results and a geometry is present.  Polls
    the relevant live connector(s) directly, normalises the results, and
    ingests them into the store so the re-run search finds data.

    Returns the number of newly ingested events (0 on any error).
    """
    if _connector_registry is None or req.geometry is None:
        return 0

    requested = {
        (t.value if hasattr(t, "value") else str(t))
        for t in (req.event_types or [])
    }
    # If no type filter is set, try all live-pollable types.
    connector_ids = {
        cid
        for etype, cid in _LIVE_POLL_MAP.items()
        if not requested or etype in requested
    }

    total_ingested = 0
    for cid in connector_ids:
        connector = _connector_registry.get(cid)
        if connector is None:
            continue
        try:
            with ThreadPoolExecutor(max_workers=1) as _pool:
                future = _pool.submit(
                    connector.fetch_and_normalize,
                    req.geometry, req.start_time, req.end_time,
                )
                try:
                    events, warnings = future.result(timeout=_LIVE_POLL_TIMEOUT_S)
                except FuturesTimeoutError:
                    log.warning("live_poll_fallback: %s timed out after %.0fs", cid, _LIVE_POLL_TIMEOUT_S)
                    continue
            if events:
                store.ingest_batch(events)
                total_ingested += len(events)
                log.info(
                    "live_poll_fallback: %s → %d events ingested (%d warnings)",
                    cid, len(events), len(warnings),
                )
            else:
                log.debug("live_poll_fallback: %s returned 0 events", cid)
        except Exception as exc:  # noqa: BLE001
            log.warning("live_poll_fallback: %s raised %s", cid, exc)
    return total_ingested


# ── Dependency ────────────────────────────────────────────────────────────────
# _store is the process-wide singleton.  Tests that import _store directly may
# clear _store._events for isolation.  get_event_store() always dereferences
# the current singleton so pollers, the events router, and the playback router
# share the same in-memory store.
_store: EventStore = get_default_event_store()


def get_event_store() -> EventStore:
    return get_default_event_store()


EventStoreDep = Annotated[EventStore, Depends(get_event_store)]


def _resolve_aoi_geometry(aoi_id: str | None) -> dict | None:
    """Resolve an AOI id to its geometry so searches can use spatial filtering."""
    if not aoi_id:
        return None
    aoi = get_aoi_store().get(aoi_id)
    if not aoi:
        return None
    geometry = aoi.geometry
    return geometry.model_dump() if hasattr(geometry, "model_dump") else geometry


def _apply_density_reduction(response: EventSearchResponse) -> EventSearchResponse:
    """P5-1.5: Uniformly subsample events when count exceeds the density threshold.

    Uses a seed derived from the result count for reproducible sampling
    within a single request.  The ``was_reduced`` flag is set on the response.
    """
    if len(response.events) <= _DENSITY_THRESHOLD:
        return response
    rng = random.Random(len(response.events))
    sampled = rng.sample(response.events, _DENSITY_MAX_RESULTS)
    sampled.sort(key=lambda e: e.event_time)
    return EventSearchResponse(
        events=sampled,
        total=response.total,
        was_reduced=True,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/search",
    response_model=EventSearchResponse,
    summary="Search canonical events by AOI + time + source + type",
)
def search_events(req: EventSearchRequest, store: EventStoreDep) -> EventSearchResponse:
    """Query the canonical_events store using spatial, temporal, and categorical filters.

    At minimum, start_time and end_time are required.
    Supply geometry or aoi_id to restrict to a specific area.
    When the result count exceeds the density threshold, uniform subsampling
    is applied server-side and the ``was_reduced`` flag is set in the response.
    """
    if req.end_time <= req.start_time:
        raise HTTPException(status_code=422, detail="end_time must be after start_time")
    if req.geometry is None and req.aoi_id:
        resolved_geometry = _resolve_aoi_geometry(req.aoi_id)
        if resolved_geometry is not None:
            req = req.model_copy(update={"geometry": resolved_geometry})
    result = store.search(req)
    # Best-effort live poll: if the initial search returned nothing, attempt to
    # hydrate the store from live connectors and re-run.
    if result.total == 0 and req.geometry is not None:
        ingested = _live_poll_and_ingest(req, store)
        if ingested > 0:
            result = store.search(req)
    return _apply_density_reduction(result)


@router.get(
    "/sources",
    response_model=list[SourceSummary],
    summary="List active source families with event counts",
)
def list_sources(store: EventStoreDep) -> list[SourceSummary]:
    """Return per-connector event counts and last-seen timestamps for the source catalog panel."""
    return store.active_sources()


@router.get(
    "/timeline",
    response_model=TimelineResponse,
    summary="Aggregated event counts bucketed by time for the timeline bar chart",
)
def get_timeline(
    store: EventStoreDep,
    start_time: datetime = Query(..., description="Window start (UTC ISO 8601)"),
    end_time: datetime = Query(..., description="Window end (UTC ISO 8601)"),
    aoi_id: str | None = Query(default=None, description="Filter to AOI correlation key"),
    bucket_minutes: int = Query(default=60, ge=1, le=1440, description="Bucket width in minutes"),
) -> TimelineResponse:
    if end_time <= start_time:
        raise HTTPException(status_code=422, detail="end_time must be after start_time")
    return store.timeline(
        start_time,
        end_time,
        aoi_id=aoi_id,
        geometry=_resolve_aoi_geometry(aoi_id),
        bucket_minutes=bucket_minutes,
    )


@router.get(
    "/{event_id}",
    response_model=CanonicalEvent,
    summary="Retrieve a single canonical event by ID",
)
def get_event(event_id: str, store: EventStoreDep) -> CanonicalEvent:
    event = store.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event not found: {event_id}")
    return event
