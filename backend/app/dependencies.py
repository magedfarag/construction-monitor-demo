"""FastAPI dependency injection helpers.

All singletons (settings, provider registry, cache, circuit breaker) are
constructed once at application startup in main.py and accessed via these
callables.
"""
from __future__ import annotations

from typing import Optional

from backend.app.cache.client import CacheClient
from backend.app.config import AppSettings, get_settings
from backend.app.providers.registry import ProviderRegistry
from backend.app.resilience.circuit_breaker import CircuitBreaker

# These are set by main.py lifespan
_registry: Optional[ProviderRegistry] = None
_cache:    Optional[CacheClient]      = None
_breaker:  Optional[CircuitBreaker]   = None


def set_registry(r: ProviderRegistry) -> None:
    global _registry
    _registry = r


def set_cache(c: CacheClient) -> None:
    global _cache
    _cache = c


def set_breaker(b: CircuitBreaker) -> None:
    global _breaker
    _breaker = b


# FastAPI-injectable callables ─────────────────────────────────────────────

def get_app_settings() -> AppSettings:
    return get_settings()


def get_registry() -> ProviderRegistry:
    assert _registry is not None, "ProviderRegistry not initialised"
    return _registry


def get_cache() -> CacheClient:
    assert _cache is not None, "CacheClient not initialised"
    return _cache


def get_circuit_breaker() -> CircuitBreaker:
    assert _breaker is not None, "CircuitBreaker not initialised"
    return _breaker
