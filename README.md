# Construction Activity Monitor Demo

## Purpose
This package is a runnable demo application for selecting an area on a map and simulating a 30-day construction change analysis workflow.

It is designed to demonstrate:
- AOI selection on an interactive map
- validation of minimum and maximum area constraints
- an analysis API contract
- a results UI with construction change cards, timestamps, coordinates, confidence scores, and before/after thumbnails
- clear extension points for real Sentinel-2 and Landsat integrations

## What is included
- `backend/app/main.py`: FastAPI application that serves both the API and the static frontend
- `backend/app/providers.py`: adapter stubs for real imagery providers
- `backend/app/static/`: HTML, CSS, JavaScript, and sample imagery assets
- `docs/API.md`: endpoint documentation and data flow
- `docs/ARCHITECTURE.md`: architecture notes, provider mapping, and limitations

## Demo behavior
The shipped demo is intentionally deterministic. It returns three curated construction scenarios inside the requested area if their timestamps fall in the requested date range:
1. Site clearing / earthwork
2. Foundation work
3. Roofing / enclosure

This keeps the package runnable without external credentials while still matching the requested UX and API shape.

## Quick start
### 1) Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Run the demo
```bash
uvicorn backend.app.main:app --reload
```

Then open:
- `http://127.0.0.1:8000/`
- Swagger UI: `http://127.0.0.1:8000/docs`

## How to use
1. Draw a polygon, rectangle, or circle on the map.
2. Or enter a bounding box and click **Draw Bounding Box**.
3. Keep the area between **0.01 km²** and **100 km²**.
4. Select the provider mode and date range.
5. Click **Analyze Last Month**.
6. Review returned detections and use the timeline slider to filter by recency.

## Real provider upgrade path
The demo ships with provider placeholders only. To convert it from curated samples to real imagery processing:
- Implement scene search in `Sentinel2StacProvider`
- Implement scene search in `LandsatStacProvider`
- Add download, cloud filtering, compositing, and change detection stages
- Persist jobs and outputs if you want asynchronous processing

## Limitations
- The delivered package is a **demo**, not a production detector.
- The current backend does **not** fetch live Sentinel, Landsat, Planet, or Maxar imagery.
- The sample imagery is illustrative and intended for UX demonstration only.
- Area calculation is approximate but sufficient for a demo.
- Circle selections are converted to polygons client-side before submission.

## Suggested next steps
- Add STAC search + authentication for Sentinel and Landsat
- Replace curated detections with a real inference pipeline
- Introduce a job queue for long-running analysis
- Store result artifacts in object storage
- Add parcel overlays, permit feeds, and inspection records for fusion scoring

## References used for architecture choices
- Copernicus Data Space Ecosystem exposes multiple APIs including STAC and other HTTP endpoints for interacting with Sentinel data. See `docs/ARCHITECTURE.md`.
- USGS exposes Landsat access through REST/JSON APIs and STAC-compatible catalog services. See `docs/ARCHITECTURE.md`.
- Leaflet.draw supports polygon, rectangle, and circle drawing in browser clients. See `docs/ARCHITECTURE.md`.
