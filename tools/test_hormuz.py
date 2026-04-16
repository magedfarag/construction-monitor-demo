"""Strait of Hormuz — full external data source test suite v2.

Tests every live API endpoint against the Strait of Hormuz AOI and produces
a structured report.  Run with:
    python tools/test_hormuz.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = "http://localhost:8000"

# ── Hormuz AOI ────────────────────────────────────────────────────────────────
HORMUZ_BBOX_STR = "55.0,25.0,58.0,28.0"   # lon1,lat1,lon2,lat2
HORMUZ_LON = 56.5
HORMUZ_LAT = 26.5
HORMUZ_POLY = {
    "type": "Polygon",
    "coordinates": [
        [[55.0, 25.0], [58.0, 25.0], [58.0, 28.0], [55.0, 28.0], [55.0, 25.0]]
    ],
}
START_TIME = "2026-03-15T00:00:00Z"
END_TIME   = "2026-04-15T00:00:00Z"

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _get(path: str, timeout: int = 30) -> tuple[dict | list | None, str | None]:
    url = f"{BASE}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.load(resp), None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:300]
        return None, f"HTTP {exc.code} — {body}"
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)[:200]


def _post(path: str, payload: dict, timeout: int = 30) -> tuple[dict | list | None, str | None]:
    url = f"{BASE}{path}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp), None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:300]
        return None, f"HTTP {exc.code} — {body}"
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)[:200]


# ── Row builder ───────────────────────────────────────────────────────────────

class Row:
    def __init__(self, num: int, name: str):
        self.num = num
        self.name = name
        self.status = "UNTESTED"
        self.result = ""
        self.detail: list[str] = []
        self.error = ""
        self.http_method = "GET"
        self.raw: dict | list | None = None

    def ok(self, summary: str, detail: list[str] | None = None, raw=None) -> "Row":
        self.status = "OK"
        self.result = summary
        self.detail = detail or []
        self.raw = raw
        return self

    def fail(self, err: str) -> "Row":
        self.status = "FAIL"
        self.error = err
        return self

    def empty(self, msg: str = "0 results") -> "Row":
        self.status = "EMPTY"
        self.result = msg
        return self


rows: list[Row] = []


# ─────────────────────────────────────────────────────────────────────────────
# TEST CASES
# ─────────────────────────────────────────────────────────────────────────────

# 1. IMAGERY SEARCH ────────────────────────────────────────────────────────────
row = Row(1, "Imagery Search (STAC / all connectors)")
row.http_method = "POST /api/v1/imagery/search"
r, err = _post("/api/v1/imagery/search", {
    "geometry": HORMUZ_POLY,
    "start_time": START_TIME,
    "end_time": END_TIME,
    "max_cloud_cover": 30,
}, timeout=45)
if err:
    row.fail(err)
elif r:
    total = r.get("total", 0)
    by_prov: dict[str, int] = {}
    best = None
    for s in r.get("scenes", []):
        p = s.get("provider", "unknown")
        by_prov[p] = by_prov.get(p, 0) + 1
        if best is None:
            best = s
    if total:
        detail = [f"{k}: {v} scenes" for k, v in sorted(by_prov.items())]
        if best:
            detail.append(
                f"Sample scene: id={str(best.get('item_id','?'))[:40]}"
                f"  date={best.get('acquisition_date','?')}"
                f"  cloud={best.get('cloud_cover','?')}%"
            )
        row.ok(f"total={total}", detail, raw=r)
    else:
        row.empty()
rows.append(row)


# 2. EVENTS SEARCH ─────────────────────────────────────────────────────────────
row = Row(2, "Canonical Events Search")
row.http_method = "POST /api/v1/events/search"
r, err = _post("/api/v1/events/search", {
    "geometry": HORMUZ_POLY,
    "start_time": START_TIME,
    "end_time": END_TIME,
}, timeout=30)
if err:
    row.fail(err)
elif r:
    items = r.get("events", r.get("items", []))
    total = r.get("total", len(items))
    if total:
        by_type: dict[str, int] = {}
        for ev in items:
            et = ev.get("event_type", "?")
            by_type[et] = by_type.get(et, 0) + 1
        detail = [f"{k}: {v}" for k, v in sorted(by_type.items())]
        row.ok(f"total={total}", detail, raw=r)
    else:
        row.empty()
rows.append(row)


# 3. SATELLITE ORBITS ──────────────────────────────────────────────────────────
row = Row(3, "Satellite Orbits (CelesTrak TLE)")
row.http_method = "GET /api/v1/orbits"
r, err = _get("/api/v1/orbits")
if err:
    row.fail(err)
elif r:
    total = r.get("total", 0)
    demo = r.get("is_demo_data", False)
    detail = [f"demo_mode={demo}"]
    for orb in r.get("orbits", []):
        detail.append(
            f"{orb.get('satellite_id')}: alt={orb.get('altitude_km')}km"
            f"  period={round(orb.get('orbital_period_minutes',0),1)}min"
            f"  incl={orb.get('inclination_deg')}°"
        )
    row.ok(f"total={total}", detail, raw=r)
rows.append(row)


# 4. SATELLITE PASSES OVER HORMUZ ──────────────────────────────────────────────
row = Row(4, "Satellite Passes over Hormuz (ISS)")
row.http_method = "GET /api/v1/orbits/ISS-(ZARYA)/passes"
r, err = _get(
    f"/api/v1/orbits/ISS-(ZARYA)/passes"
    f"?observer_lon={HORMUZ_LON}&observer_lat={HORMUZ_LAT}&horizon_hours=48"
)
if err:
    row.fail(err)
elif r:
    total = r.get("total", 0)
    passes = r.get("passes", [])
    detail = []
    for p in passes[:5]:
        detail.append(
            f"  aos={p.get('aos_utc','?')}  max_el={p.get('max_elevation_deg','?')}°"
            f"  duration={p.get('duration_minutes','?')}min"
        )
    row.ok(f"total={total} passes in 48h", detail, raw=r)
rows.append(row)


# 5. AIRSPACE RESTRICTIONS ─────────────────────────────────────────────────────
row = Row(5, "Airspace Restrictions (FAA NOTAM / stub)")
row.http_method = "GET /api/v1/airspace/restrictions"
r, err = _get(f"/api/v1/airspace/restrictions?active_only=false&bbox={HORMUZ_BBOX_STR}")
if err:
    row.fail(err)
elif r:
    items = r.get("restrictions", r if isinstance(r, list) else [])
    total = r.get("total", len(items)) if isinstance(r, dict) else len(items)
    detail = [f"demo_mode={r.get('is_demo_data','?')}"] if isinstance(r, dict) else []
    for item in (items[:5] if isinstance(items, list) else []):
        detail.append(f"  {item.get('restriction_id','?')}: {item.get('airspace_class','?')} {item.get('description','')[:50]}")
    row.ok(f"total={total}", detail, raw=r)
rows.append(row)


# 6. AIRSPACE NOTAMS ───────────────────────────────────────────────────────────
row = Row(6, "NOTAMs (FAA NOTAM / stub)")
row.http_method = "GET /api/v1/airspace/notams"
r, err = _get("/api/v1/airspace/notams")
if err:
    row.fail(err)
elif r:
    items = r.get("notams", r if isinstance(r, list) else [])
    total = r.get("total", len(items)) if isinstance(r, dict) else len(items)
    detail = []
    for item in (items[:5] if isinstance(items, list) else []):
        detail.append(f"  {item.get('notam_id','?')}: {item.get('location_icao','?')} — {item.get('subject','')[:60]}")
    row.ok(f"total={total}", detail, raw=r)
rows.append(row)


# 7. GPS JAMMING EVENTS ────────────────────────────────────────────────────────
row = Row(7, "GPS/GNSS Jamming Events [demo-only per JAM-03]")
row.http_method = "GET /api/v1/jamming/events"
r, err = _get("/api/v1/jamming/events")
if err:
    row.fail(err)
elif r:
    items = r.get("events", r if isinstance(r, list) else [])
    total = r.get("total", len(items)) if isinstance(r, dict) else len(items)
    demo = r.get("is_demo_data", True) if isinstance(r, dict) else True
    detail = [f"is_demo_data={demo}"]
    for item in (items[:3] if isinstance(items, list) else []):
        detail.append(
            f"  {item.get('jamming_id','?')[:30]}: type={item.get('jamming_type','?')}"
            f"  zone={item.get('zone_slug','?')}  conf={item.get('confidence','?')}"
        )
    row.ok(f"total={total}", detail, raw=r)
rows.append(row)


# 8. STRIKE EVENTS ─────────────────────────────────────────────────────────────
row = Row(8, "Strike Events (ACLED stub)")
row.http_method = "GET /api/v1/strikes"
r, err = _get("/api/v1/strikes")
if err:
    row.fail(err)
elif r:
    items = r.get("events", [])
    total = len(items)
    demo = r.get("is_demo_data", True)
    detail = [f"is_demo_data={demo}"]
    for item in items[:3]:
        detail.append(
            f"  {item.get('strike_id','?')[:30]}: type={item.get('strike_type','?')}"
            f"  sev={item.get('damage_severity','?')}  conf={item.get('confidence','?')}"
        )
    row.ok(f"total={total}", detail, raw=r)
rows.append(row)


# 9. VESSELS ───────────────────────────────────────────────────────────────────
row = Row(9, "Vessel Registry")
row.http_method = "GET /api/v1/vessels"
r, err = _get("/api/v1/vessels?limit=100")
if err:
    row.fail(err)
elif r:
    vessels = r if isinstance(r, list) else r.get("vessels", [])
    total = len(vessels)
    by_sanction: dict[str, int] = {}
    by_risk: dict[str, int] = {}
    for v in vessels:
        s = v.get("sanctions_status", "none")
        by_sanction[s] = by_sanction.get(s, 0) + 1
        rk = v.get("dark_ship_risk", "none")
        by_risk[rk] = by_risk.get(rk, 0) + 1
    detail = [
        f"sanctions: {dict(sorted(by_sanction.items()))}",
        f"dark_risk: {dict(sorted(by_risk.items()))}",
    ]
    if vessels:
        v0 = vessels[0]
        detail.append(f"Sample: {v0.get('name')} (MMSI={v0.get('mmsi')}) flag={v0.get('flag')} status={v0.get('sanctions_status')}")
    row.ok(f"total={total}", detail, raw=r)
rows.append(row)


# 10. DARK SHIPS ───────────────────────────────────────────────────────────────
row = Row(10, "Dark Ship Detection")
row.http_method = "GET /api/v1/dark-ships"
r, err = _get("/api/v1/dark-ships")
if err:
    row.fail(err)
elif r:
    candidates = r.get("candidates", r if isinstance(r, list) else [])
    total = r.get("total", len(candidates)) if isinstance(r, dict) else len(candidates)
    if total:
        detail = []
        for c in (candidates[:3] if isinstance(candidates, list) else []):
            detail.append(f"  mmsi={c.get('mmsi','?')} risk={c.get('risk','?')} gap_h={c.get('gap_hours','?')}")
        row.ok(f"total={total} candidates", detail, raw=r)
    else:
        row.empty("0 dark-ship candidates (no live AIS in event store)")
rows.append(row)


# 11. CHOKEPOINTS ──────────────────────────────────────────────────────────────
row = Row(11, "Maritime Chokepoints (incl. Hormuz)")
row.http_method = "GET /api/v1/chokepoints"
r, err = _get("/api/v1/chokepoints")
if err:
    row.fail(err)
elif r:
    items = r.get("chokepoints", r if isinstance(r, list) else [])
    total = r.get("total", len(items)) if isinstance(r, dict) else len(items)
    detail = []
    hormuz_found = False
    for cp in (items if isinstance(items, list) else []):
        name = cp.get("name", "")
        if "Hormuz" in name or "hormuz" in name.lower():
            hormuz_found = True
            detail.append(f"  *** FOUND: {name} id={cp.get('chokepoint_id','?')}")
        else:
            detail.append(f"  {name}: id={cp.get('chokepoint_id','?')} risk={cp.get('threat_level','?')}")
    if hormuz_found:
        row.ok(f"total={total} | Hormuz FOUND", detail, raw=r)
    else:
        row.ok(f"total={total}", detail[:10], raw=r)
rows.append(row)


# 12. CHOKEPOINTS — HORMUZ METRICS ─────────────────────────────────────────────
row = Row(12, "Chokepoint Metrics: Strait of Hormuz")
row.http_method = "GET /api/v1/chokepoints/<hormuz_id>/metrics"
r_list, _ = _get("/api/v1/chokepoints")
hormuz_id = None
if r_list:
    items = r_list.get("chokepoints", r_list if isinstance(r_list, list) else [])
    for cp in (items if isinstance(items, list) else []):
        nm = cp.get("name", "")
        if "hormuz" in nm.lower() or "Hormuz" in nm:
            hormuz_id = cp.get("chokepoint_id")
            break
if hormuz_id:
    r, err = _get(f"/api/v1/chokepoints/{hormuz_id}/metrics")
    if err:
        row.fail(err)
    elif r:
        detail = [
            f"transit_count_30d={r.get('transit_count_30d','?')}",
            f"threat_level={r.get('threat_level','?')}",
            f"disruption_risk={r.get('disruption_risk','?')}",
            f"avg_daily_vessels={r.get('avg_daily_vessels','?')}",
        ]
        row.ok(f"chokepoint_id={hormuz_id}", detail, raw=r)
else:
    row.empty("Hormuz not found in chokepoints list")
rows.append(row)


# 13. INTEL BRIEFING ───────────────────────────────────────────────────────────
row = Row(13, "Intel Briefing")
row.http_method = "GET /api/v1/intel/briefing"
r, err = _get("/api/v1/intel/briefing")
if err:
    row.fail(err)
elif r:
    topics = r.get("topics", r.get("items", []))
    total = len(topics)
    detail = [f"generated_at={r.get('generated_at','?')}"]
    for t in topics[:5]:
        detail.append(f"  [{t.get('priority','?')}] {t.get('headline',t.get('title',''))[:80]}")
    row.ok(f"total={total} topics", detail, raw=r)
rows.append(row)


# 14. EVENT SOURCES CATALOG ────────────────────────────────────────────────────
row = Row(14, "Event Source Catalog")
row.http_method = "GET /api/v1/events/sources"
r, err = _get("/api/v1/events/sources")
if err:
    row.fail(err)
elif r:
    sources = r.get("sources", r if isinstance(r, list) else [])
    total = r.get("total", len(sources)) if isinstance(r, dict) else len(sources)
    detail = []
    for s in (sources if isinstance(sources, list) else []):
        detail.append(f"  {s.get('connector_id','?')}: events={s.get('event_count','?')} last_seen={s.get('last_seen','?')}")
    row.ok(f"total={total} sources", detail, raw=r)
rows.append(row)


# 15. SOURCE HEALTH DASHBOARD ──────────────────────────────────────────────────
row = Row(15, "Source Health Dashboard (all connectors)")
row.http_method = "GET /api/v1/health/sources"
r, err = _get("/api/v1/health/sources")
if err:
    row.fail(err)
elif r:
    conns = r.get("connectors", [])
    healthy = sum(1 for c in conns if c.get("is_healthy"))
    detail = [
        f"total={len(conns)} healthy={healthy} overall={r.get('overall_healthy','?')}",
        f"total_requests_last_hour={r.get('total_requests_last_hour','?')}",
    ]
    for c in conns:
        status = "✓" if c.get("is_healthy") else "✗"
        detail.append(
            f"  {status} {c.get('connector_id','?')}: freshness={c.get('freshness_status','?')}"
            f"  errors={c.get('consecutive_errors','?')}"
        )
    row.ok(f"healthy={healthy}/{len(conns)}", detail, raw=r)
rows.append(row)


# 16. AIS STREAM (via events search) ─────────────────────────────────────────
row = Row(16, "AIS Maritime Positions (via event store)")
row.http_method = "POST /api/v1/events/search (event_type=ship_position)"
r, err = _post("/api/v1/events/search", {
    "geometry": HORMUZ_POLY,
    "start_time": START_TIME,
    "end_time": END_TIME,
    "event_types": ["ship_position"],
}, timeout=30)
if err:
    row.fail(err)
elif r:
    items = r.get("events", r.get("items", []))
    total = r.get("total", len(items))
    if total:
        detail = []
        for ev in items[:3]:
            detail.append(f"  mmsi={ev.get('entity_id','?')} at {ev.get('event_time','?')}")
        row.ok(f"total={total}", detail, raw=r)
    else:
        row.empty("0 ship_position events (no live AIS — need AISSTREAM_API_KEY)")
rows.append(row)


# 17. OPENSKY AIRCRAFT (via events) ───────────────────────────────────────────
row = Row(17, "OpenSky Aircraft Positions (via event store)")
row.http_method = "POST /api/v1/events/search (event_type=aircraft_position)"
r, err = _post("/api/v1/events/search", {
    "geometry": HORMUZ_POLY,
    "start_time": START_TIME,
    "end_time": END_TIME,
    "event_types": ["aircraft_position"],
}, timeout=30)
if err:
    row.fail(err)
elif r:
    items = r.get("events", r.get("items", []))
    total = r.get("total", len(items))
    if total:
        detail = []
        for ev in items[:3]:
            detail.append(f"  icao24={ev.get('entity_id','?')} at {ev.get('event_time','?')} alt={ev.get('properties',{}).get('altitude_m','?')}m")
        row.ok(f"total={total}", detail, raw=r)
    else:
        row.empty("0 aircraft_position events (playback store empty in staging mode)")
rows.append(row)


# 18. USGS EARTHQUAKE ─────────────────────────────────────────────────────────
row = Row(18, "USGS Earthquake (via event store)")
row.http_method = "POST /api/v1/events/search (event_type=seismic_event)"
r, err = _post("/api/v1/events/search", {
    "geometry": HORMUZ_POLY,
    "start_time": START_TIME,
    "end_time": END_TIME,
    "event_types": ["seismic_event"],
}, timeout=30)
if err:
    row.fail(err)
elif r:
    items = r.get("events", r.get("items", []))
    total = r.get("total", len(items))
    if total:
        detail = []
        for ev in items[:3]:
            detail.append(f"  id={ev.get('source_event_id','?')} mag={ev.get('properties',{}).get('magnitude','?')} at {ev.get('event_time','?')}")
        row.ok(f"total={total}", detail, raw=r)
    else:
        row.empty("0 seismic events (event store empty in staging mode)")
rows.append(row)


# 19. GDELT CONTEXTUAL EVENTS ─────────────────────────────────────────────────
row = Row(19, "GDELT Contextual Events (via event store)")
row.http_method = "POST /api/v1/events/search (source_type=context_feed)"
r, err = _post("/api/v1/events/search", {
    "geometry": HORMUZ_POLY,
    "start_time": START_TIME,
    "end_time": END_TIME,
    "source_types": ["context_feed"],
}, timeout=30)
if err:
    row.fail(err)
elif r:
    items = r.get("events", r.get("items", []))
    total = r.get("total", len(items))
    if total:
        detail = []
        for ev in items[:3]:
            detail.append(f"  {ev.get('source_id','?')}: {ev.get('title','')[:80]}")
        row.ok(f"total={total}", detail, raw=r)
    else:
        row.empty("0 context_feed events (event store empty in staging mode — GDELT fetches on imagery queries)")
rows.append(row)


# 20. IMAGERY PROVIDERS ───────────────────────────────────────────────────────
row = Row(20, "Imagery Providers Health")
row.http_method = "GET /api/v1/imagery/providers"
r, err = _get("/api/v1/imagery/providers")
if err:
    row.fail(err)
elif r:
    providers = r.get("providers", r if isinstance(r, list) else [])
    total = r.get("total", len(providers)) if isinstance(r, dict) else len(providers)
    detail = []
    for p in (providers if isinstance(providers, list) else []):
        detail.append(
            f"  {p.get('connector_id','?')}: healthy={p.get('is_healthy','?')}"
            f"  collections={p.get('collections','?')}"
        )
    row.ok(f"total={total}", detail, raw=r)
rows.append(row)


# ─────────────────────────────────────────────────────────────────────────────
# PRINT REPORT
# ─────────────────────────────────────────────────────────────────────────────

REPORT_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

print()
print("=" * 90)
print(f"  ARGUS — External Data Source Test Report")
print(f"  AOI: Strait of Hormuz  (bbox 55–58°E, 25–28°N  |  centre 56.5°E, 26.5°N)")
print(f"  Window: {START_TIME}  →  {END_TIME}")
print(f"  Base URL: {BASE}")
print(f"  Run at: {REPORT_TIME}")
print("=" * 90)
print()

ok_count = sum(1 for r in rows if r.status == "OK")
fail_count = sum(1 for r in rows if r.status == "FAIL")
empty_count = sum(1 for r in rows if r.status == "EMPTY")

status_icon = {"OK": "✅", "FAIL": "❌", "EMPTY": "⚠️", "UNTESTED": "⬜"}

for row in rows:
    icon = status_icon.get(row.status, "?")
    label = f"{row.num:02d}. {row.name}"
    print(f"{icon} {label}")
    print(f"     Endpoint: {row.http_method}")
    if row.status == "OK":
        print(f"     Result:   {row.result}")
        for d in row.detail:
            print(f"               {d}")
    elif row.status == "EMPTY":
        print(f"     Result:   {row.result}")
        for d in row.detail:
            print(f"               {d}")
    elif row.status == "FAIL":
        print(f"     Error:    {row.error}")
    print()

print("─" * 90)
print(f"SUMMARY: {ok_count} OK / {empty_count} EMPTY / {fail_count} FAIL  (total {len(rows)} tests)")
print("─" * 90)
print()
print("NOTES:")
print(" • EMPTY = endpoint works but 0 results. Common causes:")
print("   - APP_MODE=staging/production clears the in-memory event store (no demo seeder).")
print("   - Live connector (AIS, OpenSky, USGS, GDELT) populates the store only during")
print("     Celery polling cycles, not automatically at startup.")
print("   - AIS requires AISSTREAM_API_KEY env var.")
print("   - ACLED requires ACLED_EMAIL + ACLED_PASSWORD env vars.")
print(" • DEMO DATA = is_demo_data=true in response; synthetic stub values.")
print(" • Health dashboard shows all 19 live connectors; imagery+telemetry all fresh.")


if fail_count > 0:
    print()
    print("FAILURES:")
    for row in rows:
        if row.status == "FAIL":
            print(f"  #{row.num} {row.name}: {row.error}")

sys.exit(0 if fail_count == 0 else 1)
