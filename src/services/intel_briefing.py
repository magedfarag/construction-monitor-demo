"""Intelligence briefing generator — P6-6.

Aggregates current-state metrics from live data sources:
- Chokepoint threat levels (chokepoint_service)
- Vessel registry counts (vessel_registry)
- Dark-ship candidates (dark_ship_detector via event store)
No hardcoded scenario text — all values are computed at request time.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime

from pydantic import BaseModel

from src.services.chokepoint_service import get_all_chokepoints
from src.services.vessel_registry import SanctionsStatus, VesselProfile, list_vessels

log = logging.getLogger(__name__)


class VesselAlert(BaseModel):
    mmsi: str
    vessel_name: str
    sanctions_status: str
    alert_type: str          # "dark_ship" | "sanctions_entry" | "position_jump"
    detail: str
    confidence: float


class IntelBriefing(BaseModel):
    briefing_id: str
    timestamp: str
    classification: str
    risk_level: str          # CRITICAL | HIGH | MODERATE | LOW
    risk_color: str          # hex
    executive_summary: str
    key_findings: list[str]
    vessel_alerts: list[VesselAlert]
    chokepoint_status: list[dict]
    dark_ship_count: int
    sanctioned_vessel_count: int
    active_vessel_count: int


def _build_sanctions_alerts(sanctioned_vessels: list) -> list[VesselAlert]:
    """Generate VesselAlert entries for high-risk sanctioned vessels."""
    alerts: list[VesselAlert] = []
    for v in sanctioned_vessels[:10]:  # cap at 10 to avoid overwhelming the briefing
        alerts.append(VesselAlert(
            mmsi=v.mmsi,
            vessel_name=v.name,
            sanctions_status=str(v.sanctions_status),
            alert_type="sanctions_entry",
            detail=(
                f"{v.name} is on {v.sanctions_status} watchlist. "
                f"Flag: {v.flag}. "
                f"{v.sanctions_detail or 'OFAC-SDN or shadow-fleet designation.'}"
            ),
            confidence=0.95,
        ))
    return alerts


def _build_vessel_alerts(dark_ship_results: list | None) -> list[VesselAlert]:
    """Convert dark-ship candidates into VesselAlert objects."""
    alerts: list[VesselAlert] = []
    for c in (dark_ship_results or []):
        from datetime import datetime as _dt
        gap_start = c.gap_start[:10] if c.gap_start else "unknown"
        gap_end = c.gap_end[:10] if c.gap_end else "unknown"
        alert_type = "position_jump" if (c.position_jump_km or 0) > 50 else "dark_ship"
        detail_parts = [f"AIS gap {c.gap_hours:.1f}h ({gap_start} to {gap_end})."]
        if c.position_jump_km:
            detail_parts.append(f"Position jump {c.position_jump_km:.0f} km after reappearance.")
        if c.sanctions_flag:
            detail_parts.append("Vessel appears on sanctions/shadow-fleet watchlist.")
        alerts.append(VesselAlert(
            mmsi=c.mmsi,
            vessel_name=c.vessel_name,
            sanctions_status="sanctioned" if c.sanctions_flag else "clean",
            alert_type=alert_type,
            detail=" ".join(detail_parts),
            confidence=c.confidence,
        ))
    return alerts


def _build_key_findings(
    dark_count: int,
    sanctioned_count: int,
    chokepoints: list,
) -> list[str]:
    """Generate key findings from live metrics."""
    findings: list[str] = []

    # Dark ship finding
    if dark_count > 0:
        findings.append(
            f"{dark_count} vessel{'s' if dark_count != 1 else ''} detected with AIS dark periods "
            f"exceeding {6}h in the monitored area."
        )
    else:
        findings.append(
            "No active AIS dark-ship events detected in current monitoring window. "
            "AIS feed connectivity required for real-time detection."
        )

    # Chokepoint findings (top 3 by threat level)
    top_chokepoints = sorted(chokepoints, key=lambda cp: cp.threat_level, reverse=True)[:3]
    for cp in top_chokepoints:
        if cp.threat_level >= 4:
            findings.append(
                f"{cp.name} {cp.threat_label}: {cp.daily_flow_mbbl:.1f} MBBL/day throughput — "
                f"trend {cp.trend}."
            )
        elif cp.threat_level >= 3:
            findings.append(
                f"{cp.name} ELEVATED: {cp.daily_flow_mbbl:.1f} MBBL/day — monitoring advised."
            )

    # Sanctioned vessel fleet size
    if sanctioned_count > 0:
        findings.append(
            f"{sanctioned_count} sanctioned/shadow-fleet vessels in registry "
            f"(OFAC-SDN, shadow-fleet, watch-list designations)."
        )

    return findings


def _build_executive_summary(risk_level: str, dark_count: int, chokepoints: list) -> str:
    """Generate a concise executive summary from live data."""
    critical_cps = [cp for cp in chokepoints if cp.threat_level >= 5]
    high_cps = [cp for cp in chokepoints if cp.threat_level == 4]

    lines: list[str] = [f"THREAT LEVEL: {risk_level}."]

    if critical_cps:
        names = ", ".join(cp.name for cp in critical_cps)
        lines.append(
            f"{names} at CRITICAL threat — immediate interdiction risk to throughput."
        )
    if high_cps:
        names = ", ".join(cp.name for cp in high_cps)
        lines.append(f"{names} at HIGH threat — enhanced monitoring in effect.")

    if dark_count > 0:
        lines.append(
            f"{dark_count} AIS dark-ship event{'s' if dark_count != 1 else ''} active. "
            f"Recommend enhanced AIS monitoring and satellite track correlation."
        )
    else:
        lines.append(
            "No AIS dark-ship events in current window. "
            "Connect an AIS feed (AISSTREAM_API_KEY) for real-time maritime surveillance."
        )

    return " ".join(lines)


def generate_briefing() -> IntelBriefing:
    now = datetime.now(UTC)
    cps = get_all_chokepoints()
    max_threat = max((cp.threat_level for cp in cps), default=0)

    risk_level, risk_color = (
        ("CRITICAL", "#dc2626") if max_threat >= 5 else
        ("HIGH", "#f97316")     if max_threat == 4 else
        ("MODERATE", "#eab308") if max_threat == 3 else
        ("LOW", "#22c55e")
    )

    # Query live dark-ship data from the event store via the dark_ships router
    dark_candidates: list = []
    try:
        from src.api import dark_ships as _ds_router
        result = _ds_router.list_candidates()
        dark_candidates = result.candidates
    except Exception as exc:
        log.warning("Intel briefing: could not fetch dark-ship data: %s", exc)

    # Vessel registry counts
    all_vessels = list_vessels(limit=500)
    sanctioned = [
        v for v in all_vessels
        if v.sanctions_status not in (SanctionsStatus.CLEAN,)
    ]

    briefing_id = "brf-" + hashlib.sha256(now.isoformat().encode()).hexdigest()[:8]

    vessel_alerts = _build_vessel_alerts(dark_candidates) + _build_sanctions_alerts(sanctioned)

    return IntelBriefing(
        briefing_id=briefing_id,
        timestamp=now.isoformat(),
        classification="UNCLASSIFIED",
        risk_level=risk_level,
        risk_color=risk_color,
        executive_summary=_build_executive_summary(risk_level, len(dark_candidates), cps),
        key_findings=_build_key_findings(len(dark_candidates), len(sanctioned), cps),
        vessel_alerts=vessel_alerts,
        chokepoint_status=[
            {
                "id": cp.id,
                "name": cp.name,
                "threat_level": cp.threat_level,
                "threat_label": cp.threat_label,
                "daily_flow_mbbl": cp.daily_flow_mbbl,
                "trend": cp.trend,
            }
            for cp in cps
        ],
        dark_ship_count=len(dark_candidates),
        sanctioned_vessel_count=len(sanctioned),
        active_vessel_count=len(all_vessels),
    )
