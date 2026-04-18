"""
Test ais-hub.p.rapidapi.com with the correct lat/lon/radius params
vs the wrong south/west/north/east bbox params the connector sends.
"""
from __future__ import annotations
import httpx
import time

KEY = "d88c3a3441msh6577e9a8396594dp119d74jsn3dc1f859e097"
HOST = "ais-hub.p.rapidapi.com"
HEADERS = {"X-RapidAPI-Key": KEY, "X-RapidAPI-Host": HOST}

# Gulf centre: lat=25.5, lon=57.5, radius=300km covers Hormuz + entire Arabian Gulf
print("=== ais-hub: lat/lon/radius params (what worked previously) ===")
for params in [
    {"latitude": "25.5", "longitude": "57.5", "radius": "300"},
    {"lat": "25.5", "lon": "57.5", "radius": "300"},
]:
    time.sleep(2)  # avoid rate limit
    r = httpx.get(f"https://{HOST}/vessels", headers=HEADERS, params=params, timeout=10.0)
    print(f"  params={list(params.keys())}: {r.status_code} {r.text[:200]}")

print()
print("=== ais-hub: south/west/north/east params (what connector sends) ===")
time.sleep(3)
r = httpx.get(
    f"https://{HOST}/vessels",
    headers=HEADERS,
    params={"south": "24.5", "west": "55.5", "north": "27.5", "east": "60.5"},
    timeout=10.0,
)
print(f"  bbox params: {r.status_code} {r.text[:300]}")

print()
print("=== ais-hub: /v1/vessels with various params ===")
time.sleep(3)
for path, params in [
    ("/v1/vessels", {"latitude": "25.5", "longitude": "57.5", "radius": "300"}),
    ("/vessels/nearby", {"latitude": "25.5", "longitude": "57.5", "radius": "300"}),
]:
    try:
        r = httpx.get(f"https://{HOST}{path}", headers=HEADERS, params=params, timeout=10.0)
        print(f"  {path}: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"  {path}: ERROR {e}")
    time.sleep(2)
