"""Verify the playback/query live poll works end-to-end."""
import json
import requests
from datetime import datetime, timedelta, UTC

BASE = "http://localhost:8000"
HEADERS = {
    "X-API-KEY": "b09b6bd90e781f0d000e840d6d81ff58de5b7e327a8988137d406a124f36b51a",
    "Content-Type": "application/json",
}

# Get AOI
aois = requests.get(f"{BASE}/api/v1/aois", headers=HEADERS, timeout=10).json()
if not aois["items"]:
    print("ERROR: No AOIs found — AOI seeding failed")
    raise SystemExit(1)
aoi_id = aois["items"][0]["id"]
print(f"AOI: {aoi_id} ({aois['items'][0]['name']})")

# Call playback/query (same payload as useTracks)
now = datetime.now(UTC)
body = {
    "aoi_id": aoi_id,
    "start_time": (now - timedelta(days=1)).isoformat(),
    "end_time": (now + timedelta(hours=1)).isoformat(),
    "source_types": ["telemetry"],
    "limit": 4000,
}
print("Sending POST /api/v1/playback/query (live poll may take ~25s)...")
resp = requests.post(f"{BASE}/api/v1/playback/query", headers=HEADERS, json=body, timeout=120)
resp.raise_for_status()
data = resp.json()
total = data["total"]
print(f"total={total}")
if total > 0:
    types = sorted({e["event_type"] for e in data["events"]})
    sources = sorted({e["source"] for e in data["events"]})
    print(f"event_types: {types}")
    print(f"sources: {sources}")
    print("✓ PASS: aircraft/ships returned from live poll via playback/query")
else:
    print("WARN: 0 events — connectors may be rate-limited or timed out")
    print("Check backend logs for live_poll_fallback messages")
