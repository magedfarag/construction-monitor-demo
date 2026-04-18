"""Test RapidAPI maritime endpoint paths."""
from __future__ import annotations
import httpx

KEY = "d88c3a3441msh6577e9a8396594dp119d74jsn3dc1f859e097"


def test_api(host: str, paths: list[str], extra_params: dict | None = None) -> None:
    print(f"\n=== {host} ===")
    params = extra_params or {}
    for path in paths:
        try:
            r = httpx.get(
                f"https://{host}{path}",
                headers={"X-RapidAPI-Key": KEY, "X-RapidAPI-Host": host},
                params=params,
                timeout=6.0,
            )
            snippet = r.text[:200].replace("\n", " ")
            print(f"  {path}: {r.status_code} {snippet}")
        except Exception as e:
            print(f"  {path}: ERROR {e}")


# vessel-data.p.rapidapi.com
test_api(
    "vessel-data.p.rapidapi.com",
    [
        "/",
        "/v1",
        "/v1/vessels",
        "/v2",
        "/v2/vessels",
        "/vessels",
        "/vessels/list",
        "/vessels/positions",
        "/findByArea",
        "/area",
        "/getArea",
    ],
    {"lat": "25.0", "lon": "57.0", "radius": "50"},
)

# ais-hub.p.rapidapi.com
test_api(
    "ais-hub.p.rapidapi.com",
    [
        "/",
        "/v1",
        "/v1/vessels",
        "/v2",
        "/v2/vessels",
        "/vessels",
        "/positions",
        "/live",
        "/live/positions",
    ],
    {"latitude": "25.0", "longitude": "57.0", "radius": "50"},
)
