"""Investigation entity model — Phase 5 Track A.

Provides the Pydantic v2 models for saved investigations, watchlists,
analyst notes, saved filters, and evidence linking.

All datetime fields are UTC-aware.  IDs are auto-generated UUIDs.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from src.models.operational_layers import EvidenceLink

# ──────────────────────────────────────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────────────────────────────────────


class InvestigationStatus(str, Enum):
    """Lifecycle states for an investigation."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"


class WatchlistEntryType(str, Enum):
    """Entity categories that can be added to an investigation watchlist."""
    VESSEL = "vessel"
    AIRCRAFT = "aircraft"
    LOCATION = "location"
    EVENT_PATTERN = "event_pattern"
    PERSON = "person"


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
# Sub-models
# ──────────────────────────────────────────────────────────────────────────────


class WatchlistEntry(BaseModel):
    """A single entity under active monitoring within an investigation."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    entry_type: WatchlistEntryType
    identifier: str = Field(..., description="MMSI, ICAO hex, lat/lon pair, etc.")
    label: str | None = Field(default=None, description="Human-readable display name")
    notes: str | None = Field(default=None)
    added_at: datetime = Field(default_factory=_utc_now)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("added_at", mode="before")
    @classmethod
    def _utc_added_at(cls, v: Any) -> Any:
        return _require_utc(v)


class InvestigationNote(BaseModel):
    """A free-text analyst note attached to an investigation."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    investigation_id: str
    content: str
    author: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    tags: list[str] = Field(default_factory=list)

    @field_validator("created_at", mode="before")
    @classmethod
    def _utc_created_at(cls, v: Any) -> Any:
        return _require_utc(v)


class InvestigationNoteCreateRequest(BaseModel):
    """Payload for creating a new analyst note on an investigation."""

    content: str
    author: str | None = None
    tags: list[str] = Field(default_factory=list)


class SavedFilter(BaseModel):
    """A named query filter captured for reuse inside an investigation."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    filter_definition: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary JSON filter parameters, e.g. event_types, aoi_id, time_range",
    )
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("created_at", mode="before")
    @classmethod
    def _utc_created_at(cls, v: Any) -> Any:
        return _require_utc(v)


# ──────────────────────────────────────────────────────────────────────────────
# Core entity
# ──────────────────────────────────────────────────────────────────────────────


class Investigation(BaseModel):
    """Top-level investigation entity — the analyst's workspace."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str | None = None
    status: InvestigationStatus = InvestigationStatus.DRAFT
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    created_by: str | None = None
    tags: list[str] = Field(default_factory=list)
    watchlist: list[WatchlistEntry] = Field(default_factory=list)
    notes: list[InvestigationNote] = Field(default_factory=list)
    saved_filters: list[SavedFilter] = Field(default_factory=list)
    evidence_links: list[EvidenceLink] = Field(default_factory=list)
    linked_event_ids: list[str] = Field(
        default_factory=list,
        description="Canonical event_id values associated with this investigation",
    )

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _utc_timestamps(cls, v: Any) -> Any:
        return _require_utc(v)

    @model_validator(mode="after")
    def _updated_at_gte_created_at(self) -> Investigation:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must be >= created_at")
        return self


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────────────────────────────────────


class InvestigationCreateRequest(BaseModel):
    """Payload for creating a new investigation."""

    name: str
    description: str | None = None
    created_by: str | None = None
    tags: list[str] = Field(default_factory=list)


class InvestigationUpdateRequest(BaseModel):
    """Partial-update payload — all fields optional."""

    name: str | None = None
    description: str | None = None
    status: InvestigationStatus | None = None
    tags: list[str] | None = None


class InvestigationListResponse(BaseModel):
    """Paginated list of investigations."""

    items: list[Investigation]
    total: int


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

__all__ = [
    "InvestigationStatus",
    "WatchlistEntryType",
    "WatchlistEntry",
    "InvestigationNote",
    "InvestigationNoteCreateRequest",
    "SavedFilter",
    "Investigation",
    "InvestigationCreateRequest",
    "InvestigationUpdateRequest",
    "InvestigationListResponse",
]
