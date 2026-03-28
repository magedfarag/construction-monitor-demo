"""Integration tests for all API endpoints."""
from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from backend.app import dependencies
from backend.app.cache.client import CacheClient
from backend.app.providers.demo import DemoProvider
from backend.app.providers.registry import ProviderRegistry
from backend.app.resilience.circuit_breaker import CircuitBreaker

POLYGON = {"type": "Polygon", "coordinates": [[[30.0,50.0],[30.1,50.0],[30.1,50.1],[30.0,50.1],[30.0,50.0]]]}

@pytest.fixture(scope="module")
def client():
    reg = ProviderRegistry(); reg.register(DemoProvider())
    dependencies.set_registry(reg)
    dependencies.set_cache(CacheClient())
    dependencies.set_breaker(CircuitBreaker())
    from backend.app.main import app
    from backend.app.resilience.rate_limiter import limiter
    limiter.reset()
    return TestClient(app, raise_server_exceptions=True)

def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"

def test_config_returns_today(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    assert r.json()["today"] == "2026-03-28"

def test_providers_includes_demo(client):
    r = client.get("/api/providers")
    assert r.status_code == 200
    assert any(p["name"] == "demo" for p in r.json()["providers"])

def test_analyze_demo_3_changes(client):
    r = client.post("/api/analyze", json={"geometry": POLYGON, "start_date": "2026-03-01", "end_date": "2026-03-28", "provider": "demo"})
    assert r.status_code == 200
    body = r.json()
    assert body["is_demo"] is True and body["stats"]["total_changes"] == 3

def test_analyze_change_has_required_fields(client):
    r = client.post("/api/analyze", json={"geometry": POLYGON, "start_date": "2026-03-01", "end_date": "2026-03-28", "provider": "demo"})
    c = r.json()["changes"][0]
    for f in ["change_id", "change_type", "confidence", "center", "bbox", "summary", "rationale"]:
        assert f in c

def test_analyze_invalid_geometry_422(client):
    r = client.post("/api/analyze", json={"geometry": {"type": "Point", "coordinates": [30.0, 50.0]}, "start_date": "2026-03-01", "end_date": "2026-03-28"})
    assert r.status_code == 422

def test_analyze_bad_date_order_422(client):
    r = client.post("/api/analyze", json={"geometry": POLYGON, "start_date": "2026-03-28", "end_date": "2026-03-01"})
    assert r.status_code == 422

def test_search_endpoint(client):
    r = client.post("/api/search", json={"geometry": POLYGON, "start_date": "2026-03-01", "end_date": "2026-03-28", "provider": "demo"})
    assert r.status_code == 200 and "scenes" in r.json()

def test_credits_endpoint(client):
    assert client.get("/api/credits").status_code == 200

def test_jobs_without_redis_503(client):
    assert client.get("/api/jobs/test-id").status_code == 503

def test_root_serves_index(client):
    assert client.get("/").status_code == 200
