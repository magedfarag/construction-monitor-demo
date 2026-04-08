"""ACLED Armed Conflict Location & Event Data connector.

Implements BaseConnector backed by the ACLED REST API using OAuth2 authentication.

connector_id: ``acled``
source_type:  ``public_record``

API: https://acleddata.com/api-documentation/getting-started
Free account required at https://acleddata.com/

Features:
- OAuth2 password grant authentication with Bearer token
- Geographic queries via centroid + radius derived from AOI geometry.
- Date-range filtering aligned with the fetch() time window.
- Normalises ACLED event records → ``conflict_event`` CanonicalEvents.
- Sub-event type taxonomy maps to confidence scores:
    Air/drone strike, Shelling/artillery  → 0.95
    Battles (armed clash)                 → 0.90
    IED / Remote explosive                → 0.88
    Violence against civilians            → 0.85
    Riots, Protests                       → 0.70
    Strategic developments               → 0.75

Configure via environment variables:
  ACLED_EMAIL      — Registered email for ACLED account (required)
  ACLED_PASSWORD   — Password for ACLED account (required)
  ACLED_TOKEN_URL  — OAuth2 token endpoint (default: https://acleddata.com/oauth/token)
  ACLED_API_URL    — API endpoint (default: https://acleddata.com/api/acled/read)

Non-commercial use clause: ACLED data is free for non-commercial research.
Commercial use requires a separate agreement with ACLED.
"""
from __future__ import annotations

import hashlib
import logging
import math
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
    ConflictAttributes,
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

_DEFAULT_TOKEN_URL = "https://acleddata.com/oauth/token"
_DEFAULT_API_URL = "https://acleddata.com/api/acled/read"

_LICENSE = LicenseRecord(
    access_tier="public",
    commercial_use="allowed-with-terms",
    redistribution="check-provider-terms",
    attribution_required=True,
)

# ACLED sub-event-type → confidence scoring
_SUB_TYPE_CONFIDENCE: dict[str, float] = {
    "Air/drone strike": 0.95,
    "Shelling/artillery/missile attack": 0.95,
    "Remote explosive/landmine/IED": 0.88,
    "Suicide bomb": 0.88,
    "Armed clash": 0.90,
    "Government regains territory": 0.80,
    "Non-state actor overtakes territory": 0.80,
    "Attack": 0.85,
    "Abduction/forced disappearance": 0.82,
    "Sexual violence": 0.82,
    "Looting/property destruction": 0.75,
    "Violent demonstration": 0.70,
    "Mob violence": 0.70,
    "Peaceful protest": 0.65,
    "Protest with intervention": 0.65,
    "Excessive force against protesters": 0.72,
    "Arrests": 0.70,
    "Disrupted weapons use": 0.78,
    "Headquarters or base established": 0.75,
    "Non-violent transfer of territory": 0.75,
    "Agreement": 0.70,
}
_DEFAULT_CONFIDENCE = 0.75


def _geojson_to_centroid_radius(
    geometry: dict[str, Any],
) -> tuple[float, float, float]:
    """Return (lat, lon, radius_km) from a GeoJSON geometry.

    Radius is the half-diagonal of the bounding box, clamped to [10, 2000] km.
    """
    gtype = geometry.get("type", "")
    coords_flat: list[list[float]] = []
    if gtype == "Point":
        c = geometry["coordinates"]
        return float(c[1]), float(c[0]), 50.0
    if gtype == "Polygon":
        coords_flat = geometry["coordinates"][0]
    elif gtype == "MultiPolygon":
        for poly in geometry["coordinates"]:
            coords_flat.extend(poly[0])
    else:
        raise NormalizationError(f"Unsupported geometry type: {gtype!r}")
    lons = [float(c[0]) for c in coords_flat]
    lats = [float(c[1]) for c in coords_flat]
    center_lat = (min(lats) + max(lats)) / 2.0
    center_lon = (min(lons) + max(lons)) / 2.0
    # Haversine approximation for half-diagonal
    dlat = math.radians(max(lats) - min(lats))
    dlon = math.radians(max(lons) - min(lons))
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(min(lats))) * math.cos(math.radians(max(lats)))
         * math.sin(dlon / 2) ** 2)
    radius_km = max(10.0, min(2000.0, 6371.0 * 2 * math.asin(math.sqrt(a)) / 2))
    return center_lat, center_lon, round(radius_km, 1)


