"""OpenAQ Air Quality connector.

Implements BaseConnector backed by the OpenAQ v3 public API.

connector_id: ``openaq``
source_type:  ``public_record``

API: https://api.openaq.org/v3/
No authentication required (rate-limited); optional API key for higher limits.
Data license: CC BY 4.0

Air quality monitoring complements GEOINT / Gulf operations intelligence:
- PM2.5 / PM10 spikes → oil well fires, industrial accidents, dust storms
- SO2 spikes → refinery events, sour-gas releases, volcanic activity
- NO2 spikes → heavy industrial activity, vehicle convoys, fuel burning
- O3 → secondary pollution indicator for industrial zone activity
- CO → combustion events (fires, engine exhausts in closed spaces)

OpenAQ v3 fetch strategy (two requests):
  1. ``GET /v3/locations?bbox={w,s,e,n}`` — discover monitoring stations
  2. ``GET /v3/measurements?{location_ids}&datetime_from=...&limit=500``
     — get the most recent readings for each station

Produces one ``air_quality_observation`` CanonicalEvent per distinct
(location, parameter, observation-time) tuple.

Configure via environment variables:
  OPENAQ_API_URL   — Override endpoint (default: https://api.openaq.org/v3)
  OPENAQ_API_KEY   — Optional API key for higher rate limits
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
    AirQualityAttributes,
    CanonicalEvent,
    CorrelationKeys,
    EntityType,
    EventType,
    LicenseRecord,
    NormalizationRecord,
    ProvenanceRecord,
    SourceType,
    make_event_id,
)

log = logging.getLogger(__name__)

_DEFAULT_API_URL = "https://api.openaq.org/v3"

# CC BY 4.0
_LICENSE = LicenseRecord(
    access_tier="public",
    commercial_use="allowed",
    redistribution="allowed",
    attribution_required=True,
)

# Parameters considered elevated-risk for GEOINT purposes
_HIGH_INTEREST_PARAMS = frozenset({"pm25", "pm10", "so2", "no2", "o3", "co"})


def _bbox_from_geojson(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return (min_lat, min_lon, max_lat, max_lon)."""
    gtype = geometry.get("type", "")
    coords: list[list[float]] = []
    if gtype == "Point":
        coords = [geometry["coordinates"]]
    elif gtype == "Polygon":
        coords = geometry["coordinates"][0]
    elif gtype == "MultiPolygon":
        for poly in geometry["coordinates"]:
            coords.extend(poly[0])
    else:
        raise NormalizationError(f"Unsupported geometry type: {gtype!r}")
    lons = [float(c[0]) for c in coords]
    lats = [float(c[1]) for c in coords]
    return min(lats), min(lons), max(lats), max(lons)


