"""POST /api/search — search imagery without running analysis."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencies import get_registry, verify_api_key
from app.models.requests import SearchRequest
from app.models.responses import SceneSearchResult, SearchResponse
from app.providers.registry import ProviderRegistry
from app.resilience.rate_limiter import SEARCH_RATE_LIMIT, limiter

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse, summary="Search satellite imagery")
@limiter.limit(SEARCH_RATE_LIMIT)
def search_imagery(
    body: SearchRequest,
    request: Request,
    registry: Annotated[ProviderRegistry, Depends(get_registry)],
    _: Annotated[str, Depends(verify_api_key)],  # Required API key authentication
) -> SearchResponse:
    provider = registry.select_provider(body.provider)
    warnings = []

    if provider is None or provider.provider_name == "demo":
        warnings.append("No live provider available; demo search returns synthetic metadata.")
        from app.providers.demo import DemoProvider
        provider = DemoProvider()

    try:
        scenes = provider.search_imagery(
            geometry=body.geometry.model_dump(),
            start_date=body.start_date.isoformat(),
            end_date=body.end_date.isoformat(),
            cloud_threshold=body.cloud_threshold,
            max_results=body.max_results,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Provider search failed: {exc!s}") from exc

    results = [
        SceneSearchResult(
            scene_id=s.scene_id,
            provider=s.provider,
            satellite=s.satellite,
            acquired_at=s.acquired_at.isoformat(),
            cloud_cover=s.cloud_cover,
            bbox=s.bbox,
            resolution_m=s.resolution_m,
            asset_urls=s.assets,
        )
        for s in scenes
    ]
    return SearchResponse(
        scenes=results,
        total=len(results),
        provider=provider.provider_name,
        warnings=warnings,
    )
