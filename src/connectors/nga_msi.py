"""NGA Maritime Safety Information (MSI) — Broadcast Warnings to Mariners connector.

Implements BaseConnector backed by the US National Geospatial-Intelligence Agency
public MSI API.

connector_id: ``nga-msi``
source_type:  ``public_record``

API: https://msi.nga.mil/api/publications/broadcast-warn
No authentication required — public US government data.
Data is produced by US military naval commands (COMNAVMARIANAS, 5th Fleet, etc.)
and is in the public domain.

Broadcast Warnings include:
- Anti-piracy alerts (Gulf of Aden, Red Sea, Persian Gulf, Strait of Hormuz)
- Military exercise areas (exclusion zones, restricted firing)
- Minefields — historical and active
- Navigation hazards (wrecks, debris)
- Search-and-rescue operations in military zones

NAVAREA coverage relevant to Gulf / MENA:
  NAVAREA IX  — Arabian Sea, Persian Gulf, Red Sea, Gulf of Aden
  NAVAREA III — Mediterranean (Eastern Mediterranean / Levant)
  NAVAREA XI  — East Asian Waters

The connector fetches active warnings for configured NAVAREAs, then
applies client-side AOI bounding-box filtering when the warning carries
a parseable coordinate pair in its metadata.

Configure via environment variables (optional):
  NGA_MSI_API_URL           (default: https://msi.nga.mil/api/publications/broadcast-warn)
  NGA_MSI_DEFAULT_NAV_AREAS (default: IX,III — Gulf + Mediterranean)
"""
from __future__ import annotations

import hashlib
import logging
import re
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
    MaritimeWarningAttributes,
    NormalizationRecord,
    ProvenanceRecord,
    SourceType,
    make_event_id,
)

log = logging.getLogger(__name__)

_DEFAULT_API_URL = "https://msi.nga.mil/api/publications/broadcast-warn"

# US Government-produced data: public domain.
_LICENSE = LicenseRecord(
    access_tier="public",
    commercial_use="allowed",
    redistribution="allowed",
    attribution_required=True,
)

# Approximate bounding boxes for NAVAREA codes.
# Used to map an AOI centroid to the most relevant NAVAREA(s).
# Format: (min_lon, min_lat, max_lon, max_lat)
_NAVAREA_BOUNDS: dict[str, tuple[float, float, float, float]] = {
    "IX":    (32.0,  5.0,  80.0, 32.0),   # Arabian Sea, Persian Gulf, Red Sea
    "III":   (-6.0, 29.0,  42.0, 48.0),   # Mediterranean
    "XI":   (100.0, -15.0, 180.0, 45.0),  # East Asian Waters
    "X":    (90.0,  -15.0, 135.0, 25.0),  # South-East Asia
    "I":    (-50.0,  0.0,  30.0, 72.0),   # North-East Atlantic (UK NAVAREA)
    "IV":   (-100.0, 0.0, -30.0, 65.0),   # North-Central Atlantic (US)
    "II":    (-30.0, 0.0,  30.0, 72.0),   # North-East Atlantic (Norway)
    "XII":  (-180.0, 0.0, -115.0, 65.0),  # North Pacific
}

# Representative centroid (lon, lat) per NAVAREA — used as fallback geometry
_NAVAREA_CENTROIDS: dict[str, tuple[float, float]] = {
    "IX":  (56.0,  20.0),
    "III": (15.0,  38.0),
    "XI":  (140.0, 25.0),
    "X":   (115.0,  8.0),
    "I":   (-20.0, 50.0),
    "IV":  (-60.0, 35.0),
    "II":   (5.0,  60.0),
    "XII": (-150.0, 45.0),
}

