"""GET /api/health — expanded health check endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.cache.client import CacheClient
from backend.app.config import AppSettings
from backend.app.dependencies import (
    get_app_settings,
    get_cache,
    get_circuit_breaker,
    get_registry,
)
from backend.app.models.responses import HealthResponse
from backend.app.providers.registry import ProviderRegistry
from backend.app.resilience.circuit_breaker import CircuitBreaker

router = APIRouter(prefix="/api", tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service and dependency health check",
)
def health(
    settings: Annotated[AppSettings,      Depends(get_app_settings)],
    registry: Annotated[ProviderRegistry, Depends(get_registry)],
    cache:    Annotated[CacheClient,      Depends(get_cache)],
    breaker:  Annotated[CircuitBreaker,   Depends(get_circuit_breaker)],
) -> HealthResponse:
    provider_status = {}
    for p in registry.all_providers():
        ok, msg = registry.get_availability(p.provider_name)
        status_msg = "ok" if ok else msg
        # Append circuit breaker state if open
        cb_state = breaker.status(p.provider_name)
        if cb_state.value != "closed":
            status_msg = f"{status_msg} (circuit {cb_state.value})"
        provider_status[p.provider_name] = status_msg

    # Celery status — probe via inspect (best-effort)
    celery_status = "not_configured"
    if settings.redis_available():
        try:
            from celery.app.control import Inspect
            from backend.app.workers.celery_app import celery_app
            active = celery_app.control.inspect(timeout=1).active()
            celery_status = "ok" if active is not None else "no_workers"
        except Exception:  # noqa: BLE001
            celery_status = "unreachable"

    return HealthResponse(
        status="ok",
        mode=settings.app_mode,
        redis="ok" if cache.is_healthy() else "unavailable",
        celery_worker=celery_status,
        providers=provider_status,
    )
