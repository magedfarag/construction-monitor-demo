"""Test AISStream with broader Gulf/Middle East areas and longer timeout."""
from __future__ import annotations
import asyncio
import json
import websockets

API_KEY = "048b46dade03ee3603271f1eae849acfa859d6b5"
URL = "wss://stream.aisstream.io/v0/stream"


async def test_bbox(name: str, bbox: list, timeout_s: int = 25) -> list:
    """Try AISStream bbox and return any messages received."""
    msg = {
        "APIKey": API_KEY,
        "BoundingBoxes": [bbox],
        "FilterMessageTypes": ["PositionReport", "ExtendedClassBPositionReport"],
    }
    print(f"\n--- Testing {name} ---")
    print(f"  BoundingBoxes: {[bbox]}")
    collected = []
    try:
        async with websockets.connect(URL, open_timeout=10) as ws:
            await ws.send(json.dumps(msg))
            print(f"  Connected and subscribed. Waiting {timeout_s}s...")
            deadline = asyncio.get_event_loop().time() + timeout_s
            while asyncio.get_event_loop().time() < deadline and len(collected) < 5:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(raw)
                    meta = data.get("MetaData", {})
                    pos_report = (
                        data.get("Message", {}).get("PositionReport") or
                        data.get("Message", {}).get("ExtendedClassBPositionReport") or {}
                    )
                    lat = pos_report.get("Latitude", meta.get("latitude"))
                    lon = pos_report.get("Longitude", meta.get("longitude"))
                    mmsi = meta.get("MMSI")
                    ship = meta.get("ShipName", "Unknown")
                    print(f"  [{len(collected)+1}] MMSI={mmsi} name={ship!r} lat={lat} lon={lon}")
                    collected.append(data)
                except (asyncio.TimeoutError, TimeoutError):
                    continue
    except Exception as e:
        print(f"  ERROR: {e}")

    if collected:
        print(f"  Got {len(collected)} messages!")
    else:
        print(f"  No messages in {timeout_s}s.")
    return collected


async def main():
    # Test 1: Hormuz only (narrow) — baseline
    await test_bbox("HORMUZ (narrow)", [[24.5, 55.5], [27.5, 60.5]], timeout_s=15)

    # Test 2: Broader Gulf including UAE coast (major shipping hub)
    await test_bbox("BROADER GULF + UAE coast", [[22.0, 50.0], [28.0, 62.0]], timeout_s=20)

    # Test 3: Persian Gulf + Arabian Sea
    await test_bbox("PERSIAN GULF + ARABIAN SEA", [[15.0, 50.0], [30.0, 65.0]], timeout_s=20)

    # Test 4: Mediterranean (confirmed working area)
    await test_bbox("MEDITERRANEAN (control)", [[30.0, -5.0], [47.0, 37.0]], timeout_s=10)


asyncio.run(main())
