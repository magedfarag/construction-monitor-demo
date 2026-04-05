"""NASA Earth Observatory Natural Event Tracker (EONET) connector.

Implements BaseConnector backed by the NASA EONET v3 REST API.

connector_id: ``nasa-eonet``
source_type:  ``context_feed``

API: https://eonet.gsfc.nasa.gov/docs/v3
No authentication required — NASA open data, CC0 / public domain.

Categories tracked by EONET:
  wildfires, volcanoes, severe-storms, sea-and-lake-ice,
  earthquakes, landslides, drought, dust-and-haze, floods,
  temp-extreme, manmade, snow-ice, water-color

This connector fetches open (active) events, clips them to the requested
bounding box, and normalises each to a ``natural_hazard_event`` CanonicalEvent.

Geometry strategy:
- Point events  → Point geometry
- Polygon events → Polygon with Point centroid
- Multi-point track → first point used for centroid
"""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from src.connectors.base import (
    BaseConnector,
    ConnectorHealthStatus,
    ConnectorUnavailableError,
    NormalizationError,
)
from src.models.canonical_event import (
    CanonicalEvent,
    CorrelationKeys,
    EntityType,
    EventType,
    LicenseRecord,
    NaturalHazardAttributes,
    NormalizationRecord,
    ProvenanceRecord,
    SourceType,
    make_event_id,
)

log = logging.getLogger(__name__)

_DEFAULT_API_URL = "https://eonet.gsfc.nasa.gov/api/v3"

# NASA open data — CC0 / public domain.
_LICENSE = LicenseRecord(
    access_tier="public",
    commercial_use="allowed",
    redistribution="allowed",
    attribution_required=True,
)

# Map EONET category slugs to human-readable titles
_CATEGORY_TITLES: dict[str, str] = {
    "wildfires": "Wildfires",
    "volcanoes": "Volcanoes",
    "severe-storms": "Severe Storms",
    "sea-and-lake-ice": "Sea & Lake Ice",
    "earthquakes": "Earthquakes",
    "landslides": "Landslides",
    "drought": "Drought",
    "dust-and-haze": "Dust & Haze",
    "floods": "Floods",
    "temp-extreme": "Extreme Temperatures",
    "manmade": "Manmade Events",
    "snow-ice": "Snow & Ice",
    "water-color": "Water Color",
}


def _extract_first_point(geometry: dict[str, Any]) -> tuple[float, float] | None:
    """Return (lon, lat) from the first coordinate of any geometry type."""
    gtype = geometry.get("type", "")
    coords = geometry.get("coordinates")
    if not coords:
        return None
    try:
        if gtype == "Point":
            return float(coords[0]), float(coords[1])
        if gtype == "Polygon":
            return float(coords[0][0][0]), float(coords[0][0][1])
        if gtype == "MultiPoint":
            return float(coords[0][0]), float(coords[0][1])
    except (IndexError, TypeError, ValueError):
        return None
    return None


