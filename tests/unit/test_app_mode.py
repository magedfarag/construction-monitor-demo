"""Unit tests for APP_MODE feature flag (P1-4)."""
from __future__ import annotations

import pytest
from backend.app.config import AppMode, AppSettings
from backend.app.providers.demo import DemoProvider
from backend.app.providers.registry import ProviderRegistry
from backend.app.providers.base import ProviderUnavailableError
from backend.app.cache.client import CacheClient
from backend.app.services.analysis import AnalysisService


class TestAppModeEnum:
    """Tests for AppMode enum definition and defaults."""

    def test_enum_has_three_values(self):
        assert set(AppMode) == {AppMode.DEMO, AppMode.STAGING, AppMode.PRODUCTION}

    def test_enum_string_values(self):
        assert AppMode.DEMO.value == "demo"
        assert AppMode.STAGING.value == "staging"
        assert AppMode.PRODUCTION.value == "production"

    def test_default_mode_is_staging(self):
        settings = AppSettings(redis_url="")
        assert settings.app_mode == AppMode.STAGING

    def test_mode_from_string_demo(self):
        settings = AppSettings(app_mode="demo", redis_url="")
        assert settings.app_mode == AppMode.DEMO

    def test_mode_from_string_production(self):
        settings = AppSettings(app_mode="production", redis_url="")
        assert settings.app_mode == AppMode.PRODUCTION


class TestProviderSelectionByMode:
    """Tests for ProviderRegistry.select_provider_by_mode()."""

    @pytest.fixture()
    def registry(self) -> ProviderRegistry:
        reg = ProviderRegistry()
        reg.register(DemoProvider())
        return reg

    def test_demo_mode_returns_demo_only(self, registry):
        providers, desc = registry.select_provider_by_mode(AppMode.DEMO)
        assert providers == ["demo"]
        assert "Demo" in desc

    def test_staging_mode_includes_fallback(self, registry):
        providers, desc = registry.select_provider_by_mode(AppMode.STAGING)
        assert "demo" in providers
        assert "sentinel2" in providers
        assert "Staging" in desc

    def test_production_mode_no_demo_fallback(self, registry):
        providers, desc = registry.select_provider_by_mode(AppMode.PRODUCTION)
        assert "demo" not in providers
        assert "sentinel2" in providers
        assert "Production" in desc


class TestResolveProviderByMode:
    """Tests for AnalysisService._resolve_provider() respecting app mode."""

    @pytest.fixture()
    def demo_registry(self) -> ProviderRegistry:
        reg = ProviderRegistry()
        reg.register(DemoProvider())
        return reg

    @pytest.fixture()
    def cache(self) -> CacheClient:
        return CacheClient(redis_url="", ttl_seconds=60, max_entries=64)

    def test_registry_respects_app_mode_demo(self, demo_registry, cache):
        """In DEMO mode, always returns demo provider regardless of request."""
        settings = AppSettings(app_mode="demo", redis_url="")
        svc = AnalysisService(registry=demo_registry, cache=cache, settings=settings)
        provider, is_demo, warnings = svc._resolve_provider("sentinel2")
        assert is_demo is True
        assert provider.provider_name == "demo"

    def test_registry_respects_app_mode_production(self, demo_registry, cache):
        """In PRODUCTION mode, raises error when no live provider is available."""
        settings = AppSettings(app_mode="production", redis_url="")
        svc = AnalysisService(registry=demo_registry, cache=cache, settings=settings)
        with pytest.raises(ProviderUnavailableError):
            svc._resolve_provider("sentinel2")

    def test_staging_mode_falls_back_to_demo(self, demo_registry, cache):
        """In STAGING mode, falls back to demo when live provider unavailable."""
        settings = AppSettings(app_mode="staging", redis_url="")
        svc = AnalysisService(registry=demo_registry, cache=cache, settings=settings)
        provider, is_demo, warnings = svc._resolve_provider("sentinel2")
        assert is_demo is True
        assert len(warnings) > 0
