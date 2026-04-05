"""Analyst query and briefing models — Phase 5 Track C.

Provides structured query expressions for the analyst query surface and
data-backed briefing generation models backed by real normalized events.

All datetimes must be UTC-aware.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ──────────────────────────────────────────────────────────────────────────────
# Query enumerations
# ──────────────────────────────────────────────────────────────────────────────


class QueryOperator(str, Enum):
    AND = "and"
    OR = "or"
    NOT = "not"


class QueryFieldType(str, Enum):
    EVENT_TYPE = "event_type"      # filter by EventType enum value
    SOURCE_TYPE = "source_type"    # filter by SourceType enum
    ENTITY_ID = "entity_id"        # filter by vessel MMSI, aircraft callsign, etc.
    TIME_RANGE = "time_range"      # filter by time window
    CONFIDENCE = "confidence"      # minimum confidence threshold
    GEOMETRY = "geometry"          # spatial filter (AOI bounding box or polygon)
    TEXT = "text"                  # text match in event payload


# ──────────────────────────────────────────────────────────────────────────────
# Query models
# ──────────────────────────────────────────────────────────────────────────────


class QueryFilter(BaseModel):
    """A single filter clause in an analyst query."""

    field: QueryFieldType
    operator: str = "eq"  # eq | gte | lte | contains | within
    value: Any = Field(..., description="Filter value: string, number, list, or dict")


class AnalystQuery(BaseModel):
    """Structured query expression for the analyst query surface."""

    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str | None = None
    filters: list[QueryFilter] = Field(default_factory=list)
    combine_with: QueryOperator = QueryOperator.AND
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    include_provenance: bool = True


class QueryResult(BaseModel):
    """Result of executing an AnalystQuery."""

    query_id: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_matched: int
    returned_count: int
    events: list[dict] = Field(default_factory=list)
    sources_cited: list[str] = Field(default_factory=list)
    confidence_range: tuple[float, float] | None = None


# ──────────────────────────────────────────────────────────────────────────────
# Briefing models
# ──────────────────────────────────────────────────────────────────────────────


class BriefingSection(str, Enum):
    EXECUTIVE_SUMMARY = "executive_summary"
    ENTITY_ACTIVITY = "entity_activity"
    THREAT_INDICATORS = "threat_indicators"
    TIMELINE = "timeline"
    ABSENCE_SIGNALS = "absence_signals"
    SOURCE_ASSESSMENT = "source_assessment"
    RECOMMENDATIONS = "recommendations"


class BriefingRequest(BaseModel):
    """Request to generate a data-backed analyst briefing."""

    title: str
    investigation_id: str | None = None
    query: AnalystQuery | None = None
    sections: list[BriefingSection] = Field(
        default_factory=lambda: list(BriefingSection)
    )
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    classification_label: str = "UNCLASSIFIED"
    created_by: str | None = None


class BriefingOutput(BaseModel):
    """Output of a generated analyst briefing, backed by real data."""

    briefing_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str | None = None
    classification_label: str = "UNCLASSIFIED"
    investigation_id: str | None = None
    sections_generated: list[BriefingSection] = Field(default_factory=list)
    content: dict[str, str] = Field(
        default_factory=dict, description="section_name -> narrative text"
    )
    citations: list[dict] = Field(
        default_factory=list,
        description='[{"source": str, "event_id": str, "timestamp": str}]',
    )
    data_summary: dict[str, Any] = Field(
        default_factory=dict, description="Quick stats: event counts by type, sources used, time range"
    )
    raw_event_count: int = 0
    confidence_assessment: str = "low"  # "high" | "medium" | "low"