def _point_in_bbox(
    lon: float,
    lat: float,
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
) -> bool:
    """Return True if (lon, lat) falls inside the bounding box."""
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def _bbox_from_geojson(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return (min_lat, min_lon, max_lat, max_lon) from a GeoJSON geometry."""
    gtype = geometry.get("type", "")
    coords_flat: list[list[float]] = []
    if gtype == "Point":
        coords_flat = [geometry["coordinates"]]
    elif gtype == "Polygon":
        coords_flat = geometry["coordinates"][0]
    elif gtype == "MultiPolygon":
        for poly in geometry["coordinates"]:
            coords_flat.extend(poly[0])
    else:
        raise NormalizationError(f"Unsupported geometry type: {gtype!r}")
    lons = [float(c[0]) for c in coords_flat]
    lats = [float(c[1]) for c in coords_flat]
    return min(lats), min(lons), max(lats), max(lons)


class NasaEonetConnector(BaseConnector):
    """NASA EONET — global natural hazard event connector.

    Fetches open and recently closed natural events and normalises them to
    ``natural_hazard_event`` CanonicalEvents scoped to the query AOI.
    """

    connector_id = "nasa-eonet"
    display_name = "NASA EONET (Natural Event Tracker)"
    source_type = "context_feed"

    def __init__(
        self,
        *,
        api_url: str = _DEFAULT_API_URL,
        days_lookback: int = 30,
        http_timeout: float = 30.0,
        categories: list[str] | None = None,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._days_lookback = days_lookback
        self._http_timeout = http_timeout
        # None means all categories
        self._categories = categories

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        """Verify the NASA EONET API is reachable."""
        try:
            resp = httpx.get(f"{self._api_url}/events?limit=1", timeout=10.0)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"NASA EONET API unreachable: {exc}") from exc

    def fetch(
        self,
        geometry: dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        *,
        categories: list[str] | None = None,
        max_results: int = 200,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Fetch open natural hazard events, filtered to the AOI bounding box.

        EONET does not support geographic filtering server-side; events are
        fetched globally and clipped to the bounding box client-side.
        """
        try:
            min_lat, min_lon, max_lat, max_lon = _bbox_from_geojson(geometry)
        except NormalizationError as exc:
            log.warning("Cannot derive bbox from geometry: %s", exc)
            return []

        cats = categories or self._categories
        params: dict[str, Any] = {
            "status": "open",
            "days": self._days_lookback,
            "limit": min(max_results, 1000),
        }
        if cats:
            params["category"] = ",".join(cats)

        try:
            resp = httpx.get(
                f"{self._api_url}/events",
                params=params,
                timeout=self._http_timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"NASA EONET fetch failed: {exc}") from exc

        events = resp.json().get("events", [])
        log.debug("NASA EONET: %d global events, clipping to bbox", len(events))

        # Clip to AOI bounding box — keep events whose first geometry point is inside
        clipped: list[dict[str, Any]] = []
        for event in events:
            geometries = event.get("geometry", [])
            for geom_entry in geometries:
                geom = geom_entry.get("coordinates") and geom_entry
                if not geom:
                    continue
                pt = _extract_first_point(
                    {"type": geom_entry.get("type", "Point"), "coordinates": geom_entry.get("coordinates")}
                )
                if pt and _point_in_bbox(pt[0], pt[1], min_lat, min_lon, max_lat, max_lon):
                    # Inject bbox clip context for normalize()
                    event["_matched_geom"] = geom_entry
                    clipped.append(event)
                    break

        log.debug("NASA EONET: %d events after bbox clip", len(clipped))
        return clipped[:max_results]

    def normalize(self, raw: dict[str, Any]) -> CanonicalEvent:
        """Transform a NASA EONET event dict into a ``natural_hazard_event`` CanonicalEvent."""
        eonet_id: str = raw.get("id", "")
        if not eonet_id:
            raise NormalizationError("EONET event missing 'id'")

        status: str = raw.get("status", "open")
        closed_date: str | None = raw.get("closed")

        # Categories — first category wins for primary classification
        categories = raw.get("categories", [])
        cat_slug: str | None = categories[0].get("id") if categories else None
        cat_title: str | None = categories[0].get("title") if categories else None
        if cat_title is None and cat_slug:
            cat_title = _CATEGORY_TITLES.get(cat_slug, cat_slug)

        # Sources
        sources: list[str] = [s.get("url", "") for s in raw.get("sources", []) if s.get("url")]

        # Geometry: prefer matched geometry, else most recent
        matched_geom = raw.get("_matched_geom")
        if not matched_geom:
            geometries = raw.get("geometry", [])
            matched_geom = geometries[-1] if geometries else None

        if not matched_geom:
            raise NormalizationError(f"EONET event {eonet_id!r} has no geometry")

        geom_type = matched_geom.get("type", "Point")
        geom_coords = matched_geom.get("coordinates")
        if not geom_coords:
            raise NormalizationError(f"EONET event {eonet_id!r} geometry has no coordinates")

        # Extract a representative point for centroid
        pt = _extract_first_point({"type": geom_type, "coordinates": geom_coords})
        if pt is None:
            raise NormalizationError(f"EONET event {eonet_id!r}: cannot extract point from geometry")
        lon, lat = pt

        centroid = {"type": "Point", "coordinates": [lon, lat]}
        geometry = {"type": geom_type, "coordinates": geom_coords}

        # Timestamp from matched geometry or fallback to now
        raw_date = matched_geom.get("date")
        if raw_date:
            try:
                event_time = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except ValueError:
                event_time = datetime.now(UTC)
        else:
            event_time = datetime.now(UTC)

        attrs = NaturalHazardAttributes(
            category=cat_slug,
            category_title=cat_title,
            sources=sources,
            status=status,
            closed_date=str(closed_date) if closed_date else None,
            eonet_id=eonet_id,
        )

        dedupe_key = hashlib.sha256(f"{eonet_id}:{event_time.isoformat()}".encode()).hexdigest()[:16]
        event_id = make_event_id("nasa-eonet", eonet_id, event_time.isoformat())

        return CanonicalEvent(
            event_id=event_id,
            source="nasa-eonet",
            source_type=SourceType.CONTEXT_FEED,
            entity_type=EntityType.NATURAL_HAZARD,
            entity_id=eonet_id,
            event_type=EventType.NATURAL_HAZARD_EVENT,
            event_time=event_time,
            geometry=geometry,
            centroid=centroid,
            confidence=0.85,
            attributes=attrs.model_dump(),
            normalization=NormalizationRecord(
                normalized_by="connector.nasa.eonet",
                dedupe_key=dedupe_key,
            ),
            provenance=ProvenanceRecord(
                raw_source_ref=f"eonet://events/{eonet_id}",
                source_record_id=eonet_id,
                source_url=sources[0] if sources else None,
            ),
            correlation_keys=CorrelationKeys(),
            license=_LICENSE,
        )

    def health(self) -> ConnectorHealthStatus:
        """Lightweight health probe against the EONET events endpoint."""
        try:
            resp = httpx.get(
                f"{self._api_url}/events",
                params={"limit": 1, "status": "open"},
                timeout=10.0,
            )
            resp.raise_for_status()
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=True,
                message=f"NASA EONET reachable (HTTP {resp.status_code})",
                last_successful_poll=datetime.now(UTC),
            )
        except Exception as exc:
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=False,
                message=str(exc),
            )
