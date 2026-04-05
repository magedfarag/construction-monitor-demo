"""Evidence pack models — Phase 5 Track B.

Defines the data containers for assembled evidence packs and narrative exports.
An EvidencePack collects timeline entries, layer summaries, and provenance
records from one or more canonical events, optionally linked to a saved
investigation.

All datetime fields are UTC-aware.  IDs are auto-generated UUIDs.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_utc(v: Any) -> Any:
    """Validate that a datetime value is UTC-aware."""
    if v is None:
        return v
    if isinstance(v, str):
        v = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if isinstance(v, datetime) and v.tzinfo is None:
        raise ValueError(
            f"Naive datetime rejected — all timestamps must carry UTC timezone info: {v!r}"
        )
    return v


# ──────────────────────────────────────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────────────────────────────────────


class EvidencePackFormat(str, Enum):
    """Output serialisation format for a rendered evidence pack."""
    JSON = "json"
    MARKDOWN = "markdown"
    GEOJSON = "geojson"


class EvidencePackSection(str, Enum):
    """Logical sections that can be included in an evidence pack."""
    TIMELINE = "timeline"
    LAYER_SUMMARY = "layer_summary"
    PROVENANCE = "provenance"
    IMAGES = "images"
    ENTITIES = "entities"
    NOTES = "notes"
    EVIDENCE_LINKS = "evidence_links"
    ABSENCE_SIGNALS = "absence_signals"


# ──────────────────────────────────────────────────────────────────────────────
# Sub-models
# ──────────────────────────────────────────────────────────────────────────────


class TimelineEntry(BaseModel):
    """A single time-ordered entry in an evidence pack timeline."""

    timestamp: datetime = Field(..., description="UTC-aware event timestamp")
    event_type: str
    event_id: str
    summary: str
    source: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    layer: str = Field(..., description="Operational layer the event belongs to")

    @field_validator("timestamp", mode="before")
    @classmethod
    def _utc_timestamp(cls, v: Any) -> Any:
        return _require_utc(v)


class LayerSummaryEntry(BaseModel):
    """Aggregated statistics for a single operational layer in the pack."""

    layer_name: str
    event_count: int = Field(ge=0)
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None
    coverage_description: str
    sources: list[str] = Field(default_factory=list)

    @field_validator("time_range_start", "time_range_end", mode="before")
    @classmethod
    def _utc_range(cls, v: Any) -> Any:
        return _require_utc(v)


class ProvenanceRecord(BaseModel):
    """Tracks where the evidence in a pack came from."""

    source_name: str
    source_type: str
    event_count: int = Field(ge=0)
    license: str | None = None
    retrieval_timestamp: datetime | None = None
    notes: str | None = None

    @field_validator("retrieval_timestamp", mode="before")
    @classmethod
    def _utc_retrieval(cls, v: Any) -> Any:
        return _require_utc(v)


# ──────────────────────────────────────────────────────────────────────────────
# Core entity
# ──────────────────────────────────────────────────────────────────────────────


class EvidencePack(BaseModel):
    """A fully assembled evidence pack combining events, timeline, layers, and provenance."""

    pack_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str | None = None
    investigation_id: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    created_by: str | None = None
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    sections_included: list[EvidencePackSection] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    layer_summaries: list[LayerSummaryEntry] = Field(default_factory=list)
    provenance_records: list[ProvenanceRecord] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    evidence_links: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    total_events: int = Field(default=0, ge=0)
    export_format: EvidencePackFormat = EvidencePackFormat.JSON

    @field_validator("created_at", "time_window_start", "time_window_end", mode="before")
    @classmethod
    def _utc_timestamps(cls, v: Any) -> Any:
        return _require_utc(v)


# ──────────────────────────────────────────────────────────────────────────────
# Request model
# ──────────────────────────────────────────────────────────────────────────────


class EvidencePackRequest(BaseModel):
    """Payload for generating a new evidence pack."""

    title: str
    description: str | None = None
    investigation_id: str | None = None
    created_by: str | None = None
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    sections: list[EvidencePackSection] = Field(
        default_factory=lambda: list(EvidencePackSection)
    )
    event_ids: list[str] | None = Field(
        default=None,
        description="Explicit event selection — None means use time window or investigation",
    )
    export_format: EvidencePackFormat = EvidencePackFormat.JSON
    include_layer_summaries: bool = True
    include_provenance: bool = True
    include_timeline: bool = True

    @field_validator("time_window_start", "time_window_end", mode="before")
    @classmethod
    def _utc_window(cls, v: Any) -> Any:
        return _require_utc(v)


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

__all__ = [
    "EvidencePackFormat",
    "EvidencePackSection",
    "TimelineEntry",
    "LayerSummaryEntry",
    "ProvenanceRecord",
    "EvidencePack",
    "EvidencePackRequest",
]
