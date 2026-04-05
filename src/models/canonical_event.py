"""Canonical event model — single normalized envelope for all source families.

Implements the schema defined in docs/geoint-platform-architecture-and-plan/
schemas/canonical-event.schema.json and the design goals in
docs/geoint-platform-architecture-and-plan/docs/canonical-event-model.md.

All timestamps MUST be UTC-aware (ISO 8601 with Z or +00:00 offset).
Confidence scores are in [0.0, 1.0].
event_id is deterministic: generate with make_event_id().
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ──────────────────────────────────────────────────────────────────────────────
# Enumerations (P0-3.2)
# ──────────────────────────────────────────────────────────────────────────────


class EventType(str, Enum):
    """All supported event families."""
    IMAGERY_ACQUISITION = "imagery_acquisition"
    IMAGERY_DETECTION = "imagery_detection"
    CHANGE_DETECTION = "change_detection"
    SHIP_POSITION = "ship_position"
    SHIP_TRACK_SEGMENT = "ship_track_segment"
    AIRCRAFT_POSITION = "aircraft_position"
    AIRCRAFT_TRACK_SEGMENT = "aircraft_track_segment"
    PERMIT_EVENT = "permit_event"
    INSPECTION_EVENT = "inspection_event"
    PROJECT_EVENT = "project_event"
    COMPLAINT_EVENT = "complaint_event"
    CONTEXTUAL_EVENT = "contextual_event"
    SYSTEM_HEALTH_EVENT = "system_health_event"
    DARK_SHIP_CANDIDATE = "dark_ship_candidate"
    SATELLITE_PASS = "satellite_pass"
    SATELLITE_ORBIT = "satellite_orbit"
    AIRSPACE_RESTRICTION = "airspace_restriction"
    NOTAM_EVENT = "notam_event"
    GPS_JAMMING_EVENT = "gps_jamming_event"
    STRIKE_EVENT = "strike_event"
    CAMERA_OBSERVATION = "camera_observation"
    DETECTION_OVERLAY = "detection_overlay"
    VIDEO_CLIP_REF = "video_clip_ref"
    RENDER_MODE_EVENT = "render_mode_event"
    SEISMIC_EVENT = "seismic_event"
    NATURAL_HAZARD_EVENT = "natural_hazard_event"
    WEATHER_OBSERVATION = "weather_observation"
    CONFLICT_EVENT = "conflict_event"
    MARITIME_WARNING = "maritime_warning"
    MILITARY_SITE_OBSERVATION = "military_site_observation"
    THERMAL_ANOMALY_EVENT = "thermal_anomaly_event"
    SPACE_WEATHER_EVENT = "space_weather_event"
    AIR_QUALITY_OBSERVATION = "air_quality_observation"


class SourceType(str, Enum):
    """Normalised source category codes."""
    IMAGERY_CATALOG = "imagery_catalog"
    TELEMETRY = "telemetry"
    REGISTRY = "registry"
    PUBLIC_RECORD = "public_record"
    CONTEXT_FEED = "context_feed"
    DERIVED = "derived"


class EntityType(str, Enum):
    """The kind of real-world object an event is about."""
    IMAGERY_SCENE = "imagery_scene"
    VESSEL = "vessel"
    AIRCRAFT = "aircraft"
    CONSTRUCTION_SITE = "construction_site"
    PERMIT = "permit"
    NEWS_ARTICLE = "news_article"
    SYSTEM = "system"
    TRACK = "track"
    SEISMIC_HAZARD = "seismic_hazard"
    NATURAL_HAZARD = "natural_hazard"
    CONFLICT_INCIDENT = "conflict_incident"
    MARITIME_ZONE = "maritime_zone"
    MILITARY_INSTALLATION = "military_installation"
    THERMAL_ANOMALY = "thermal_anomaly"
    SPACE_WEATHER_PHENOMENON = "space_weather_phenomenon"
    AIR_QUALITY_SENSOR = "air_quality_sensor"


# ──────────────────────────────────────────────────────────────────────────────
# Sub-models (P0-3.3)
# ──────────────────────────────────────────────────────────────────────────────


class NormalizationRecord(BaseModel):
    """Tracks how and when raw source data was transformed."""
    schema_version: str = Field(default="1.0.0")
    normalized_by: str = Field(..., description="Connector module identifier, e.g. connector.cdse.stac")
    normalization_warnings: list[str] = Field(default_factory=list)
    dedupe_key: str | None = Field(default=None)


class ProvenanceRecord(BaseModel):
    """Links back to the raw source artefact."""
    raw_source_ref: str = Field(..., description="S3 path or equivalent reference to the raw payload")
    source_record_id: str | None = Field(default=None)
    source_record_version: str | None = Field(default=None, description="ETag or content-hash of the source record")
    source_url: str | None = Field(default=None)


class LicenseRecord(BaseModel):
    """Per-event licensing and redistribution metadata."""
    access_tier: str = Field(default="public", description="public | restricted | commercial")
    commercial_use: str = Field(default="check-provider-terms", description="allowed | allowed-with-terms | not-allowed | check-provider-terms")
    redistribution: str = Field(default="check-provider-terms", description="allowed | not-allowed | check-provider-terms")
    attribution_required: bool = Field(default=True)


class CorrelationKeys(BaseModel):
    """Typed cross-reference pointers for entity-centric correlation."""
    aoi_ids: list[str] = Field(default_factory=list)
    mmsi: str | None = Field(default=None, description="Maritime Mobile Service Identity")
    imo: str | None = Field(default=None, description="IMO vessel number")
    icao24: str | None = Field(default=None, description="ICAO 24-bit aircraft address")
    callsign: str | None = Field(default=None)
    permit_id: str | None = Field(default=None)
    place_key: str | None = Field(default=None, description="Normalised place identifier, e.g. SA-RIYADH")


# ──────────────────────────────────────────────────────────────────────────────
# Per-family attribute models (P0-3.4)
# ──────────────────────────────────────────────────────────────────────────────


class ImageryAttributes(BaseModel):
    """Attributes for imagery_acquisition and imagery_detection events."""
    platform: str | None = Field(default=None, description="e.g. Sentinel-2A, Landsat-9")
    sensor: str | None = Field(default=None)
    gsd_m: float | None = Field(default=None, description="Ground sample distance in metres")
    cloud_cover_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    off_nadir_angle: float | None = Field(default=None)
    sun_azimuth: float | None = Field(default=None)
    scene_url: str | None = Field(default=None)
    bands_available: list[str] = Field(default_factory=list)
    processing_level: str | None = Field(default=None, description="e.g. L1C, L2A, ARD")


class ShipPositionAttributes(BaseModel):
    """Attributes for ship_position events."""
    mmsi: str | None = None
    imo: str | None = None
    vessel_name: str | None = None
    ship_type: int | None = None
    course_deg: float | None = Field(default=None, ge=0.0, le=360.0)
    speed_kn: float | None = Field(default=None, ge=0.0)
    heading_deg: float | None = Field(default=None, ge=0.0, le=360.0)
    nav_status: str | None = None
    length_m: float | None = None
    beam_m: float | None = None
    destination: str | None = None
    eta: str | None = None


class AircraftAttributes(BaseModel):
    """Attributes for aircraft_position events."""
    icao24: str | None = None
    callsign: str | None = None
    origin_country: str | None = None
    baro_altitude_m: float | None = None
    geo_altitude_m: float | None = None
    velocity_ms: float | None = None
    true_track_deg: float | None = None
    vertical_rate_ms: float | None = None
    on_ground: bool | None = None
    squawk: str | None = None


class PermitAttributes(BaseModel):
    """Attributes for permit_event events."""
    permit_number: str | None = None
    permit_type: str | None = None
    applicant: str | None = None
    description: str | None = None
    status: str | None = None
    issued_date: str | None = None
    expiry_date: str | None = None
    authority: str | None = None


class ContextualAttributes(BaseModel):
    """Attributes for contextual_event events derived from GDELT and similar feeds."""
    headline: str | None = None
    url: str | None = None
    tone: float | None = None
    theme_codes: list[str] = Field(default_factory=list)
    source_publication: str | None = None
    language: str | None = None
    num_mentions: int | None = None
    num_sources: int | None = None
    gdelt_id: str | None = None


class SeismicAttributes(BaseModel):
    """Attributes for seismic_event events (USGS Earthquake Catalog)."""
    magnitude: float | None = None
    magnitude_type: str | None = None
    depth_km: float | None = None
    place: str | None = None
    status: str | None = None
    tsunami_flag: int | None = None
    felt_reports: int | None = None
    cdi: float | None = None
    mmi: float | None = None
    alert: str | None = None
    usgs_url: str | None = None
    net: str | None = None


class NaturalHazardAttributes(BaseModel):
    """Attributes for natural_hazard_event events (NASA EONET)."""
    category: str | None = None
    category_title: str | None = None
    sources: list[str] = Field(default_factory=list)
    status: str | None = None
    closed_date: str | None = None
    eonet_id: str | None = None


class WeatherAttributes(BaseModel):
    """Attributes for weather_observation events (Open-Meteo)."""
    cloud_cover_pct: float | None = None
    precipitation_mm: float | None = None
    wind_speed_ms: float | None = None
    wind_direction_deg: float | None = None
    temperature_c: float | None = None
    forecast_horizon_hours: int | None = None
    weather_model: str | None = None


class ConflictAttributes(BaseModel):
    """Attributes for conflict_event events (ACLED Armed Conflict data)."""
    acled_event_id: str | None = None
    disorder_type: str | None = None
    event_type: str | None = None
    sub_event_type: str | None = None
    actor1: str | None = None
    actor2: str | None = None
    country: str | None = None
    admin1: str | None = None
    location: str | None = None
    fatalities: int | None = None
    source: str | None = None
    notes: str | None = None
    civilian_targeting: str | None = None


class MaritimeWarningAttributes(BaseModel):
    """Attributes for maritime_warning events (NGA MSI Broadcast Warnings)."""
    nav_area: str | None = None
    nav_area_code: str | None = None
    subregion: str | None = None
    region: str | None = None
    authority: str | None = None
    msg_year: str | None = None
    msg_number: str | None = None
    cancel_date: str | None = None
    issue_date: str | None = None
    warning_text: str | None = None
    status: str | None = None


class MilitaryFeatureAttributes(BaseModel):
    """Attributes for military_site_observation events (OpenStreetMap Overpass)."""
    osm_id: str | None = None
    osm_type: str | None = None
    military_type: str | None = None
    name: str | None = None
    operator: str | None = None
    additional_tags: dict[str, str] = Field(default_factory=dict)


class ThermalAnomalyAttributes(BaseModel):
    """Attributes for thermal_anomaly_event events (NASA FIRMS active fire data)."""
    satellite: str | None = None        # Terra, Aqua, Suomi-NPP, NOAA-20, NOAA-21
    instrument: str | None = None       # MODIS, VIIRS
    frp: float | None = None            # Fire Radiative Power (MW)
    brightness: float | None = None     # Channel 21/22 brightness (Kelvin)
    bright_t31: float | None = None     # Channel 31 brightness temperature (K)
    confidence: str | None = None       # VIIRS: high/nominal/low; MODIS: 0-100
    track: float | None = None          # Pixel size along track (km)
    scan: float | None = None           # Pixel size along scan (km)
    acq_date: str | None = None         # Acquisition date YYYY-MM-DD
    acq_time: str | None = None         # Acquisition time HHMM UTC
    day_night: str | None = None        # D (day) or N (night)
    version: str | None = None          # FIRMS product version
    source_dataset: str | None = None   # e.g. VIIRS_SNPP_NRT, MODIS_NRT


class SpaceWeatherAttributes(BaseModel):
    """Attributes for space_weather_event events (NOAA SWPC alerts)."""
    product_id: str | None = None        # NOAA SWPC product code (e.g. ALTEF3)
    issue_datetime: str | None = None    # ISO 8601 issue datetime
    message: str | None = None           # Full alert text (truncated to 2000 chars)
    phenomenon: str | None = None        # Geomagnetic Storm, Solar Flare, etc.
    noaa_scale: str | None = None        # G1-G5, S1-S5, R1-R5
    kp_index: float | None = None        # Planetary K-index
    severity: str | None = None          # Minor, Moderate, Strong, Severe, Extreme
    serial_number: str | None = None


class AirQualityAttributes(BaseModel):
    """Attributes for air_quality_observation events (OpenAQ sensor readings)."""
    location_id: int | None = None
    location_name: str | None = None
    sensor_id: int | None = None
    parameter: str | None = None         # pm25, pm10, o3, no2, so2, co
    display_name: str | None = None      # Human-readable parameter name
    value: float | None = None
    unit: str | None = None
    last_updated: str | None = None      # ISO8601
    is_mobile: bool | None = None
    is_monitor: bool | None = None
    provider_name: str | None = None
    country_code: str | None = None
    locality: str | None = None


# ──────────────────────────────────────────────────────────────────────────────
# Main canonical event model (P0-3.1)
# ──────────────────────────────────────────────────────────────────────────────


class CanonicalEvent(BaseModel):
    """Single normalised envelope for all geospatial event families.

    Designed for storage in PostgreSQL/PostGIS canonical_events table.
    geometry and centroid conform to GeoJSON (RFC 7946).

    Usage::
        event = CanonicalEvent(
            event_id=make_event_id("copernicus-cdse", "S2A_...", "2026-04-01T10:22:33Z"),
            source="copernicus-cdse",
            source_type=SourceType.IMAGERY_CATALOG,
            entity_type=EntityType.IMAGERY_SCENE,
            event_type=EventType.IMAGERY_ACQUISITION,
            event_time=datetime(2026, 4, 1, 10, 22, 33, tzinfo=timezone.utc),
            geometry={"type": "Polygon", "coordinates": [...]},
            centroid={"type": "Point", "coordinates": [46.67, 24.71]},
            attributes=ImageryAttributes(platform="Sentinel-2A", cloud_cover_pct=3.2).model_dump(),
            normalization=NormalizationRecord(normalized_by="connector.cdse.stac"),
            provenance=ProvenanceRecord(raw_source_ref="s3://bucket/raw/cdse/scene.json"),
            ingested_at=datetime.now(timezone.utc),
            license=LicenseRecord(),
        )
    """

    # Identity
    event_id: str = Field(..., description="Deterministic internal identifier; use make_event_id()")
    source: str = Field(..., description="Normalised provider/source code, e.g. copernicus-cdse")
    source_type: SourceType
    entity_type: EntityType
    entity_id: str | None = Field(
        default=None,
        description=(
            "Source-native entity identifier. Semantics by entity_type: "
            "VESSEL → MMSI (9-digit string, zero-padded); "
            "AIRCRAFT → ICAO24 hex string; "
            "IMAGERY_SCENE → catalogue scene_id (e.g. Sentinel-2 SAFE path); "
            "CONTEXTUAL_EVENT → GDELT event_id when available, else None; "
            "PERMIT → permit_number from issuing authority."
        ),
    )
    event_type: EventType

    # Time — all UTC enforced by validator
    event_time: datetime = Field(..., description="Primary event timestamp (UTC)")
    time_start: datetime | None = Field(default=None, description="Interval start (UTC)")
    time_end: datetime | None = Field(default=None, description="Interval end (UTC)")
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    first_seen_at: datetime | None = Field(default=None)
    last_seen_at: datetime | None = Field(default=None)

    # Spatial — GeoJSON dicts
    geometry: dict[str, Any] = Field(..., description="GeoJSON geometry object (RFC 7946)")
    centroid: dict[str, Any] = Field(..., description="GeoJSON Point at event centroid")
    altitude_m: float | None = Field(default=None)
    depth_m: float | None = Field(default=None)

    # Quality
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    quality_flags: list[str] = Field(default_factory=list)

    # Payload — typed per family, serialised to dict for schema flexibility
    attributes: dict[str, Any] = Field(default_factory=dict)

    # Provenance chain
    normalization: NormalizationRecord
    provenance: ProvenanceRecord
    correlation_keys: CorrelationKeys = Field(default_factory=CorrelationKeys)
    license: LicenseRecord = Field(default_factory=LicenseRecord)

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("event_time", "time_start", "time_end", "ingested_at", "first_seen_at", "last_seen_at", mode="before")
    @classmethod
    def _enforce_utc(cls, v: Any) -> Any:
        """Reject naive datetimes; coerce Z/+00:00 strings to UTC-aware datetime."""
        if v is None:
            return v
        if isinstance(v, str):
            # Replace trailing Z with +00:00 for fromisoformat compat
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if isinstance(v, datetime):
            if v.tzinfo is None:
                raise ValueError(f"Naive datetime rejected — all timestamps must carry UTC timezone info: {v!r}")
            return v
        return v

    @field_validator("geometry", "centroid")
    @classmethod
    def _require_geojson_type(cls, v: dict[str, Any]) -> dict[str, Any]:
        if "type" not in v or "coordinates" not in v:
            raise ValueError("geometry/centroid must be a GeoJSON object with 'type' and 'coordinates'")
        return v

    @field_validator("centroid")
    @classmethod
    def _centroid_must_be_point(cls, v: dict[str, Any]) -> dict[str, Any]:
        if v.get("type") != "Point":
            raise ValueError("centroid must be a GeoJSON Point")
        return v

    @model_validator(mode="after")
    def _time_interval_order(self) -> CanonicalEvent:
        if self.time_start and self.time_end and self.time_start > self.time_end:
            raise ValueError("time_start must not be after time_end")
        return self


# ──────────────────────────────────────────────────────────────────────────────
# event_id generation utility (P0-3.6)
# ──────────────────────────────────────────────────────────────────────────────


def make_event_id(source: str, entity_id: str, event_time: str | datetime) -> str:
    """Generate a deterministic event_id from (source, entity_id, event_time).

    The ID is stable: the same source+entity+time always yields the same id,
    enabling safe upserts and deduplication without external coordination.

    Args:
        source:     Normalised provider code, e.g. "copernicus-cdse".
        entity_id:  Source-native scene or object identifier.
        event_time: UTC datetime or ISO 8601 string.

    Returns:
        String of the form ``evt_<source_slug>_<sha256_12>``.

    Example::
        make_event_id("copernicus-cdse", "S2A_MSIL2A_20260401", "2026-04-01T10:22:33Z")
        # "evt_copernicus-cdse_a3f8b2c1d04e"
    """
    if isinstance(event_time, datetime):
        ts = event_time.astimezone(UTC).isoformat()
    else:
        ts = event_time
    raw = f"{source}:{entity_id}:{ts}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:12]
    source_slug = source.lower().replace(" ", "-")
    return f"evt_{source_slug}_{digest}"
