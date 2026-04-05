"""USGS Earthquake Catalog connector.

Implements BaseConnector backed by the USGS FDSN Event Web Service.

connector_id: ``usgs-earthquake``
source_type:  ``public_record``

API: https://earthquake.usgs.gov/fdsnws/event/1/
No authentication required — data is public domain (USGov).  All magnitude,
depth, and waveform data is freely redistributable.

Features:
- AOI-bounded queries via bounding-box derived from GeoJSON geometry.
- Minimum magnitude filter (default 2.5 to avoid noise).
- Normalises GeoJSON Feature records → ``seismic_event`` CanonicalEvents.
- Healthcheck probes the USGS service root endpoint.

Configure via environment variables (optional overrides):
  USGS_EARTHQUAKE_API_URL  (default: https://earthquake.usgs.gov/fdsnws/event/1)
  USGS_EARTHQUAKE_MIN_MAGNITUDE  (default: 2.5)
"""
from __future__ import annotations

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
    NormalizationRecord,
    ProvenanceRecord,
    SeismicAttributes,
    SourceType,
    make_event_id,
)

log = logging.getLogger(__name__)

_DEFAULT_API_URL = "https://earthquake.usgs.gov/fdsnws/event/1"

# USGS data is produced by a US government agency: public domain.
_LICENSE = LicenseRecord(
    access_tier="public",
    commercial_use="allowed",
    redistribution="allowed",
    attribution_required=True,
)


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


class UsgsEarthquakeConnector(BaseConnector):
    """USGS FDSN Earthquake Catalog — globally scoped seismic event connector.

    Returns ``seismic_event`` CanonicalEvents for all earthquakes intersecting
    the requested bounding box within the time window.
    """

    connector_id = "usgs-earthquake"
    display_name = "USGS Earthquake Catalog"
    source_type = "public_record"

    def __init__(
        self,
        *,
        api_url: str = _DEFAULT_API_URL,
        min_magnitude: float = 2.5,
        http_timeout: float = 30.0,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._min_magnitude = min_magnitude
        self._http_timeout = http_timeout

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        """Verify the USGS FDSN service is reachable."""
        try:
            resp = httpx.get(
                f"{self._api_url}/version",
                timeout=10.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"USGS Earthquake API unreachable: {exc}") from exc

    def fetch(
        self,
        geometry: dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        *,
        min_magnitude: float | None = None,
        max_results: int = 100,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Fetch earthquake events intersecting the geometry bounding box.

        Returns raw GeoJSON Feature dicts from the USGS catalog.
        """
        min_mag = min_magnitude if min_magnitude is not None else self._min_magnitude
        try:
            min_lat, min_lon, max_lat, max_lon = _bbox_from_geojson(geometry)
        except NormalizationError as exc:
            log.warning("Cannot derive bbox from geometry: %s", exc)
            return []

        params: dict[str, Any] = {
            "format": "geojson",
            "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "minlatitude": round(min_lat, 6),
            "maxlatitude": round(max_lat, 6),
            "minlongitude": round(min_lon, 6),
            "maxlongitude": round(max_lon, 6),
            "minmagnitude": min_mag,
            "orderby": "time",
            "limit": max_results,
        }
        try:
            resp = httpx.get(
                f"{self._api_url}/query",
                params=params,
                timeout=self._http_timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"USGS Earthquake query failed: {exc}") from exc

        payload = resp.json()
        features = payload.get("features", [])
        log.debug("USGS Earthquake: %d events returned for bbox", len(features))
        return features

    def normalize(self, raw: dict[str, Any]) -> CanonicalEvent:
        """Transform a USGS GeoJSON Feature into a ``seismic_event`` CanonicalEvent."""
        props = raw.get("properties", {})
        geom = raw.get("geometry", {})

        feature_id: str = raw.get("id", "")
        if not feature_id:
            raise NormalizationError("USGS feature missing 'id' field")

        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            raise NormalizationError(f"USGS feature {feature_id!r} has invalid geometry coordinates")

        lon, lat = float(coords[0]), float(coords[1])
        depth_km: float | None = float(coords[2]) if len(coords) >= 3 and coords[2] is not None else None

        # USGS time is epoch milliseconds
        raw_time = props.get("time")
        if raw_time is None:
            raise NormalizationError(f"USGS feature {feature_id!r} missing 'time'")
        event_time = datetime.fromtimestamp(int(raw_time) / 1000.0, tz=UTC)

        mag = props.get("mag")
        mag_type = props.get("magType")
        place = props.get("place", "")
        status = props.get("status", "")
        tsunami = props.get("tsunami")
        felt = props.get("felt")
        cdi = props.get("cdi")
        mmi = props.get("mmi")
        alert = props.get("alert")
        usgs_url = props.get("url", "")
        net = props.get("net", "")

        attrs = SeismicAttributes(
            magnitude=float(mag) if mag is not None else None,
            magnitude_type=str(mag_type) if mag_type else None,
            depth_km=depth_km,
            place=place or None,
            status=status or None,
            tsunami_flag=int(tsunami) if tsunami is not None else None,
            felt_reports=int(felt) if felt is not None else None,
            cdi=float(cdi) if cdi is not None else None,
            mmi=float(mmi) if mmi is not None else None,
            alert=str(alert) if alert else None,
            usgs_url=usgs_url or None,
            net=net or None,
        )

        geometry_point = {"type": "Point", "coordinates": [lon, lat]}
        event_id = make_event_id("usgs-earthquake", feature_id, event_time.isoformat())

        # Confidence: reviewed events score higher than automatic
        confidence = 0.9 if status == "reviewed" else 0.6

        return CanonicalEvent(
            event_id=event_id,
            source="usgs-earthquake",
            source_type=SourceType.PUBLIC_RECORD,
            entity_type=EntityType.SEISMIC_HAZARD,
            entity_id=feature_id,
            event_type=EventType.SEISMIC_EVENT,
            event_time=event_time,
            geometry=geometry_point,
            centroid=geometry_point,
            altitude_m=None,
            depth_m=depth_km * 1000.0 if depth_km is not None else None,
            confidence=confidence,
            attributes=attrs.model_dump(),
            normalization=NormalizationRecord(
                normalized_by="connector.usgs.earthquake",
                dedupe_key=feature_id,
            ),
            provenance=ProvenanceRecord(
                raw_source_ref=f"usgs://earthquake/{feature_id}",
                source_record_id=feature_id,
                source_url=usgs_url or None,
            ),
            correlation_keys=CorrelationKeys(),
            license=_LICENSE,
        )

    def health(self) -> ConnectorHealthStatus:
        """Lightweight health probe against the USGS version endpoint."""
        try:
            resp = httpx.get(f"{self._api_url}/version", timeout=10.0)
            resp.raise_for_status()
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=True,
                message=f"USGS FDSN reachable (HTTP {resp.status_code})",
                last_successful_poll=datetime.now(UTC),
            )
        except Exception as exc:
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=False,
                message=str(exc),
            )
