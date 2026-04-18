"""Quick AISStream connectivity and bbox verification test."""
from __future__ import annotations
import asyncio
import json


async def test(bbox_desc: str, bbox: list) -> None:
    import websockets  # type: ignore[import-untyped]
    url = "wss://stream.aisstream.io/v0/stream"
    msg = {
        "APIKey": "048b46dade03ee3603271f1eae849acfa859d6b5",
        "BoundingBoxes": [bbox],
        "FilterMessageTypes": ["PositionReport"],
    }
    print(f"\n--- Testing {bbox_desc} ---")
    print(f"  Subscription: {json.dumps(msg['BoundingBoxes'])}")
    try:
        async with websockets.connect(url, open_timeout=10) as ws:
            await ws.send(json.dumps(msg))
            print("  Connected and subscribed.")
            collected = 0
            for _ in range(12):  # 12 x 1s = 12 seconds
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    data = json.loads(raw)
                    msg_type = data.get("MessageType", "?")
                    if "error" in data:
                        print(f"  ERROR from server: {data['error']}")
                        return
                    meta = data.get("MetaData", {})
                    mmsi = meta.get("MMSI", "?")
                    lat = meta.get("latitude", "?")
                    lon = meta.get("longitude", "?")
                    print(f"  [{collected+1}] {msg_type}: MMSI={mmsi} lat={lat} lon={lon}")
                    collected += 1
                    if collected >= 3:
                        break
                except (asyncio.TimeoutError, TimeoutError):
                    pass
            if collected == 0:
                print("  No messages received in 12 seconds.")
            else:
                print(f"  Received {collected} messages. AISStream is working!")
    except Exception as e:
        print(f"  Connection failed: {e}")


async def main() -> None:
    # Test 1: World bbox
    await test("WORLD bbox", [[-90, -180], [90, 180]])
    # Test 2: Hormuz bbox (fixed format)
    await test("HORMUZ bbox [[-90,-180],[90,180]]", [[24.5, 55.5], [27.5, 60.5]])


asyncio.run(main())
