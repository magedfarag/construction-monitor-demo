"""Test ais-hub.p.rapidapi.com with latmin/latmax/lonmin/lonmax params
(the format used by the real AIS Hub API at data.aishub.net).
"""
from __future__ import annotations
import httpx
import time

KEY = "d88c3a3441msh6577e9a8396594dp119d74jsn3dc1f859e097"
HOST = "ais-hub.p.rapidapi.com"
HEADERS = {"X-RapidAPI-Key": KEY, "X-RapidAPI-Host": HOST}

print("=== ais-hub: latmin/latmax/lonmin/lonmax params (AIS Hub API format) ===")
print()

# Test 1: Gulf / Hormuz bbox
time.sleep(1)
params_gulf = {
    "latmin": "24.5",
    "latmax": "27.5",
    "lonmin": "55.5",
    "lonmax": "60.5",
    "format": "1",
    "output": "json",
}
r = httpx.get(f"https://{HOST}/vessels", headers=HEADERS, params=params_gulf, timeout=10.0)
print(f"Gulf bbox /vessels: {r.status_code}")
print(f"  Response: {r.text[:400]}")
print()

time.sleep(2)

# Test 2: Mediterranean bbox (control — AISStream confirmed ships here)
params_med = {
    "latmin": "30.0",
    "latmax": "47.0",
    "lonmin": "-5.0",
    "lonmax": "37.0",
    "format": "1",
    "output": "json",
}
r = httpx.get(f"https://{HOST}/vessels", headers=HEADERS, params=params_med, timeout=10.0)
print(f"Mediterranean bbox /vessels: {r.status_code}")
print(f"  Response: {r.text[:400]}")
print()

time.sleep(2)

# Test 3: /v1/vessels with same params
params_v1 = {
    "latmin": "30.0",
    "latmax": "47.0",
    "lonmin": "-5.0",
    "lonmax": "37.0",
    "format": "1",
    "output": "json",
}
r = httpx.get(f"https://{HOST}/v1/vessels", headers=HEADERS, params=params_v1, timeout=10.0)
print(f"Mediterranean bbox /v1/vessels: {r.status_code}")
print(f"  Response: {r.text[:400]}")
print()

time.sleep(2)

# Test 4: No bbox params (return all vessels)
r = httpx.get(
    f"https://{HOST}/vessels",
    headers=HEADERS,
    params={"format": "1", "output": "json"},
    timeout=10.0,
)
print(f"No bbox (all vessels) /vessels: {r.status_code}")
print(f"  Response: {r.text[:400]}")
