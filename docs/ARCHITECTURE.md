# Architecture Notes

## 1. Demo architecture
The demo uses a single FastAPI service that:
- serves the static frontend
- validates geometry and date ranges
- exposes a synchronous `/api/analyze` endpoint
- returns curated results shaped like a real imagery-change API

## 2. Frontend flow
1. User draws a polygon, rectangle, or circle.
2. Browser converts circles into polygons for GeoJSON transport.
3. Browser computes AOI area with Turf.js.
4. Browser posts the geometry and dates to `/api/analyze`.
5. Browser renders returned detections and applies timeline filtering client-side.

## 3. Production-grade extension path
A realistic implementation would replace the sample result generator with this pipeline:
1. AOI validation and buffering
2. STAC or provider search for scenes in the last 30 days
3. cloud and quality filtering
4. best-scene selection or temporal compositing
5. co-registration and normalization
6. change detection model or rule engine
7. false-positive suppression for cloud shadow, seasonal vegetation, and sensor artifacts
8. scoring and packaging of results

## 4. Source and interface choices
### Sentinel-2
Copernicus Data Space documentation states that the platform provides multiple APIs for interacting with Sentinel data, including STAC and other HTTP-based interfaces. The Sentinel-2 collection page states that the STAC-compliant catalog can be used to discover and search Earth observation data. citeturn371209search4turn371209search8turn371209search12

### Landsat
USGS states that its Machine-to-Machine API is a RESTful JSON API and that Landsat data access is also available through STAC-oriented services such as LandsatLook STAC. citeturn371209search1turn371209search5turn371209search17

### Frontend mapping and drawing
Leaflet.draw documentation shows support for drawing polygons, rectangles, and circles, which matches the requested interaction model. citeturn371209search2turn371209search6

### Backend API framework
FastAPI provides typed request/response handling and documented support for response models and background tasks, which makes it suitable for a future asynchronous job architecture. citeturn371209search3turn371209search11turn371209search15

## 5. Trade-offs
### Near-real-time monitoring
- Sentinel-2 is free and frequent, but 10 m resolution can miss small site details.
- Landsat extends historical coverage but is coarser and less useful for small urban parcels.
- Commercial providers improve revisit and spatial detail, but they are not free.

### Historical analysis
- Landsat is stronger for longer baselines.
- Sentinel-2 is stronger for recent-period detail.
- Best practice is usually fusion rather than exclusive dependence on one source.

## 6. Limitations for this demo
- No live provider credentials or downloads are included.
- No production-grade cloud mask, BRDF normalization, or orthorectification workflow is implemented.
- No queue, object storage, or persistent database is included.
- No legal review is bundled for commercial deployment; provider-specific terms still need review.