# Regex to extract DDMM.m N/S DDDMM.m E/W from warning text
_COORD_RE = re.compile(
    r"(\d{1,2})-(\d{1,2}(?:\.\d+)?)\s*([NS])\s+"
    r"(\d{1,3})-(\d{1,2}(?:\.\d+)?)\s*([EW])"
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


def _navarea_from_centroid(lon: float, lat: float) -> str | None:
    """Return the NAVAREA code whose bounding box contains (lon, lat)."""
    for code, (min_lon, min_lat, max_lon, max_lat) in _NAVAREA_BOUNDS.items():
        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
            return code
    return None


def _parse_first_coord_from_text(text: str) -> tuple[float, float] | None:
    """Extract the first DM coordinate from maritime warning text.

    Returns (lon, lat) or None if no parseable coordinate found.
    """
    if not text:
        return None
    m = _COORD_RE.search(text)
    if not m:
        return None
    try:
        lat_deg = int(m.group(1))
        lat_min = float(m.group(2))
        lat_hemi = m.group(3)
        lon_deg = int(m.group(4))
        lon_min = float(m.group(5))
        lon_hemi = m.group(6)
        lat = lat_deg + lat_min / 60.0
        if lat_hemi == "S":
            lat = -lat
        lon = lon_deg + lon_min / 60.0
        if lon_hemi == "W":
            lon = -lon
        return lon, lat
    except (ValueError, IndexError):
        return None


class NgaMsiConnector(BaseConnector):
    """NGA Broadcast Warnings to Mariners — military maritime intelligence connector.

    Returns ``maritime_warning`` CanonicalEvents for active broadcast
    warnings in configured NAVAREAs. Particularly relevant for:
    - Strait of Hormuz transit alerts (NAVAREA IX)
    - Red Sea / Gulf of Aden anti-piracy / Houthi activity
    - Naval exercise exclusion zones (Eastern Mediterranean — NAVAREA III)
    """

    connector_id = "nga-msi"
    display_name = "NGA Maritime Safety Information (Broadcast Warnings)"
    source_type = "public_record"

    def __init__(
        self,
        *,
        api_url: str = _DEFAULT_API_URL,
        default_nav_areas: list[str] | None = None,
        http_timeout: float = 30.0,
    ) -> None:
        self._api_url = api_url
        self._default_nav_areas = default_nav_areas or ["IX", "III"]
        self._http_timeout = http_timeout

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        """Verify NGA MSI API is reachable with a minimal request."""
        try:
            resp = httpx.get(
                self._api_url,
                params={"output": "json", "includePublications": "true",
                        "status": "active", "navArea": "IX"},
                timeout=15.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"NGA MSI API unreachable: {exc}") from exc

    def fetch(
        self,
        geometry: dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        *,
        nav_areas: list[str] | None = None,
        max_results: int = 200,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Fetch active broadcast warnings for the AOI.

        Determines relevant NAVAREAs from the geometry centroid, then fetches
        warnings and filters them to the AOI bounding box where coordinates
        are parseable.
        """
        # Determine which NAVAREAs to query
        areas = nav_areas or self._default_nav_areas
        if not areas:
            # Fall back: auto-detect from centroid
            try:
                min_lat, min_lon, max_lat, max_lon = _bbox_from_geojson(geometry)
                detected = _navarea_from_centroid(
                    (min_lon + max_lon) / 2.0, (min_lat + max_lat) / 2.0
                )
                areas = [detected] if detected else ["IX"]
            except NormalizationError:
                areas = ["IX"]

        all_warnings: list[dict[str, Any]] = []
        for nav_area in areas:
            params: dict[str, Any] = {
                "output": "json",
                "includePublications": "true",
                "status": "active",
                "navArea": nav_area,
            }
            try:
                resp = httpx.get(
                    self._api_url,
                    params=params,
                    timeout=self._http_timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                warnings = data.get("broadcastWarn", [])
                log.debug("NGA MSI NAVAREA %s: %d active warnings", nav_area, len(warnings))
                all_warnings.extend(warnings)
            except httpx.HTTPError as exc:
                log.warning("NGA MSI fetch for NAVAREA %s failed: %s", nav_area, exc)

        if not all_warnings:
            return []

        # Client-side bbox filter where coordinates are available
        try:
            min_lat, min_lon, max_lat, max_lon = _bbox_from_geojson(geometry)
            bbox_available = True
        except NormalizationError:
            bbox_available = False

        filtered: list[dict[str, Any]] = []
        for warning in all_warnings[:1000]:  # cap to prevent memory issues
            if bbox_available:
                # Try metadata lat/lon first
                w_lat = warning.get("latitude")
                w_lon = warning.get("longitude")
                if w_lat is not None and w_lon is not None:
                    try:
                        if not (min_lat <= float(w_lat) <= max_lat
                                and min_lon <= float(w_lon) <= max_lon):
                            continue
                    except (ValueError, TypeError):
                        pass
                else:
                    # Try parsing from warning text
                    pt = _parse_first_coord_from_text(warning.get("text", ""))
                    if pt:
                        p_lon, p_lat = pt
                        if not (min_lat <= p_lat <= max_lat and min_lon <= p_lon <= max_lon):
                            continue
                    # No coordinates — include by default (NAVAREA inclusion is enough)
            filtered.append(warning)

        log.debug("NGA MSI: %d warnings after bbox filter", len(filtered))
        return filtered[:max_results]

    def normalize(self, raw: dict[str, Any]) -> CanonicalEvent:
        """Transform an NGA MSI broadcast warning into a ``maritime_warning`` CanonicalEvent."""
        msg_year = str(raw.get("msgYear", raw.get("year", "")))
        msg_num = str(raw.get("msgNumber", ""))
        authority = str(raw.get("authority", ""))
        nav_area = str(raw.get("navArea", ""))
        nav_area_code = str(raw.get("navAreaCode", nav_area))
        subregion = str(raw.get("subregion", ""))
        region = str(raw.get("region", ""))
        warning_text = str(raw.get("text", ""))
        status = str(raw.get("status", "Active"))
        cancel_date = raw.get("cancelDate")
        issue_date = raw.get("issueDate") or raw.get("year")

        if not msg_year or not msg_num:
            raise NormalizationError(
                f"NGA MSI warning missing year/number: {raw!r}"
            )

        native_id = f"{nav_area_code}-{msg_year}-{msg_num}"

        # Determine geometry: prefer API lat/lon, fall back to text parse, then NAVAREA centroid
        lon: float | None = None
        lat: float | None = None
        w_lat = raw.get("latitude")
        w_lon = raw.get("longitude")
        if w_lat is not None and w_lon is not None:
            try:
                lat, lon = float(w_lat), float(w_lon)
            except (ValueError, TypeError):
                pass
        if lat is None:
            pt = _parse_first_coord_from_text(warning_text)
            if pt:
                lon, lat = pt
        if lat is None:
            centroid_coords = _NAVAREA_CENTROIDS.get(nav_area_code.upper(), (0.0, 0.0))
            lon, lat = centroid_coords

        geom_point = {"type": "Point", "coordinates": [lon, lat]}

        # Event time: use issue date if available, else now
        event_time = datetime.now(UTC)
        if issue_date:
            try:
                event_time = datetime.strptime(
                    str(issue_date).split("T")[0], "%Y-%m-%d"
                ).replace(tzinfo=UTC)
            except ValueError:
                pass

        attrs = MaritimeWarningAttributes(
            nav_area=nav_area or None,
            nav_area_code=nav_area_code or None,
            subregion=subregion or None,
            region=region or None,
            authority=authority or None,
            msg_year=msg_year or None,
            msg_number=msg_num or None,
            cancel_date=str(cancel_date) if cancel_date else None,
            issue_date=str(issue_date) if issue_date else None,
            warning_text=warning_text[:2000] if warning_text else None,  # cap text length
            status=status or None,
        )

        dedupe = hashlib.sha256(
            f"nga-msi:{native_id}".encode()
        ).hexdigest()[:16]
        event_id = make_event_id("nga-msi", native_id, event_time.isoformat())

        return CanonicalEvent(
            event_id=event_id,
            source="nga-msi",
            source_type=SourceType.PUBLIC_RECORD,
            entity_type=EntityType.MARITIME_ZONE,
            entity_id=native_id,
            event_type=EventType.MARITIME_WARNING,
            event_time=event_time,
            geometry=geom_point,
            centroid=geom_point,
            confidence=0.98,  # official military/government source
            attributes=attrs.model_dump(),
            normalization=NormalizationRecord(
                normalized_by="connector.nga.msi",
                dedupe_key=dedupe,
            ),
            provenance=ProvenanceRecord(
                raw_source_ref=f"nga-msi://{native_id}",
                source_record_id=native_id,
                source_url="https://msi.nga.mil/NavWarnings",
            ),
            correlation_keys=CorrelationKeys(),
            license=_LICENSE,
        )

    def health(self) -> ConnectorHealthStatus:
        """Lightweight health probe against the NGA MSI API."""
        try:
            resp = httpx.get(
                self._api_url,
                params={"output": "json", "includePublications": "true",
                        "status": "active", "navArea": "IX"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            count = len(data.get("broadcastWarn", []))
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=True,
                message=f"NGA MSI reachable — {count} NAVAREA IX warnings",
                last_successful_poll=datetime.now(UTC),
            )
        except Exception as exc:
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=False,
                message=str(exc),
            )
