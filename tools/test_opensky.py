"""Quick OpenSky test — Gulf + Mediterranean bboxes."""
from __future__ import annotations
import httpx

BASE = "https://opensky-network.org/api"

print("=== OpenSky: Gulf (Hormuz area) ===")
try:
    r = httpx.get(
        f"{BASE}/states/all",
        params={"lamin": 24.5, "lomin": 55.5, "lamax": 27.5, "lomax": 60.5},
        timeout=15.0,
    )
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        states = data.get("states") or []
        print(f"  Aircraft count: {len(states)}")
        for s in states[:3]:
            callsign = s[1] or "??"
            lat = s[6]
            lon = s[5]
            print(f"    {callsign.strip()} @ lat={lat} lon={lon}")
    else:
        print(f"  Response: {r.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")

print()
print("=== OpenSky: Mediterranean ===")
try:
    r = httpx.get(
        f"{BASE}/states/all",
        params={"lamin": 30.0, "lomin": -5.0, "lamax": 47.0, "lomax": 37.0},
        timeout=15.0,
    )
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        states = data.get("states") or []
        print(f"  Aircraft count: {len(states)}")
        for s in states[:3]:
            callsign = s[1] or "??"
            lat = s[6]
            lon = s[5]
            print(f"    {callsign.strip()} @ lat={lat} lon={lon}")
    else:
        print(f"  Response: {r.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")
