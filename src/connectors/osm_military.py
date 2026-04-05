"""OpenStreetMap Overpass API — Military Features connector.

Implements BaseConnector backed by the public Overpass API.

connector_id: ``osm-military``
source_type:  ``public_record``

API: https://overpass-api.de/api/interpreter (POST)
No authentication required.  OSM data is licensed under ODbL 1.0 (Open
Database License); derived data must carry the same licence and attribute
© OpenStreetMap contributors.

Queried OSM feature types (military and related):
  military=airfield         — Military airfield
  military=base             — Military base / installation
  military=naval_base       — Naval base / port
  military=camp             — Military camp / staging area
  military=barracks         — Barracks
  military=bunker           — Hardened shelter / command bunker
  military=checkpoint       — Military checkpoint / border crossing
  military=range            — Artillery / firing range
  military=training_area    — Military training zone
  military=weapons_range    — Small arms / weapons range
  landuse=military          — Military land area (general)
  aeroway=aerodrome + military=* — Military airfield (combined tag)

Results are clipped to the query AOI bounding box.  Each feature produces
one ``military_site_observation`` CanonicalEvent.

Rate-limit guidance: Overpass public server recommends ≤1 req/2 s.
Heavy queries should use the custom Overpass instance environment variable.

Configure via environment variables (optional):
  OSM_OVERPASS_URL — Override endpoint (default: https://overpass-api.de/api/interpreter)
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
    MilitaryFeatureAttributes,
    NormalizationRecord,
    ProvenanceRecord,
    SourceType,
    make_event_id,
)

log = logging.getLogger(__name__)

_DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# ODbL 1.0 — redistribution requires: same licence + attribution
_LICENSE = LicenseRecord(
    access_tier="public",
    commercial_use="allowed-with-terms",
    redistribution="allowed",
    attribution_required=True,
)

# Military type values we surface in ARGUS.
# Keep list focused on operationally significant sites.
_MILITARY_TYPES = [
    "airfield",
    "base",
    "naval_base",
    "camp",
    "barracks",
    "bunker",
    "checkpoint",
    "range",
    "training_area",
    "weapons_range",
    "port",
    "office",
]

# Friendly display labels
_MILITARY_LABELS: dict[str, str] = {
    "airfield":      "Military Airfield",
    "base":          "Military Base",
    "naval_base":    "Naval Base",
    "camp":          "Military Camp",
    "barracks":      "Barracks",
    "bunker":        "Hardened Bunker",
    "checkpoint":    "Military Checkpoint",
    "range":         "Firing/Artillery Range",
    "training_area": "Training Area",
    "weapons_range": "Weapons Range",
    "port":          "Military Port",
    "office":        "Military Office",
}


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


def _build_overpass_query(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    timeout: int = 30,
) -> str:
    """Build an Overpass QL query for military features in the given bbox."""
    bbox = f"{min_lat},{min_lon},{max_lat},{max_lon}"
    return (
        f"[bbox:{bbox}][out:json][timeout:{timeout}];\n"
        "(\n"
        f"  node[military];\n"
        f"  way[military];\n"
        f"  relation[military];\n"
        f"  way[landuse=military];\n"
        f"  relation[landuse=military];\n"
        ");\n"
        "out center;"
    )


def _extract_center(element: dict[str, Any]) -> tuple[float, float] | None:
    """Return (lon, lat) for an Overpass element (node, way, or relation)."""
    etype = element.get("type", "")
    if etype == "node":
        lat = element.get("lat")
        lon = element.get("lon")
        if lat is not None and lon is not None:
            return float(lon), float(lat)
    else:
        # way and relation have a 'center' block after `out center`
        center = element.get("center", {})
        lat = center.get("lat")
        lon = center.get("lon")
        if lat is not None and lon is not None:
            return float(lon), float(lat)
    return None


class OsmMilitaryConnector(BaseConnector):
    """OpenStreetMap military features — static infrastructure connector.

    Produces ``military_site_observation`` CanonicalEvents for military
    installations within the query AOI. Particularly useful for Gulf/MENA:
    - Saudi RSAF airbases (Dhahran, Tabuk, Khamis Mushayt)
    - UAE airbases (Al-Dhafra, Al-Bateen)
    - Qatar Al-Udeid Air Base
    - Bahrain NSA (US 5th Fleet HQ)
    - Iranian IRGC naval bases in the Gulf
    - Israeli Air Force bases (if AOI includes Levant)

    Note: OSM data reflects what mappers have tagged. Coverage of sensitive
    military installations is inherently incomplete — use as context layer.
    """

    connector_id = "osm-military"
    display_name = "OpenStreetMap Military Features"
    source_type = "public_record"

    def __init__(
        self,
        *,
        overpass_url: str = _DEFAULT_OVERPASS_URL,
        http_timeout: float = 60.0,
    ) -> None:
        self._overpass_url = overpass_url
        self._http_timeout = http_timeout

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        """Verify Overpass API is reachable."""
        # Lightweight test query: single node in null island bbox
        test_query = "[bbox:0,0,0.001,0.001][out:json][timeout:5];node[military];out;"
        try:
            resp = httpx.post(
                self._overpass_url,
                data={"data": test_query},
                timeout=15.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"Overpass API unreachable: {exc}") from exc

    def fetch(
        self,
        geometry: dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        *,
        max_results: int = 500,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Fetch military features within the AOI bounding box.

        Time parameters are not used by Overpass (OSM is current-state).
        Returns raw Overpass element dicts.
        """
        try:
            min_lat, min_lon, max_lat, max_lon = _bbox_from_geojson(geometry)
        except NormalizationError as exc:
            log.warning("Cannot derive bbox from geometry: %s", exc)
            return []

        query = _build_overpass_query(
            min_lat, min_lon, max_lat, max_lon,
            timeout=int(self._http_timeout),
        )
        try:
            resp = httpx.post(
                self._overpass_url,
                data={"data": query},
                timeout=self._http_timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"Overpass query failed: {exc}") from exc

        elements = resp.json().get("elements", [])
        log.debug("OSM Overpass: %d military elements returned for bbox", len(elements))
        return elements[:max_results]

    def normalize(self, raw: dict[str, Any]) -> CanonicalEvent:
        """Transform an Overpass element into a ``military_site_observation`` CanonicalEvent."""
        osm_type = raw.get("type", "")
        raw_id = raw.get("id")
        if not raw_id:
            raise NormalizationError("Overpass element missing 'id'")
        osm_id = str(raw_id)

        tags = raw.get("tags", {})
        military_type = tags.get("military") or (
            "military_area" if tags.get("landuse") == "military" else None
        )
        name = tags.get("name") or tags.get("name:en") or None
        operator = tags.get("operator") or tags.get("owner") or None

        # Extract coordinates
        pt = _extract_center(raw)
        if pt is None:
            raise NormalizationError(
                f"Overpass element {osm_id!r} ({osm_type}) has no usable coordinates"
            )
        lon, lat = pt

        geom_point = {"type": "Point", "coordinates": [lon, lat]}
        now = datetime.now(UTC)

        # Exclude non-significant tags (keep only military-relevant ones)
        extra_tags = {
            k: str(v) for k, v in tags.items()
            if k not in ("military", "landuse", "name", "name:en", "operator", "owner")
            and not k.startswith("source")
            and not k.startswith("note")
        }

        attrs = MilitaryFeatureAttributes(
            osm_id=osm_id,
            osm_type=osm_type,
            military_type=military_type or None,
            name=name,
            operator=operator,
            additional_tags=extra_tags,
        )

        native_id = f"{osm_type}/{osm_id}"
        dedupe = hashlib.sha256(f"osm-military:{native_id}".encode()).hexdigest()[:16]
        event_id = make_event_id("osm-military", native_id, now.isoformat())

        return CanonicalEvent(
            event_id=event_id,
            source="osm-military",
            source_type=SourceType.PUBLIC_RECORD,
            entity_type=EntityType.MILITARY_INSTALLATION,
            entity_id=native_id,
            event_type=EventType.MILITARY_SITE_OBSERVATION,
            event_time=now,
            geometry=geom_point,
            centroid=geom_point,
            confidence=0.70,  # OSM coverage of military sites is inherently incomplete
            quality_flags=["osm-community-mapped", "static-infrastructure"],
            attributes=attrs.model_dump(),
            normalization=NormalizationRecord(
                normalized_by="connector.osm.military",
                dedupe_key=dedupe,
            ),
            provenance=ProvenanceRecord(
                raw_source_ref=f"osm://{native_id}",
                source_record_id=native_id,
                source_url=f"https://www.openstreetmap.org/{native_id}",
            ),
            correlation_keys=CorrelationKeys(),
            license=_LICENSE,
        )

    def health(self) -> ConnectorHealthStatus:
        """Lightweight health probe against Overpass API."""
        try:
            test_query = "[bbox:0,0,1,1][out:json][timeout:5];node[military];out;"
            resp = httpx.post(
                self._overpass_url,
                data={"data": test_query},
                timeout=15.0,
            )
            resp.raise_for_status()
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=True,
                message=f"Overpass API reachable (HTTP {resp.status_code})",
                last_successful_poll=datetime.now(UTC),
            )
        except Exception as exc:
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=False,
                message=str(exc),
            )