class OpenAqConnector(BaseConnector):
    """OpenAQ air quality sensor network connector.

    Fetches the most recent readings from ground-based monitoring stations
    within the query AOI.  Particularly useful for:
    - UAE, Saudi Arabia, Kuwait, Bahrain (dense urban sensor networks)
    - Detecting oil field / industrial flare events via PM2.5 / SO2 spikes
    - Monitoring air quality impact from conflict-related fires (Yemen, Iraq)

    Note: sensor coverage in MENA is urban-centric.  Rural and offshore areas
    have limited ground-truth coverage; combine with NASA FIRMS for
    comprehensive fire/thermal-anomaly intelligence.
    """

    connector_id = "openaq"
    display_name = "OpenAQ Air Quality Network"
    source_type = "public_record"

    def __init__(
        self,
        *,
        api_url: str = _DEFAULT_API_URL,
        api_key: str = "",
        max_locations: int = 30,
        http_timeout: float = 30.0,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._api_key = api_key
        self._max_locations = max(1, min(50, max_locations))
        self._http_timeout = http_timeout

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            h["X-API-Key"] = self._api_key
        return h

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        """Verify OpenAQ v3 API is reachable."""
        try:
            resp = httpx.get(
                f"{self._api_url}/locations",
                params={"limit": 1},
                headers=self._headers(),
                timeout=15.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"OpenAQ API unreachable: {exc}") from exc

    def fetch(
        self,
        geometry: dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        *,
        max_results: int = 500,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Fetch air quality measurements in the AOI for the time window.

        Step 1 — discover monitoring stations in the bbox.
        Step 2 — fetch measurements for those locations.
        Returns a flat list of measurement dicts (location metadata embedded).
        """
        try:
            min_lat, min_lon, max_lat, max_lon = _bbox_from_geojson(geometry)
        except NormalizationError as exc:
            log.warning("Cannot derive bbox from geometry: %s", exc)
            return []

        # Step 1: locations
        bbox_str = f"{min_lon},{min_lat},{max_lon},{max_lat}"
        try:
            r1 = httpx.get(
                f"{self._api_url}/locations",
                params={"bbox": bbox_str, "limit": self._max_locations},
                headers=self._headers(),
                timeout=self._http_timeout,
            )
            r1.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"OpenAQ locations fetch failed: {exc}") from exc

        locations = r1.json().get("results", [])
        if not locations:
            log.debug("OpenAQ: no monitoring stations in bbox %s", bbox_str)
            return []

        # Build a location metadata lookup
        location_meta: dict[int, dict[str, Any]] = {
            loc["id"]: loc for loc in locations
        }
        location_ids = list(location_meta.keys())

        # Step 2: measurements
        params: list[tuple] = [
            ("datetime_from", start_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("datetime_to", end_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("limit", min(max_results, 500)),
            ("sort", "desc"),
        ]
        for lid in location_ids[: self._max_locations]:
            params.append(("location_id", str(lid)))

        try:
            r2 = httpx.get(
                f"{self._api_url}/measurements",
                params=params,
                headers=self._headers(),
                timeout=self._http_timeout,
            )
            r2.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("OpenAQ measurements fetch failed: %s", exc)
            # Degrade gracefully: return location-only records without measurements
            return [
                {"_location": loc, "_measurement": None} for loc in locations
            ]

        measurements = r2.json().get("results", [])
        log.debug("OpenAQ: %d measurements for %d stations", len(measurements), len(locations))

        # Embed location metadata into each measurement
        enriched: list[dict[str, Any]] = []
        for m in measurements:
            loc_id = m.get("location_id") or (m.get("location", {}) or {}).get("id")
            meta = location_meta.get(loc_id, {})
            enriched.append({"_location": meta, "_measurement": m})
        return enriched[: max_results]

    def normalize(self, raw: dict[str, Any]) -> CanonicalEvent:
        """Transform an enriched measurement dict → ``air_quality_observation``."""
        loc = raw.get("_location") or {}
        measurement = raw.get("_measurement") or {}

        # Extract coordinates from location
        coords = loc.get("coordinates", {}) or {}
        lat = coords.get("latitude")
        lon = coords.get("longitude")
        if lat is None or lon is None:
            # Try from measurement
            mloc = measurement.get("location", {}) or {}
            mcoords = mloc.get("coordinates", {}) or {}
            lat = mcoords.get("latitude")
            lon = mcoords.get("longitude")
        if lat is None or lon is None:
            raise NormalizationError("OpenAQ record has no usable coordinates")

        lat = float(lat)
        lon = float(lon)
        geom = {"type": "Point", "coordinates": [lon, lat]}

        loc_id: int | None = loc.get("id") or measurement.get("location_id")
        loc_name: str | None = loc.get("name") or (
            measurement.get("location", {}) or {}
        ).get("name")

        # Parameter and value
        parameter: str | None = None
        display_name: str | None = None
        value: float | None = None
        unit: str | None = None
        sensor_id: int | None = None

        if measurement:
            param_block = measurement.get("parameter") or {}
            if isinstance(param_block, dict):
                parameter = param_block.get("name") or param_block.get("id")
                display_name = param_block.get("displayName") or param_block.get("display_name")
                unit = param_block.get("units") or param_block.get("unit")
            raw_val = measurement.get("value")
            if raw_val is not None:
                try:
                    value = float(raw_val)
                except (ValueError, TypeError):
                    pass
            sensor_id = measurement.get("sensor_id") or measurement.get("sensors_id")

        # Event time
        event_time = datetime.now(UTC)
        period = measurement.get("period", {}) or {}
        dt_from = period.get("datetimeFrom", {}) or {}
        ts = dt_from.get("utc") or measurement.get("datetime") or measurement.get("date", {}).get("utc")
        if ts:
            try:
                event_time = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except ValueError:
                pass

        # Build a stable identifier
        param_key = str(parameter or "unknown")
        native_id = f"{loc_id}-{param_key}-{event_time.strftime('%Y%m%dT%H%M')}" if loc_id else (
            f"{lon:.4f}:{lat:.4f}-{param_key}"
        )
        dedupe = hashlib.sha256(f"openaq:{native_id}".encode()).hexdigest()[:16]

        attrs = AirQualityAttributes(
            location_id=int(loc_id) if loc_id is not None else None,
            location_name=loc_name,
            sensor_id=int(sensor_id) if sensor_id is not None else None,
            parameter=str(parameter) if parameter else None,
            display_name=str(display_name) if display_name else None,
            value=value,
            unit=str(unit) if unit else None,
            last_updated=event_time.isoformat(),
            is_mobile=loc.get("isMobile"),
            is_monitor=loc.get("isMonitor"),
            provider_name=(loc.get("provider") or {}).get("name") if isinstance(loc.get("provider"), dict) else None,
            country_code=(loc.get("country") or {}).get("code") if isinstance(loc.get("country"), dict) else None,
            locality=loc.get("locality"),
        )

        # Confidence: lower when measurement value is absent (location-only record)
        confidence = 0.85 if value is not None else 0.50

        return CanonicalEvent(
            event_id=make_event_id("openaq", native_id, event_time.isoformat()),
            source="openaq",
            source_type=SourceType.PUBLIC_RECORD,
            entity_type=EntityType.AIR_QUALITY_SENSOR,
            entity_id=native_id,
            event_type=EventType.AIR_QUALITY_OBSERVATION,
            event_time=event_time,
            geometry=geom,
            centroid=geom,
            confidence=confidence,
            quality_flags=["air-quality", param_key],
            attributes=attrs.model_dump(),
            normalization=NormalizationRecord(
                normalized_by="connector.openaq",
                dedupe_key=dedupe,
            ),
            provenance=ProvenanceRecord(
                raw_source_ref=f"openaq://locations/{loc_id}",
                source_record_id=native_id,
                source_url="https://openaq.org/",
            ),
            correlation_keys=CorrelationKeys(),
            license=_LICENSE,
        )

    def health(self) -> ConnectorHealthStatus:
        """Probe OpenAQ v3 API."""
        try:
            resp = httpx.get(
                f"{self._api_url}/locations",
                params={"limit": 1},
                headers=self._headers(),
                timeout=10.0,
            )
            resp.raise_for_status()
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=True,
                message=f"OpenAQ API reachable (HTTP {resp.status_code})",
                last_successful_poll=datetime.now(UTC),
            )
        except Exception as exc:
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=False,
                message=str(exc),
            )
