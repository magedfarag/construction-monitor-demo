# Strait of Hormuz data source test runner
# Run: python tools/run_hormuz_test.py
import json, sys, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

BASE = "http://localhost:8000"
POLY = {"type":"Polygon","coordinates":[[[55.0,25.0],[58.0,25.0],[58.0,28.0],[55.0,28.0],[55.0,25.0]]]}
LON, LAT = 56.5, 26.5
BBOX = "55.0,25.0,58.0,28.0"
T1, T2 = "2026-03-15T00:00:00Z", "2026-04-15T00:00:00Z"

# Live-telemetry tests (#16, #17, #20) use a rolling window that includes NOW
# so that best-effort live-poll events (ingested with event_time=now) are visible.
_NOW = datetime.now(timezone.utc)
T_LIVE1 = (_NOW - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
T_LIVE2 = (_NOW + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

def xget(path):
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r: return json.load(r), None
    except urllib.error.HTTPError as e: return None, f"HTTP {e.code}: {e.read().decode()[:100]}"
    except Exception as e: return None, str(e)[:80]

def xpost(path, body):
    d = json.dumps(body).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=d, headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as r: return json.load(r), None
    except urllib.error.HTTPError as e: return None, f"HTTP {e.code}: {e.read().decode()[:150]}"
    except Exception as e: return None, str(e)[:80]

rows = []

# 1 - IMAGERY SEARCH
r, err = xpost("/api/v1/imagery/search", {"geometry":POLY,"start_time":T1,"end_time":T2,"max_cloud_cover":30})
if err:
    rows.append(("FAIL","01","Imagery Search (STAC multi-catalog)","POST /api/v1/imagery/search",err,[]))
else:
    total = r.get("total_items", r.get("total", 0))
    items = r.get("items", r.get("scenes", []))
    by_c = {}
    for s in items:
        c = s.get("connector_id", s.get("provider","?"))
        by_c[c] = by_c.get(c,0)+1
    details = [f"  {k}: {v} scenes" for k,v in sorted(by_c.items())]
    if items:
        s0 = items[0]
        details.append(f"  Sample: {s0.get('entity_id','?')}")
        details.append(f"    date={s0.get('event_time','')[:10]}  cloud={s0.get('cloud_cover_pct','?')}%  gsd={s0.get('gsd_m','?')}m  platform={s0.get('platform','?')}")
        details.append(f"    preview={s0.get('scene_url','n/a')}")
    rows.append(("OK" if total else "EMPTY","01","Imagery Search","POST /api/v1/imagery/search",f"total_items={total}",details))

# 2 - EVENTS SEARCH
r, err = xpost("/api/v1/events/search", {"geometry":POLY,"start_time":T1,"end_time":T2})
if err:
    rows.append(("FAIL","02","Canonical Events Search","POST /api/v1/events/search",err,[]))
else:
    total = r.get("total", 0)
    rows.append(("OK" if total else "EMPTY","02","Canonical Events Search","POST /api/v1/events/search",f"total={total}",["  In-memory store empty: APP_MODE != demo"]))

# 3 - ORBITS
r, err = xget("/api/v1/orbits")
if err:
    rows.append(("FAIL","03","Satellite Orbits","GET /api/v1/orbits",err,[]))
else:
    orbs = r.get("orbits",[])
    details = [f"  {o.get('satellite_id')}: alt={o.get('altitude_km')}km  incl={o.get('inclination_deg')}deg  period={round(o.get('orbital_period_minutes',0),1)}min  norad_id={o.get('norad_id')}" for o in orbs]
    details.insert(0, f"  is_demo_data={r.get('is_demo_data')}  source=CelesTrak TLE stub")
    rows.append(("OK","03","Satellite Orbits (CelesTrak TLE)","GET /api/v1/orbits",f"total={r.get('total',0)}",details))

# 4 - ISS PASSES
r, err = xget(f"/api/v1/orbits/ISS-(ZARYA)/passes?lon={LON}&lat={LAT}&horizon_hours=48")
if err:
    rows.append(("FAIL","04","ISS Passes over Hormuz",f"GET .../ISS-(ZARYA)/passes?lon={LON}&lat={LAT}",err,[]))
else:
    passes = r.get("passes",[])
    details = [f"  AOS={p.get('aos','?')[:19]}Z  LOS={p.get('los','?')[11:19]}Z  max_el={p.get('max_elevation_deg','?')}deg" for p in passes[:6]]
    if len(passes)>6: details.append(f"  ... +{len(passes)-6} more passes")
    rows.append(("OK","04","ISS Passes over Hormuz (48h)",f"GET .../ISS-(ZARYA)/passes?lon={LON}&lat={LAT}&horizon_hours=48",f"total={r.get('total',0)} passes  is_demo={r.get('is_demo_data')}",details))

# 5 - SENTINEL-2A PASSES
r, err = xget(f"/api/v1/orbits/SENTINEL-2A/passes?lon={LON}&lat={LAT}&horizon_hours=48")
if err:
    rows.append(("FAIL","05","Sentinel-2A Passes",f"GET .../SENTINEL-2A/passes",err,[]))
else:
    passes = r.get("passes",[])
    details = [f"  AOS={p.get('aos','?')[:19]}Z  max_el={p.get('max_elevation_deg','?')}deg" for p in passes[:4]]
    rows.append(("OK","05","Sentinel-2A Passes over Hormuz (48h)",f"GET .../SENTINEL-2A/passes?lon={LON}&lat={LAT}&horizon_hours=48",f"total={len(passes)} passes",details))

# 6 - AIRSPACE RESTRICTIONS
r, err = xget(f"/api/v1/airspace/restrictions?active_only=false&bbox={BBOX}")
if err:
    rows.append(("FAIL","06","Airspace Restrictions",f"GET .../airspace/restrictions?bbox={BBOX}",err,[]))
else:
    items = r.get("restrictions", r if isinstance(r,list) else [])
    total = r.get("total", len(items) if isinstance(items,list) else 0)
    details = [f"  is_demo_data={r.get('is_demo_data','?')}"]
    for x in (items[:4] if isinstance(items,list) else []):
        details.append(f"  {x.get('restriction_id','?')}: class={x.get('airspace_class','?')}  {x.get('description','')[:60]}")
    rows.append(("EMPTY" if not total else "OK","06","Airspace Restrictions (FAA NOTAM stub)",f"GET .../airspace/restrictions?active_only=false&bbox={BBOX}",f"total={total}",details))

# 7 - NOTAMS
r, err = xget("/api/v1/airspace/notams")
if err:
    rows.append(("FAIL","07","NOTAMs","GET /api/v1/airspace/notams",err,[]))
else:
    items = r.get("notams", r if isinstance(r,list) else [])
    total = r.get("total", len(items) if isinstance(items,list) else 0)
    details = [f"  is_demo_data={r.get('is_demo_data','?')}"]
    for x in (items[:5] if isinstance(items,list) else []):
        details.append(f"  {x.get('notam_id','?')}: icao={x.get('location_icao','?')}  {x.get('subject','')[:60]}")
    rows.append(("OK" if total else "EMPTY","07","NOTAMs (FAA NOTAM stub)","GET /api/v1/airspace/notams",f"total={total}",details))

# 8 - JAMMING EVENTS
r, err = xget("/api/v1/jamming/events")
if err:
    rows.append(("FAIL","08","GPS Jamming","GET /api/v1/jamming/events",err,[]))
else:
    items = r.get("events", r if isinstance(r,list) else [])
    total = r.get("total", len(items) if isinstance(items,list) else 0)
    details = [f"  is_demo_data={r.get('is_demo_data',True)} [PERMANENT — no approved public GNSS feed; JAM-03 policy]"]
    for x in (items[:4] if isinstance(items,list) else []):
        details.append(f"  type={x.get('jamming_type','?')}  conf={x.get('confidence','?')}  zone={x.get('zone_slug','?')}")
    rows.append(("OK","08","GPS/GNSS Jamming Events [demo-only JAM-03]","GET /api/v1/jamming/events",f"total={total}",details))

# 9 - STRIKE EVENTS
r, err = xget("/api/v1/strikes")
if err:
    rows.append(("FAIL","09","Strike Events","GET /api/v1/strikes",err,[]))
else:
    events = r.get("events",[])
    details = [f"  is_demo_data={r.get('is_demo_data',True)}  [stub — needs ACLED credentials for live]"]
    for x in events[:4]:
        details.append(f"  {x.get('strike_type','?'):10}  sev={x.get('damage_severity','?'):10}  conf={x.get('confidence','?')}  target={x.get('target_description','?')}")
    rows.append(("OK","09","Strike Events (ACLED stub)","GET /api/v1/strikes",f"total={len(events)}",details))

# 10 - VESSELS
r, err = xget("/api/v1/vessels?limit=100")
if err:
    rows.append(("FAIL","10","Vessel Registry","GET /api/v1/vessels",err,[]))
else:
    vessels = r if isinstance(r,list) else r.get("vessels",[])
    by_s, by_r = {}, {}
    for v in vessels:
        s = v.get("sanctions_status","?"); by_s[s] = by_s.get(s,0)+1
        rk = v.get("dark_ship_risk","?"); by_r[rk] = by_r.get(rk,0)+1
    details = [f"  sanctions: {dict(sorted(by_s.items()))}", f"  dark_risk: {dict(sorted(by_r.items()))}"]
    for v in vessels[:5]:
        details.append(f"  {v.get('name','?'):22} MMSI={v.get('mmsi','?')}  flag={v.get('flag','?')}  status={v.get('sanctions_status','?'):12}  risk={v.get('dark_ship_risk','?')}")
    rows.append(("OK","10","Vessel Registry","GET /api/v1/vessels?limit=100",f"total={len(vessels)}",details))

# 11 - DARK SHIPS
r, err = xget("/api/v1/dark-ships")
if err:
    rows.append(("FAIL","11","Dark Ships","GET /api/v1/dark-ships",err,[]))
else:
    cand = r.get("candidates", r if isinstance(r,list) else [])
    total = r.get("total", len(cand) if isinstance(cand,list) else 0)
    if total:
        rows.append(("OK","11","Dark Ship Detection","GET /api/v1/dark-ships",f"total={total} candidates",[]))
    else:
        rows.append(("EMPTY","11","Dark Ship Detection","GET /api/v1/dark-ships","0 candidates",["  No live AIS data in event store (needs AISSTREAM_API_KEY + Celery worker)"]))

# 12 - CHOKEPOINTS LIST
r, err = xget("/api/v1/chokepoints")
hormuz_id = None
if err:
    rows.append(("FAIL","12","Maritime Chokepoints","GET /api/v1/chokepoints",err,[]))
else:
    items = r.get("chokepoints", r if isinstance(r,list) else [])
    details = []
    for cp in (items if isinstance(items,list) else []):
        nm = cp.get("name","?")
        if "hormuz" in nm.lower(): hormuz_id = cp.get("id", cp.get("chokepoint_id"))
        star = "*** " if "hormuz" in nm.lower() else "    "
        details.append(f"  {star}{nm}: threat={cp.get('threat_level','?')}/{cp.get('threat_label','?')}  flow={cp.get('daily_flow_mbbl','?')} MBBL/d  vessels_24h={cp.get('vessel_count_24h','?')}")
    rows.append(("OK","12","Maritime Chokepoints","GET /api/v1/chokepoints",f"total={len(items) if isinstance(items,list) else 0}",details))

# 13 - HORMUZ METRICS
if hormuz_id:
    r, err = xget(f"/api/v1/chokepoints/{hormuz_id}/metrics")
    if err:
        rows.append(("FAIL","13","Hormuz Metrics",f"GET /api/v1/chokepoints/{hormuz_id}/metrics",err,[]))
    else:
        details = [f"  {k}: {v}" for k,v in (r.items() if isinstance(r,dict) else []) if not isinstance(v,(dict,list))]
        rows.append(("OK","13","Hormuz Chokepoint Metrics",f"GET /api/v1/chokepoints/{hormuz_id}/metrics",f"id={hormuz_id}",details))
else:
    rows.append(("EMPTY","13","Hormuz Metrics","GET /api/v1/chokepoints/<id>/metrics","Hormuz ID not resolved",[]))

# 14 - INTEL BRIEFING
r, err = xget("/api/v1/intel/briefing")
if err:
    rows.append(("FAIL","14","Intel Briefing","GET /api/v1/intel/briefing",err,[]))
else:
    details = [
        f"  risk_level={r.get('risk_level','?')}  classification={r.get('classification','?')}",
        f"  dark_ships={r.get('dark_ship_count','?')}  sanctioned_vessels={r.get('sanctioned_vessel_count','?')}  active_vessels={r.get('active_vessel_count','?')}",
        f"  summary: {r.get('executive_summary','')[:120]}",
    ]
    for f in r.get("key_findings",[])[:4]:
        details.append(f"  finding: {str(f)[:100]}")
    for cp in r.get("chokepoint_status",[])[:4]:
        details.append(f"  [{cp.get('name','?')}] {cp.get('threat_label','?')}  flow={cp.get('daily_flow_mbbl','?')} MBBL/d")
    rows.append(("OK","14","Intel Briefing","GET /api/v1/intel/briefing",f"risk={r.get('risk_level','?')}",details))

# 15 - SOURCE HEALTH
r, err = xget("/api/v1/health/sources")
if err:
    rows.append(("FAIL","15","Source Health","GET /api/v1/health/sources",err,[]))
else:
    conns = r.get("connectors",[])
    healthy = sum(1 for c in conns if c.get("is_healthy"))
    details = [f"  overall_healthy={r.get('overall_healthy')}  total_requests_last_hour={r.get('total_requests_last_hour')}"]
    for c in conns:
        ico = "OK" if c.get("is_healthy") else "XX"
        age = c.get("freshness_age_minutes")
        age_s = f"{round(age,0)}min" if age else "never"
        details.append(f"  [{ico}] {c.get('connector_id','?'):32}  freshness={c.get('freshness_status','?'):8}  last_ok={age_s}  consecutive_errors={c.get('consecutive_errors','?')}")
    rows.append(("OK","15","Source Health Dashboard","GET /api/v1/health/sources",f"healthy={healthy}/{len(conns)}",details))

# 16 - AIS
r, err = xpost("/api/v1/events/search", {"geometry":POLY,"start_time":T_LIVE1,"end_time":T_LIVE2,"event_types":["ship_position"]})
total = r.get("total",0) if r else 0
rows.append(("OK" if total else "EMPTY","16","AIS Ship Positions (event store)","POST /api/v1/events/search {event_types=[ship_position]}",f"total={total}",["  AIS store empty — needs AISSTREAM_API_KEY + Celery worker running"] if not total else []))

# 17 - AIRCRAFT
r, err = xpost("/api/v1/events/search", {"geometry":POLY,"start_time":T_LIVE1,"end_time":T_LIVE2,"event_types":["aircraft_position"]})
total = r.get("total",0) if r else 0
rows.append(("OK" if total else "EMPTY","17","Aircraft Positions (event store)","POST /api/v1/events/search {event_types=[aircraft_position]}",f"total={total}",["  OpenSky connector healthy but event store empty (staging mode, no Celery)"] if not total else []))

# 18 - IMAGERY PROVIDERS
r, err = xget("/api/v1/imagery/providers")
if err:
    rows.append(("FAIL","18","Imagery Providers","GET /api/v1/imagery/providers",err,[]))
else:
    providers = r.get("providers", r if isinstance(r,list) else [])
    details = []
    for p in (providers if isinstance(providers,list) else []):
        details.append(f"  {p.get('connector_id','?'):25}  collections={p.get('collections',[])}  endpoint={str(p.get('stac_url','?'))[:55]}")
    rows.append(("OK","18","Imagery Providers","GET /api/v1/imagery/providers",f"total={len(providers) if isinstance(providers,list) else 0}",details))

# 19 - IMAGERY COMPARE
r_s, _ = xpost("/api/v1/imagery/search", {"geometry":POLY,"start_time":T1,"end_time":T2,"max_cloud_cover":30})
scenes = r_s.get("items",[]) if r_s else []
if len(scenes) >= 2:
    r, err = xpost("/api/v1/imagery/compare", {"before_event_id": scenes[-1].get("event_id"), "after_event_id": scenes[0].get("event_id")})
    if err:
        rows.append(("FAIL","19","Imagery Compare","POST /api/v1/imagery/compare",err,[]))
    else:
        details = [f"  {k}: {v}" for k,v in (r.items() if isinstance(r,dict) else []) if not isinstance(v,(dict,list))]
        rows.append(("OK","19","Imagery Compare (oldest vs newest scene)","POST /api/v1/imagery/compare",f"before={scenes[-1].get('event_time','')[:10]}  after={scenes[0].get('event_time','')[:10]}",details))
else:
    rows.append(("EMPTY","19","Imagery Compare","POST /api/v1/imagery/compare","Need >= 2 scenes",[]))

# 20 - PLAYBACK
r, err = xpost("/api/v1/playback/query", {"geometry":POLY,"start_time":T_LIVE1,"end_time":T_LIVE2,"page_size":10})
total = (r.get("total") or len(r.get("events",[]))) if r else 0
rows.append(("OK" if total else "EMPTY","20","Playback Query","POST /api/v1/playback/query",f"total={total}",["  Event store empty — set APP_MODE=demo or run Celery worker"] if not total else []))

# PRINT REPORT
ICONS = {"OK":"OK  ","FAIL":"FAIL","EMPTY":"MPTY"}
print()
print("="*108)
print("   ARGUS — Strait of Hormuz External Data Source Report")
print("   AOI : bbox 55-58 E  25-28 N  |  centre lon=56.5  lat=26.5")
print(f"   Win : {T1}  ->  {T2}")
print(f"   Srv : {BASE}")
print(f"   Run : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("="*108)
print()
ok=fail=empty=0
for status,num,name,ep,result,details in rows:
    if status=="OK": ok+=1; icon="✅"
    elif status=="FAIL": fail+=1; icon="❌"
    else: empty+=1; icon="⚠️ "
    print(f"{icon} [{ICONS[status]}] {num}. {name}")
    print(f"         endpoint : {ep}")
    print(f"         result   : {result}")
    for d in details: print(f"                  {d}")
    print()
print("-"*108)
print(f"  SUMMARY  ✅ OK={ok}   ⚠️  EMPTY={empty}   ❌ FAIL={fail}   Total={len(rows)}")
print("-"*108)
print()
print("ROOT CAUSES FOR EMPTY:")
print("  APP_MODE=staging — in-memory event store cleared at startup (demo seeder disabled).")
print("  Live connectors (AIS, OpenSky, USGS, NGA, GDELT) need Celery worker to populate store.")
print("  AISSTREAM_API_KEY not set — dark-ships and AIS ship_position will remain empty.")
print("  ACLED_EMAIL + ACLED_PASSWORD not set — strike events use synthetic stub only.")
