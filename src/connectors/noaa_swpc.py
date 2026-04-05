"""NOAA Space Weather Prediction Center (SWPC) connector.

Implements BaseConnector backed by the NOAA SWPC JSON alert feed.

connector_id: ``noaa-swpc``
source_type:  ``public_record``

API: https://services.swpc.noaa.gov/products/alerts.json
No authentication required — public US Government data (public domain).

Space weather events produced by SWPC affect:
- Satellite communications (HF, UHF/SHF cross-polar links)
- GPS positioning accuracy (ionospheric scintillation)
- HF radar performance (OTHR / JORN affected by D-layer absorption)
- Power grid and long-line infrastructure
- Radiation dose for high-altitude platforms and reconnaissance aircraft

Event families:
  G-scale (G1–G5) — Geomagnetic storms (HF/GPS disruption)
  S-scale (S1–S5) — Solar radiation storms (satellite/astronaut hazard)
  R-scale (R1–R5) — Radio blackouts (HF comms disruption)

NOAA SWPC product codes (partial list):
  ALTEF3 — Enhanced electron flux
  ALTP   — Proton event
  ALTXM  — X-class solar flare
  WATA   — Geomagnetic activity watch
  WARK   — K-index warning
  SUMX   — Solar flare summary
  GEOMAG — Geomagnetic storm

Space weather events carry no geographic centroid (they are global
phenomena). The canonical event is given a null-island geometry (0°, 0°)
with a ``global-phenomenon`` quality flag. Consumers should treat these as
context-layer events, not point-source detections.

Configure via environment variable (optional):
  NOAA_SWPC_API_URL — Override endpoint (default: https://services.swpc.noaa.gov)
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
    NormalizationRecord,
    ProvenanceRecord,
    SourceType,
    SpaceWeatherAttributes,
    make_event_id,
)

log = logging.getLogger(__name__)

_DEFAULT_API_URL = "https://services.swpc.noaa.gov"
_ALERTS_PATH = "/products/alerts.json"

# NOAA SWPC data: US Government, public domain.
_LICENSE = LicenseRecord(
    access_tier="public",
    commercial_use="allowed",
    redistribution="allowed",
    attribution_required=True,
)

# Product ID prefix → human-readable phenomenon label
_PRODUCT_PHENOMENA: dict[str, str] = {
    "ALTEF":  "Electron Flux",
    "ALTP":   "Proton Event",
    "ALTXM":  "X-ray / Solar Flare",
    "WATA":   "Geomagnetic Storm Watch",
    "WATK":   "K-Index Watch",
    "WARK":   "K-Index Warning",
    "SUMX":   "Solar Flare Summary",
    "SUMN":   "Solar Flare Summary",
    "SUMSEV": "Space Weather Summary",
    "GEOMAG": "Geomagnetic Storm",
    "WRAP":   "Proton Event Warning",
    "WRAK":   "K-Index Warning",
}

# NOAA scale patterns in message text (G1-G5, S1-S5, R1-R5)
_SCALE_RE = re.compile(r"\b([GSR][1-5])\b")
# Kp index in message
_KP_RE = re.compile(
    # Match "Kp" or "K-index" followed by up to 30 non-digit chars then the value.
    # Handles: "K-index of 7", "Kp index level reached 7", "Kp index: 5", "Kp: 6"
    r"(?:Kp|K-index)[^0-9\n]{0,30}([0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)
# Serial number
_SERIAL_RE = re.compile(r"Serial\s+(?:Number|No\.?)[\s:]*([0-9]+)", re.IGNORECASE)
# Severity labels by scale number
_SEVERITY_LABELS = {1: "Minor", 2: "Moderate", 3: "Strong", 4: "Severe", 5: "Extreme"}

# Global sentinel geometry — space weather is a planetary phenomenon
_GLOBAL_GEOM = {"type": "Point", "coordinates": [0.0, 0.0]}


def _parse_phenomenon(product_id: str) -> str:
    """Map SWPC product code to a concise phenomenon label."""
    for prefix, label in _PRODUCT_PHENOMENA.items():
        if product_id.upper().startswith(prefix):
            return label
    return "Space Weather Alert"


def _parse_scale_severity(message: str) -> tuple[str | None, str | None]:
    """Extract the highest NOAA scale code and its severity label from alert text."""
    scales = _SCALE_RE.findall(message)
    if not scales:
        return None, None
    # Pick the highest scale (e.g. G3 > G2)
    best = max(scales, key=lambda s: int(s[1]))
    level = int(best[1])
    return best, _SEVERITY_LABELS.get(level)


def _parse_kp(message: str) -> float | None:
    """Extract Kp-index value from SWPC alert message text."""
    m = _KP_RE.search(message)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _parse_serial(message: str) -> str | None:
    """Extract SWPC serial number from message."""
    m = _SERIAL_RE.search(message)
    return m.group(1) if m else None


def _parse_issue_time(iso_str: str) -> datetime:
    """Parse SWPC issue_datetime string to UTC datetime."""
    # Format: "2026-04-05 12:00:00.000" or "2026-04-05T12:00:00"
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(iso_str[:26], fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return datetime.now(UTC)


class NoaaSwpcConnector(BaseConnector):
    """NOAA Space Weather Prediction Center — global space weather alerts.

    Produces ``space_weather_event`` CanonicalEvents from the latest SWPC
    alert/warning/summary product issuances.  Events carry no geographic
    footprint (global phenomenon), but include structured attributes for:
    - NOAA G/S/R-scale severity
    - Kp-index (geomagnetic activity)
    - Phenomenon type (X-ray flare, electron flux, geomagnetic storm…)

    Downstream consumers can use these as context layers to:
    - Degrade satellite imagery source confidence during G3+ storms
    - Flag GPS positioning accuracy degradation (G2+ / R2+ events)
    - Alert on HF communications disruption (R3+ Radio Blackout)
    """

    connector_id = "noaa-swpc"
    display_name = "NOAA Space Weather Prediction Center"
    source_type = "public_record"

    def __init__(
        self,
        *,
        api_url: str = _DEFAULT_API_URL,
        http_timeout: float = 20.0,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._http_timeout = http_timeout

    # ── BaseConnector interface ───────────────────────────────────────────────

    def connect(self) -> None:
        """Verify SWPC alerts endpoint is reachable."""
        try:
            resp = httpx.get(
                f"{self._api_url}{_ALERTS_PATH}", timeout=15.0
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"NOAA SWPC unreachable: {exc}") from exc

    def fetch(
        self,
        geometry: dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        *,
        max_results: int = 200,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Fetch the latest SWPC alert products.

        ``geometry``, ``start_time``, and ``end_time`` are accepted for
        interface compatibility but ignored — SWPC returns a static snapshot
        of the most recent ~200 products, independent of geography.
        """
        try:
            resp = httpx.get(
                f"{self._api_url}{_ALERTS_PATH}",
                timeout=self._http_timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorUnavailableError(f"SWPC fetch failed: {exc}") from exc

        alerts = resp.json()
        if not isinstance(alerts, list):
            log.warning("SWPC returned non-list response: %s", type(alerts).__name__)
            return []
        log.debug("NOAA SWPC: %d alert products fetched", len(alerts))
        return alerts[:max_results]

    def normalize(self, raw: dict[str, Any]) -> CanonicalEvent:
        """Transform a SWPC alert dict → ``space_weather_event`` CanonicalEvent."""
        product_id = str(raw.get("product_id", ""))
        issue_str = str(raw.get("issue_datetime", ""))
        message = str(raw.get("message", ""))

        if not product_id:
            raise NormalizationError("SWPC record missing 'product_id'")
        if not issue_str:
            raise NormalizationError(f"SWPC record {product_id!r} missing 'issue_datetime'")

        event_time = _parse_issue_time(issue_str)
        phenomenon = _parse_phenomenon(product_id)
        noaa_scale, severity = _parse_scale_severity(message)
        kp = _parse_kp(message)
        serial = _parse_serial(message)

        # Confidence: higher for official alert products vs summaries/watches
        is_alert = any(product_id.upper().startswith(p) for p in ("ALT", "GEOMAG"))
        confidence = 0.95 if is_alert else 0.80

        native_id = f"{product_id}-{serial}" if serial else f"{product_id}-{issue_str[:10]}"
        dedupe = hashlib.sha256(f"noaa-swpc:{product_id}:{issue_str}".encode()).hexdigest()[:16]

        attrs = SpaceWeatherAttributes(
            product_id=product_id,
            issue_datetime=event_time.isoformat(),
            message=message[:2000] if message else None,
            phenomenon=phenomenon,
            noaa_scale=noaa_scale,
            kp_index=kp,
            severity=severity,
            serial_number=serial,
        )

        return CanonicalEvent(
            event_id=make_event_id("noaa-swpc", native_id, event_time.isoformat()),
            source="noaa-swpc",
            source_type=SourceType.PUBLIC_RECORD,
            entity_type=EntityType.SPACE_WEATHER_PHENOMENON,
            entity_id=native_id,
            event_type=EventType.SPACE_WEATHER_EVENT,
            event_time=event_time,
            geometry=_GLOBAL_GEOM,
            centroid=_GLOBAL_GEOM,
            confidence=confidence,
            quality_flags=["global-phenomenon", "noaa-swpc"],
            attributes=attrs.model_dump(),
            normalization=NormalizationRecord(
                normalized_by="connector.noaa.swpc",
                dedupe_key=dedupe,
            ),
            provenance=ProvenanceRecord(
                raw_source_ref=f"noaa-swpc://{product_id}",
                source_record_id=native_id,
                source_url="https://www.swpc.noaa.gov/",
            ),
            correlation_keys=CorrelationKeys(),
            license=_LICENSE,
        )

    def health(self) -> ConnectorHealthStatus:
        """Lightweight health probe against SWPC alerts feed."""
        try:
            resp = httpx.get(f"{self._api_url}{_ALERTS_PATH}", timeout=10.0)
            resp.raise_for_status()
            count = len(resp.json()) if isinstance(resp.json(), list) else -1
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=True,
                message=f"SWPC reachable — {count} alerts (HTTP {resp.status_code})",
                last_successful_poll=datetime.now(UTC),
            )
        except Exception as exc:
            return ConnectorHealthStatus(
                connector_id=self.connector_id,
                healthy=False,
                message=str(exc),
            )
