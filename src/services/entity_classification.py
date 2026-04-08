"""Classification utilities for military vs civilian entities."""
from __future__ import annotations

from typing import Literal

# ──────────────────────────────────────────────────────────────────────────────
# Vessel Classification
# ──────────────────────────────────────────────────────────────────────────────

MILITARY_VESSEL_TYPES = {
    "Patrol Craft",
    "Patrol",
    "Corvette",
    "Frigate",
    "Destroyer",
    "Cruiser",
    "Submarine",
    "Aircraft Carrier",
    "Amphibious",
    "Mine Warfare",
    "Naval Auxiliary",
    "Fast Attack Craft",
}

MILITARY_OPERATORS = {
    "IRGC Navy",
    "IRGC",
    "Navy",
    "Naval",
    "Military",
    "Defense",
    "Coast Guard",  # Paramilitary
}

MILITARY_OWNER_KEYWORDS = {
    "Navy",
    "IRGC",
    "Military",
    "Defense",
    "Armed Forces",
    "Coast Guard",
}


def classify_vessel(
    vessel_type: str | None,
    owner: str | None = None,
    operator: str | None = None,
    vessel_name: str | None = None,
) -> Literal["military", "civilian"]:
    """
    Classify a vessel as military or civilian based on type, owner, operator, and name.

    Args:
        vessel_type: Vessel type (e.g., "VLCC", "Patrol Craft")
        owner: Vessel owner
        operator: Vessel operator
        vessel_name: Vessel name

    Returns:
        "military" or "civilian"
    """
    # Check vessel type
    if vessel_type and vessel_type in MILITARY_VESSEL_TYPES:
        return "military"

    # Check operator
    if operator:
        for keyword in MILITARY_OPERATORS:
            if keyword.lower() in operator.lower():
                return "military"

    # Check owner
    if owner:
        for keyword in MILITARY_OWNER_KEYWORDS:
            if keyword.lower() in owner.lower():
                return "military"

    # Check vessel name for military prefixes/patterns
    if vessel_name:
        name_upper = vessel_name.upper()
        military_prefixes = ["HMS", "USS", "IRGCN", "INS", "PLANS", "KRI", "HTMS"]
        for prefix in military_prefixes:
            if name_upper.startswith(prefix + " ") or name_upper.startswith(prefix + "-"):
                return "military"

    return "civilian"


# ──────────────────────────────────────────────────────────────────────────────
# Aircraft Classification
# ──────────────────────────────────────────────────────────────────────────────

MILITARY_AIRCRAFT_CALLSIGN_PREFIXES = {
    # US Military
    "RCH",      # Reach (USAF transport)
    "CNV",      # Convoy (USAF transport)
    "EVAC",     # Medical evacuation
    "RCHD",     # Reach medical
    "BOXER",    # C-17 callsign
    "PAT",      # Patrol
    "SPAR",     # Special Air Resource (USAF)
    "DAWG",     # E-3 AWACS
    "METAL",    # Tanker
    "EVAL",     # Test aircraft
    # NATO/Allied
    "NATO",     # NATO aircraft
    "RRR",      # UK RAF
    "RSAF",     # Royal Saudi Air Force
    "UAEAF",    # UAE Air Force
    "BAF",      # Belgian Air Force
    # IRGC/Iranian
    "IRM",      # Iran military
    "IRA",      # Iran Air Force
    # Other indicators
    "MIL",      # Generic military
    "NAVY",     # Naval aviation
    "ARMY",     # Army aviation
    "FORCE",    # Air force
}

MILITARY_ORIGIN_COUNTRIES_WITH_MILITARY_ACTIVITY = {
    "United States",
    "Iran",
    "Saudi Arabia",
    "United Arab Emirates",
    "Qatar",
    "Bahrain",
    "Oman",
    "United Kingdom",
    "France",
}


def classify_aircraft(
    callsign: str | None,
    origin_country: str | None = None,
    icao24: str | None = None,
) -> Literal["military", "civilian", "unknown"]:
    """
    Classify an aircraft as military or civilian based on callsign and origin.

    Args:
        callsign: Aircraft callsign
        origin_country: Country of origin/registration
        icao24: ICAO 24-bit address

    Returns:
        "military", "civilian", or "unknown"
    """
    if not callsign and not origin_country:
        return "unknown"

    # Check callsign for military prefixes
    if callsign:
        callsign_upper = callsign.strip().upper()

        # Check exact prefixes
        for prefix in MILITARY_AIRCRAFT_CALLSIGN_PREFIXES:
            if callsign_upper.startswith(prefix):
                return "military"

        # Check for numeric-only callsigns (often military)
        if callsign_upper.isdigit() and origin_country in MILITARY_ORIGIN_COUNTRIES_WITH_MILITARY_ACTIVITY:
            return "military"

    # ICAO24 address ranges (US military aircraft have specific ranges)
    # Note: This is a simplified check; full implementation would use comprehensive ranges
    if icao24:
        # US military typically use AE#### range
        if icao24.upper().startswith("AE"):
            return "military"

    # If we have country info but no military indicators, assume civilian
    if origin_country:
        return "civilian"

    return "unknown"


# ──────────────────────────────────────────────────────────────────────────────
# Missile/Projectile Classification (Future)
# ──────────────────────────────────────────────────────────────────────────────

def classify_projectile(
    projectile_type: str | None,
    source: str | None = None,
) -> Literal["military", "civilian"]:
    """
    Classify a projectile/missile (future implementation).

    Args:
        projectile_type: Type of projectile
        source: Source/operator

    Returns:
        "military" or "civilian"
    """
    # All missiles/projectiles are military by definition
    return "military"
