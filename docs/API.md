# API Documentation

## `GET /api/health`
Returns a simple service health payload.

### Example response
```json
{
  "status": "ok",
  "mode": "demo"
}
```

## `GET /api/config`
Returns client configuration and constraints.

### Example response
```json
{
  "today": "2026-03-28",
  "min_area_km2": 0.01,
  "max_area_km2": 100,
  "supported_providers": ["demo-fusion", "sentinel-2-stac", "landsat-stac"],
  "max_lookback_days": 30
}
```

## `POST /api/analyze`
Receives the selected geometry and returns a construction activity analysis response.

### Request body
```json
{
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [46.65, 24.70],
        [46.70, 24.70],
        [46.70, 24.74],
        [46.65, 24.74],
        [46.65, 24.70]
      ]
    ]
  },
  "start_date": "2026-02-26",
  "end_date": "2026-03-28",
  "provider": "demo-fusion",
  "area_km2": 19.857
}
```

### Response fields
- `analysis_id`: unique analysis identifier
- `requested_area_km2`: validated AOI size
- `provider`: selected provider or adapter target
- `request_bounds`: `[minLng, minLat, maxLng, maxLat]`
- `imagery_window`: request time window
- `warnings`: implementation notes and caveats
- `changes[]`: each detected change event
- `stats`: aggregate counts and confidence summaries

### Change object
```json
{
  "change_id": "chg-foundation-2",
  "detected_at": "2026-03-16T12:30:00",
  "change_type": "Foundation work",
  "confidence": 91.0,
  "center": {"lng": 46.675, "lat": 24.721},
  "bbox": [46.671, 24.718, 46.679, 24.724],
  "provider": "demo-fusion",
  "summary": "New slab-like reflective surfaces and regular footprint suggest foundation installation.",
  "rationale": [
    "Rectilinear footprint emerged after excavation stage",
    "High reflectance and consistent edges resemble poured concrete",
    "Context is spatially consistent with active construction rather than demolition"
  ],
  "before_image": "/static/assets/foundation_before.png",
  "after_image": "/static/assets/foundation_after.png",
  "thumbnail": "/static/assets/foundation_after.png"
}
```

## Validation rules
- Geometry must be a polygon or multipolygon.
- Effective area must be between **0.01 km²** and **100 km²**.
- Date range must stay inside the most recent **30 days** of the demo dataset.
- Start date must be before or equal to end date.