class AcledConnector(BaseConnector):
    """ACLED Armed Conflict Location & Event Data connector.

    Produces ``conflict_event`` CanonicalEvents for armed clashes,
    air/drone strikes, explosions, and civilian violence. Highly relevant
    for MENA/Gulf intelligence: covers Yemen, Iraq, Syria, Lebanon,
    Saudi Arabia, UAE, and surrounding regions.
    
    Uses OAuth2 password grant flow for authentication.
    """

    connector_id = "acled"
    display_name = "ACLED (Armed Conflict Location & Event Data)"
    source_type = "public_record"

    def __init__(
        self,
        *,
        email: str,
        password: str,
        token_url: str = _DEFAULT_TOKEN_URL,
        api_url: str = _DEFAULT_API_URL,
        http_timeout: float = 30.0,
    ) -> None:
        if not email:
            raise ValueError("ACLED requires a registered email")
        if not password:
            raise ValueError("ACLED requires a password")
        self._email = email
        self._password = password
        self._token_url = token_url
        self._api_url = api_url
        self._http_timeout = http_timeout
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    def _get_access_token(self) -> str:
        """Get OAuth2 access token using password grant flow.
        
        Caches token until it expires (24 hours per ACLED docs).
        """
        # Return cached token if still valid
        if self._access_token and self._token_expires_at:
            if datetime.now(UTC) < self._token_expires_at:
                return self._access_token
        
        # Request new access token
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "username": self._email,
            "password": self._password,
            "grant_type": "password",
            "client_id": "acled",
        }
        
        try:
            resp = httpx.post(self._token_url, headers=headers, data=data, timeout=15.0)
            resp.raise_for_status()
            token_data = resp.json()
            
            access_token = token_data["access_token"]
            self._access_token = access_token
            # Token expires in 86400 seconds (24 hours), refresh 5 minutes early
            expires_in = token_data.get("expires_in", 86400)
            self._token_expires_at = datetime.now(UTC).replace(
                microsecond=0
            ) + timedelta(seconds=expires_in - 300)
            
            return access_token
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(
                f"Failed to get ACLED access token: {exc}"
            ) from exc
        except (KeyError, ValueError) as exc:
            raise ConnectorUnavailableError(
                f"Invalid ACLED token response: {exc}"
            ) from exc

    def _auth_headers(self) -> dict[str, str]:
        """Return headers with Bearer token for authenticated requests."""
        token = self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        """Verify ACLED OAuth2 credentials with a minimal query (limit=1)."""
        params: dict[str, Any] = {
            "_format": "json",
            "limit": 1,
            "fields": "event_id_cnty|event_date",
        }
        try:
            resp = httpx.get(
                self._api_url,
                params=params,
                headers=self._auth_headers(),
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != 200:
                raise ConnectorUnavailableError(
                    f"ACLED auth failed: {data.get('message', data)}"
                )
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"ACLED API unreachable: {exc}") from exc

    def fetch(
        self,
        geometry: dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        *,
        max_results: int = 200,
        event_types: list[str] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Fetch ACLED conflict events intersecting the AOI and time window.

        Uses centroid + radius derived from the GeoJSON geometry.
        Returns raw ACLED event dicts.
        """
        try:
            lat, lon, radius_km = _geojson_to_centroid_radius(geometry)
        except NormalizationError as exc:
            log.warning("Cannot derive centroid from geometry: %s", exc)
            return []

        date_from = start_time.strftime("%Y-%m-%d")
        date_to = end_time.strftime("%Y-%m-%d")

        params: dict[str, Any] = {
            "_format": "json",
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "radius": round(radius_km, 1),
            "event_date": f"{date_from}|{date_to}",
            "event_date_where": "BETWEEN",
            "limit": min(max_results, 500),
            "order": "event_date",
            "order_ascending": 0,
        }
        if event_types:
            params["event_type"] = "|".join(event_types)

        try:
            resp = httpx.get(
                self._api_url,
                params=params,
                headers=self._auth_headers(),
                timeout=self._http_timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"ACLED fetch failed: {exc}") from exc

        payload = resp.json()
        if payload.get("status") != 200:
            raise ConnectorUnavailableError(
                f"ACLED API error: {payload.get('message', payload)}"
            )
        records = payload.get("data", [])
        log.debug("ACLED: %d events returned for bbox (lat=%.4f lon=%.4f r=%.1f km)",
                  len(records), lat, lon, radius_km)
        return records

    def normalize(self, raw: dict[str, Any]) -> CanonicalEvent:
        """Transform an ACLED event dict into a ``conflict_event`` CanonicalEvent."""
        event_id_native: str = raw.get("event_id_cnty", "")
        if not event_id_native:
            raise NormalizationError("ACLED record missing 'event_id_cnty'")

        # Parse date
        date_str: str = raw.get("event_date", "")
        if not date_str:
            raise NormalizationError(f"ACLED event {event_id_native!r} missing 'event_date'")
        try:
            event_time = datetime.strptime(date_str, "%Y-%m-%d").replace(
                hour=12, tzinfo=UTC
            )
        except ValueError as exc:
            raise NormalizationError(
                f"Cannot parse ACLED date {date_str!r}: {exc}"
            ) from exc

        # Coordinates
        try:
            lat = float(raw["latitude"])
            lon = float(raw["longitude"])
        except (KeyError, ValueError, TypeError) as exc:
            raise NormalizationError(
                f"ACLED event {event_id_native!r} has invalid coordinates: {exc}"
            ) from exc

        geom_point = {"type": "Point", "coordinates": [lon, lat]}

        # Sub-event detail
        event_type_acled: str = raw.get("event_type", "")
        sub_event_type: str = raw.get("sub_event_type", "")
        confidence = _SUB_TYPE_CONFIDENCE.get(sub_event_type, _DEFAULT_CONFIDENCE)

        attrs = ConflictAttributes(
            acled_event_id=event_id_native or None,
            disorder_type=raw.get("disorder_type") or None,
            event_type=event_type_acled or None,
            sub_event_type=sub_event_type or None,
            actor1=raw.get("actor1") or None,
            actor2=raw.get("actor2") or None,
            country=raw.get("country") or None,
            admin1=raw.get("admin1") or None,
            location=raw.get("location") or None,
            fatalities=int(raw["fatalities"]) if raw.get("fatalities") is not None else None,
            source=raw.get("source") or None,
            notes=raw.get("notes") or None,
            civilian_targeting=raw.get("civilian_targeting") or None,
        )

        dedupe = hashlib.sha256(
            f"acled:{event_id_native}:{date_str}".encode()
        ).hexdigest()[:16]
        canonical_id = make_event_id("acled", event_id_native, event_time.isoformat())

        return CanonicalEvent(
            event_id=canonical_id,
            source="acled",
            source_type=SourceType.PUBLIC_RECORD,
            entity_type=EntityType.CONFLICT_INCIDENT,
            entity_id=event_id_native,
            event_type=EventType.CONFLICT_EVENT,
            event_time=event_time,
            geometry=geom_point,
            centroid=geom_point,
            confidence=confidence,
            attributes=attrs.model_dump(),
            normalization=NormalizationRecord(
                normalized_by="connector.acled",
                dedupe_key=dedupe,
            ),
            provenance=ProvenanceRecord(
                raw_source_ref=f"acled://events/{event_id_native}",
                source_record_id=event_id_native,
                source_url="https://acleddata.com/data-export-tool/",
            ),
            correlation_keys=CorrelationKeys(
                place_key=f"{raw.get('country', 'XX').upper().replace(' ', '-')}-{raw.get('admin1', '').upper().replace(' ', '-')}"
                if raw.get("country") else None,
            ),
            license=_LICENSE,
        )

    def health(self) -> ConnectorHealthStatus:
        """Lightweight health probe — minimal authenticated query."""
        try:
            params = {"_format": "json", "limit": 1, "fields": "event_id_cnty"}
            resp = httpx.get(
                self._api_url,
                params=params,
                headers=self._auth_headers(),
                timeout=10.0,
            )
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("status") != 200:
                return ConnectorHealthStatus(
                    connector_id=self.connector_id,
                    healthy=False,
                    message=f"ACLED auth error: {payload.get('message', '')}",
                )
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=True,
                message=f"ACLED reachable (HTTP {resp.status_code})",
                last_successful_poll=datetime.now(UTC),
            )
        except Exception as exc:
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=False,
                message=str(exc),
            )
