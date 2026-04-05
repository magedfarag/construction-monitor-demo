"""API response models."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChangeRecord(BaseModel):
    change_id: str
    detected_at: datetime
    change_type: str
    confidence: float = Field(ge=0.0, le=100.0)
    center: dict[str, float]
    bbox: list[float]
    provider: str
    summary: str
    rationale: list[str]
    before_image: str
    after_image: str
    thumbnail: str
    # Live mode extras (omitted in demo mode)
    scene_id_before: str | None = None
    scene_id_after: str | None = None
    resolution_m: int | None = None
    warnings: list[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    analysis_id: str
    requested_area_km2: float
    provider: str
    is_demo: bool = Field(
        default=False,
        description="True when results are synthetic demo data",
    )
    request_bounds: list[float]
    imagery_window: dict[str, str]
    warnings: list[str]
    changes: list[ChangeRecord]
    stats: dict[str, Any]


class JobStatusResponse(BaseModel):
    job_id: str
    state: str
    result: AnalyzeResponse | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class ProviderInfo(BaseModel):
    name: str
    display_name: str
    available: bool
    reason: str | None = None   # why unavailable, if applicable
    resolution_m: int | None = None
    notes: list[str] = Field(default_factory=list)


class ProvidersResponse(BaseModel):
    providers: list[ProviderInfo]
    demo_available: bool


class HealthResponse(BaseModel):
    status: str
    mode: str
    demo_available: bool = True
    redis: str
    celery_worker: str
    providers: dict[str, str]
    version: str = "2.0.0"
    circuit_breakers: dict[str, str] = Field(
        default_factory=dict,
        description="Per-provider circuit breaker state (closed/open/half_open)",
    )
    job_manager: str = Field(
        default="unknown",
        description="Job persistence backend in use (redis+postgresql / redis / memory)",
    )
    cache_stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Cache hit/miss ratio and backend type",
    )
    database: str = Field(
        default="not_configured",
        description="PostgreSQL connectivity status",
    )
    object_storage: str = Field(
        default="not_configured",
        description="S3/MinIO connectivity status",
    )


class ConfigResponse(BaseModel):
    today: str
    min_area_km2: float
    max_area_km2: float
    max_lookback_days: int
    supported_providers: list[str]
    app_mode: str
    async_area_threshold_km2: float
    default_cloud_threshold: float
    cache_ttl_seconds: int
    redis_available: bool
    celery_available: bool


class SceneSearchResult(BaseModel):
    scene_id: str
    provider: str
    satellite: str
    acquired_at: str
    cloud_cover: float
    bbox: list[float]
    resolution_m: int
    asset_urls: dict[str, str]


class SearchResponse(BaseModel):
    scenes: list[SceneSearchResult]
    total: int
    provider: str
    warnings: list[str]


class CreditsResponse(BaseModel):
    provider_request_counts: dict[str, int]
    cache_hit_rate: float
    cache_hits: int
    cache_misses: int
    estimated_scenes_fetched: int
