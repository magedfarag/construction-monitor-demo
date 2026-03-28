"""Unit tests for CacheClient."""
from __future__ import annotations
from backend.app.cache.client import CacheClient

def test_memory_cache_set_get():
    c = CacheClient(redis_url="", ttl_seconds=10, max_entries=16)
    c.set("k", {"data": 42})
    assert c.get("k") == {"data": 42}

def test_memory_cache_miss_returns_none():
    c = CacheClient(redis_url="", ttl_seconds=10, max_entries=16)
    assert c.get("missing") is None

def test_memory_cache_delete():
    c = CacheClient(redis_url="", ttl_seconds=10, max_entries=16)
    c.set("k", "v"); c.delete("k")
    assert c.get("k") is None

def test_hit_rate_stats():
    c = CacheClient(redis_url="", ttl_seconds=10, max_entries=16)
    c.set("x", 1)
    c.get("x"); c.get("missing")
    s = c.stats()
    assert s["hits"] == 1 and s["misses"] == 1 and s["hit_rate"] == 0.5

def test_is_healthy_memory():
    assert CacheClient(redis_url="", ttl_seconds=10, max_entries=4).is_healthy() is True

def test_redis_fallback_on_invalid_url():
    c = CacheClient(redis_url="redis://invalid.local:9999/0", ttl_seconds=10, max_entries=4)
    c.set("k", "v")
    assert c.get("k") == "v"
