from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app import dependencies
from backend.app.cache.client import CacheClient
from backend.app.config import get_settings
from backend.app.logging_config import configure_logging
from backend.app.providers.demo import DemoProvider
from backend.app.providers.registry import ProviderRegistry
from backend.app.resilience.circuit_breaker import CircuitBreaker

APP_DIR    = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    import logging as _log
    settings = get_settings()
    configure_logging(log_level=settings.log_level, log_format=settings.log_format)
    registry = ProviderRegistry()
    registry.register(DemoProvider())
    if settings.sentinel2_is_configured():
        try:
            from backend.app.providers.sentinel2 import Sentinel2Provider
            registry.register(Sentinel2Provider(settings))
        except Exception as exc:
            _log.getLogger(__name__).warning("Sentinel2Provider: %s", exc)
    if settings.landsat_is_configured():
        try:
            from backend.app.providers.landsat import LandsatProvider
            registry.register(LandsatProvider(settings))
        except Exception as exc:
            _log.getLogger(__name__).warning("LandsatProvider: %s", exc)
    cache   = CacheClient.from_settings(settings)
    breaker = CircuitBreaker(
        failure_threshold=settings.circuit_breaker_failure_threshold,
        recovery_timeout=settings.circuit_breaker_recovery_timeout,
    )
    dependencies.set_registry(registry)
    dependencies.set_cache(cache)
    dependencies.set_breaker(breaker)
    _log.getLogger(__name__).info(
        "Application started | mode=%s providers=%s redis=%s",
        settings.app_mode,
        [p.provider_name for p in registry.all_providers()],
        "yes" if settings.redis_available() else "no",
    )
    yield

app = FastAPI(
    title="Construction Activity Monitor",
    version="2.0.0",
    description="Detects construction activity in satellite imagery.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

from backend.app.routers import health, config_router, providers_router, credits, analyze, jobs, search
app.include_router(health.router)
app.include_router(config_router.router)
app.include_router(providers_router.router)
app.include_router(credits.router)
app.include_router(analyze.router)
app.include_router(jobs.router)
app.include_router(search.router)
