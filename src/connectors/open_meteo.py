"""Open-Meteo weather forecast connector.

Implements BaseConnector backed by the Open-Meteo free REST API.

connector_id: ``open-meteo``
source_type:  ``context_feed``

API: https://open-meteo.com/en/docs
No authentication required.  Open-Meteo provides free weather forecasts
worldwide and is licensed under Attribution 4.0 International (CC BY 4.0).
Commercial use is allowed with attribution.

This connector:
- Computes the centroid of the query AOI geometry.
- Requests a 24-hour hourly forecast for that centroid.
- Returns the next available forecast hour as a single ``weather_observation``
  CanonicalEvent summarising conditions relevant to GEOINT operations:
  cloud cover (affects optical imagery), precipitation, wind, temperature.

Hourly variables requested:
  cloud_cover, precipitation, wind_speed_10m, wind_direction_10m, temperature_2m

Returned event time_start / time_end span the requested forecast window.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
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
    SourceType,
    WeatherAttributes,
    make_event_id,
)

log = logging.getLogger(__name__)

_DEFAULT_API_URL = "https://api.open-meteo.com/v1"

# CC BY 4.0 — commercial use allowed with attribution.
_LICENSE = LicenseRecord(
    access_tier="public",
    commercial_use="allowed",
    redistribution="allowed",
    attribution_required=True,
)

_HOURLY_VARS = [
    "cloud_cover",
    "precipitation",
    "wind_speed_10m",
    "wind_direction_10m",
    "temperature_2m",
]


def _centroid_from_geojson(geometry: dict[str, Any]) -> tuple[float, float]:
    """Return (lon, lat) centroid of a GeoJSON geometry.

    Supports Point, Polygon, and MultiPolygon.
    """
    gtype = geometry.get("type", "")
    coords = geometry.get("coordinates", [])
    if gtype == "Point":
        return float(coords[0]), float(coords[1])
    if gtype == "Polygon" and coords:
        ring = coords[0]
        lons = [float(p[0]) for p in ring]
        lats = [float(p[1]) for p in ring]
        return sum(lons) / len(lons), sum(lats) / len(lats)
    if gtype == "MultiPolygon" and coords:
        ring = coords[0][0]
        lons = [float(p[0]) for p in ring]
        lats = [float(p[1]) for p in ring]
        return sum(lons) / len(lons), sum(lats) / len(lats)
    raise NormalizationError(f"Cannot compute centroid for geometry type {gtype!r}")


class OpenMeteoConnector(BaseConnector):
    """Open-Meteo — zero-auth global weather forecast connector.

    Produces a single ``weather_observation`` CanonicalEvent per AOI query,
    carrying the average forecast values over the first 6 hours from now.
    Cloud cover and precipitation are most operationally relevant for GEOINT
    imagery collection planning.
    """

    connector_id = "open-meteo"
    display_name = "Open-Meteo (Global Weather Forecast)"
    source_type = "context_feed"

    def __init__(
        self,
        *,
        api_url: str = _DEFAULT_API_URL,
        forecast_hours: int = 6,
        http_timeout: float = 30.0,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._forecast_hours = min(max(forecast_hours, 1), 24)
        self._http_timeout = http_timeout

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        """Verify Open-Meteo is reachable with a minimal forecast request."""
        try:
            resp = httpx.get(
                f"{self._api_url}/forecast",
                params={
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "hourly": "cloud_cover",
                    "forecast_days": 1,
                },
                timeout=10.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"Open-Meteo API unreachable: {exc}") from exc

    def fetch(
        self,
        geometry: dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        *,
        forecast_hours: int | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Fetch a short-range weather forecast for the AOI centroid.

        Returns a list with a single dict containing the raw Open-Meteo
        JSON response enriched with ``_centroid_lon`` / ``_centroid_lat``
        metadata for downstream normalize().
        """
        try:
            lon, lat = _centroid_from_geojson(geometry)
        except NormalizationError as exc:
            log.warning("Cannot derive centroid from geometry: %s", exc)
            return []

        params: dict[str, Any] = {
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "hourly": ",".join(_HOURLY_VARS),
            "wind_speed_unit": "ms",
            "forecast_days": 1,
            "timezone": "UTC",
        }
        try:
            resp = httpx.get(
                f"{self._api_url}/forecast",
                params=params,
                timeout=self._http_timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"Open-Meteo forecast failed: {exc}") from exc

        data = resp.json()
        data["_centroid_lon"] = lon
        data["_centroid_lat"] = lat
        data["_forecast_hours"] = forecast_hours or self._forecast_hours
        return [data]

    def normalize(self, raw: dict[str, Any]) -> CanonicalEvent:
        """Transform an Open-Meteo JSON response into a ``weather_observation`` CanonicalEvent."""
        lon: float = raw.get("_centroid_lon", 0.0)
        lat: float = raw.get("_centroid_lat", 0.0)
        n_hours: int = int(raw.get("_forecast_hours", self._forecast_hours))

        hourly = raw.get("hourly", {})
        times: list[str] = hourly.get("time", [])
        cloud: list[float | None] = hourly.get("cloud_cover", [])
        precip: list[float | None] = hourly.get("precipitation", [])
        wind_speed: list[float | None] = hourly.get("wind_speed_10m", [])
        wind_dir: list[float | None] = hourly.get("wind_direction_10m", [])
        temp: list[float | None] = hourly.get("temperature_2m", [])

        if not times:
            raise NormalizationError("Open-Meteo response contains no hourly time steps")

        # Average values over the first n_hours slots
        def _avg(values: list[float | None], n: int) -> float | None:
            vals = [v for v in values[:n] if v is not None]
            return sum(vals) / len(vals) if vals else None

        avg_cloud = _avg(cloud, n_hours)
        avg_precip = _avg(precip, n_hours)
        avg_wind_speed = _avg(wind_speed, n_hours)
        avg_wind_dir = _avg(wind_dir, n_hours)
        avg_temp = _avg(temp, n_hours)

        # Event time = first hourly time step
        try:
            event_time = datetime.fromisoformat(times[0].replace("Z", "+00:00"))
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=UTC)
        except (ValueError, IndexError):
            event_time = datetime.now(UTC)

        # time_end = last averaged slot
        try:
            last_idx = min(n_hours, len(times)) - 1
            time_end = datetime.fromisoformat(times[last_idx].replace("Z", "+00:00"))
            if time_end.tzinfo is None:
                time_end = time_end.replace(tzinfo=UTC)
        except (ValueError, IndexError):
            time_end = event_time + timedelta(hours=n_hours)

        attrs = WeatherAttributes(
            cloud_cover_pct=round(avg_cloud, 1) if avg_cloud is not None else None,
            precipitation_mm=round(avg_precip, 2) if avg_precip is not None else None,
            wind_speed_ms=round(avg_wind_speed, 2) if avg_wind_speed is not None else None,
            wind_direction_deg=round(avg_wind_dir, 1) if avg_wind_dir is not None else None,
            temperature_c=round(avg_temp, 1) if avg_temp is not None else None,
            forecast_horizon_hours=n_hours,
            weather_model=raw.get("hourly_units", {}).get("model", "open-meteo"),
        )

        centroid = {"type": "Point", "coordinates": [lon, lat]}
        dedupe = hashlib.sha256(
            f"open-meteo:{lat:.4f}:{lon:.4f}:{event_time.isoformat()}".encode()
        ).hexdigest()[:16]
        event_id = make_event_id("open-meteo", f"{lat:.4f}:{lon:.4f}", event_time.isoformat())

        return CanonicalEvent(
            event_id=event_id,
            source="open-meteo",
            source_type=SourceType.CONTEXT_FEED,
            entity_type=EntityType.SYSTEM,
            event_type=EventType.WEATHER_OBSERVATION,
            event_time=event_time,
            time_start=event_time,
            time_end=time_end,
            geometry=centroid,
            centroid=centroid,
            confidence=0.95,
            attributes=attrs.model_dump(),
            normalization=NormalizationRecord(
                normalized_by="connector.open_meteo",
                dedupe_key=dedupe,
            ),
            provenance=ProvenanceRecord(
                raw_source_ref=f"open-meteo://{lat:.4f},{lon:.4f}",
                source_url="https://open-meteo.com",
            ),
            correlation_keys=CorrelationKeys(),
            license=_LICENSE,
        )

    def health(self) -> ConnectorHealthStatus:
        """Lightweight health probe — fetch a single hourly slot for null island."""
        try:
            resp = httpx.get(
                f"{self._api_url}/forecast",
                params={
                    "latitude": 51.5,
                    "longitude": 0.1,
                    "hourly": "cloud_cover",
                    "forecast_days": 1,
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=True,
                message=f"Open-Meteo reachable (HTTP {resp.status_code})",
                last_successful_poll=datetime.now(UTC),
            )
        except Exception as exc:
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=False,
                message=str(exc),
            )
