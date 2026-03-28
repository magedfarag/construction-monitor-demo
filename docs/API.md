# API Reference — Construction Activity Monitor v2.0

**Base URL**: `http://localhost:8000` (development)  
**Version**: 2.0.0  
**Authentication**: Optional API key via `X-API-Key` header (required if `API_KEY_REQUIRED=true`)

---

## **Health & Status**

### `GET /api/health`
Check API and dependency health (no auth required).

**Request**:
```bash
curl http://localhost:8000/api/health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2026-03-28T10:15:00Z",
  "dependencies": {
    "redis": "healthy",
    "sentinel2_provider": "healthy",
    "landsat_provider": "unhealthy",
    "demo_provider": "healthy"
  }
}
```

**Response** (503 Service Unavailable):
```json
{
  "status": "degraded",
  "timestamp": "2026-03-28T10:15:00Z",
  "dependencies": {
    "redis": "unhealthy",
    "sentinel2_provider": "unavailable",
    "landsat_provider": "healthy",
    "demo_provider": "healthy"
  }
}
```

---

### `GET /api/config`
Retrieve application configuration (no auth required).

**Request**:
```bash
curl http://localhost:8000/api/config
```

**Response** (200 OK):
```json
{
  "app_mode": "live",
  "cache_enabled": true,
  "async_enabled": true,
  "async_area_threshold_km2": 50.0,
  "supported_providers": ["sentinel2", "landsat", "demo"],
  "available_providers": ["landsat", "demo"],
  "max_area_km2": 100.0,
  "min_area_km2": 0.01,
  "max_date_range_days": 365,
  "rate_limits": {
    "analyze": "5 per 1 minute",
    "search": "10 per 1 minute",
    "jobs": "20 per 1 minute"
  }
}
```

---

### `GET /api/providers`
List available satellite providers and their current status (no auth required).

**Request**:
```bash
curl http://localhost:8000/api/providers
```

**Response** (200 OK):
```json
{
  "providers": [
    {
      "id": "sentinel2",
      "name": "Sentinel-2 (Copernicus)",
      "available": false,
      "status": "OPEN",
      "last_failure": "2026-03-28T09:45:00Z",
      "resolution_m": 10,
      "latency_ms": 1250
    },
    {
      "id": "landsat",
      "name": "Landsat 8/9 (USGS)",
      "available": true,
      "status": "CLOSED",
      "last_success": "2026-03-28T10:10:00Z",
      "resolution_m": 30,
      "latency_ms": 850
    },
    {
      "id": "demo",
      "name": "Demo Provider (Mock)",
      "available": true,
      "status": "CLOSED",
      "last_success": "2026-03-28T10:13:00Z",
      "resolution_m": 10,
      "latency_ms": 5
    }
  ]
}
```

---

### `GET /api/credits`
Check credit/quota usage across providers (no auth required).

**Request**:
```bash
curl http://localhost:8000/api/credits
```

**Response** (200 OK):
```json
{
  "organizations": [
    {
      "provider": "sentinel2",
      "organization": "Copernicus",
      "requests_this_month": 1250,
      "quota_monthly": 50000,
      "utilization_percent": 2.5
    },
    {
      "provider": "landsat",
      "organization": "USGS",
      "requests_this_month": 8900,
      "quota_monthly": 999999,
      "utilization_percent": 0.89
    }
  ]
}
```

---

## **Analysis**

### `POST /api/analyze`
Analyze an area of interest (AOI) for construction changes between two dates (auth required, rate-limited: 5/min).

**Request Headers**:
```
X-API-Key: your-api-key  (if API_KEY_REQUIRED=true)
Content-Type: application/json
```

**Request Body**:
```json
{
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [46.655, 24.710],
        [46.670, 24.710],
        [46.670, 24.720],
        [46.655, 24.720],
        [46.655, 24.710]
      ]
    ]
  },
  "start_date": "2026-02-27",
  "end_date": "2026-03-28",
  "provider": "auto",
  "confidence_threshold": 50,
  "async_execution": false
}
```

**Request Fields**:
- `geometry` (required): GeoJSON Polygon or MultiPolygon (must be valid geography)
- `start_date` (required): ISO 8601 date string (YYYY-MM-DD)
- `end_date` (required): ISO 8601 date string (YYYY-MM-DD)
- `provider` (optional, default: "auto"): "sentinel2" | "landsat" | "demo" | "auto"
- `confidence_threshold` (optional, default: 50): 0–100, filter changes below threshold
- `async_execution` (optional, default: false): true to dispatch to background worker

**Response** (200 OK, sync):
```json
{
  "analysis_id": "ana-20260328-abc123",
  "status": "completed",
  "provider": "landsat",
  "is_demo": false,
  "area_km2": 1.234,
  "changes": [
    {
      "change_id": "chg-001",
      "change_type": "Excavation",
      "confidence": 87,
      "geometry": {
        "type": "Polygon",
        "coordinates": [[...]]
      },
      "centroid": { "lng": 46.6625, "lat": 24.715 },
      "rationale": [
        "NDVI decreased by 0.35 (vegetation loss)",
        "Cluster area: 5.2 hectares",
        "Sharp boundaries (machinery signature)"
      ]
    }
  ],
  "statistics": {
    "total_changes": 1,
    "average_confidence": 87,
    "min_confidence": 87,
    "max_confidence": 87,
    "total_affected_area_km2": 0.052
  },
  "scenes": {
    "before": {
      "scene_id": "S2A_20260227T053651_N0510",
      "date": "2026-02-27",
      "satellite": "Sentinel-2A",
      "cloud_percent": 12.5
    },
    "after": {
      "scene_id": "LC09_L2SP_161045_20260328_20260328_02_T1",
      "date": "2026-03-28",
      "satellite": "Landsat 9",
      "cloud_percent": 8.3
    }
  },
  "warnings": [],
  "execution_time_ms": 2350
}
```

**Response** (202 Accepted, async):
```json
{
  "job_id": "job-20260328-def456",
  "status": "pending",
  "analysis_id": null,
  "timestamp": "2026-03-28T10:15:00Z",
  "poll_url": "/api/jobs/job-20260328-def456"
}
```

**Error Responses**:

- **400 Bad Request**: Invalid geometry or date range
  ```json
  {
    "error": "invalid_request",
    "message": "end_date must be after start_date",
    "details": { "end_date": "2026-03-28", "start_date": "2026-03-28" }
  }
  ```

- **402 Payment Required**: Area exceeds max bounds
  ```json
  {
    "error": "area_exceeds_limit",
    "message": "AOI area (125.5 km²) exceeds maximum (100 km²)",
    "area_km2": 125.5,
    "max_area_km2": 100.0
  }
  ```

- **429 Too Many Requests**: Rate limit exceeded
  ```json
  {
    "error": "rate_limited",
    "message": "5 requests per 1 minute exceeded",
    "retry_after": 45
  }
  ```

- **503 Service Unavailable**: All providers down
  ```json
  {
    "error": "no_providers_available",
    "message": "No imagery providers available",
    "suggestions": ["Check network connectivity", "Try again in 1 minute"]
  }
  ```

---

### `POST /api/search`
Search for satellite imagery scenes without performing change detection (auth required, rate-limited: 10/min).

**Request Headers**:
```
X-API-Key: your-api-key
Content-Type: application/json
```

**Request Body**:
```json
{
  "geometry": {
    "type": "Polygon",
    "coordinates": [[...]]
  },
  "start_date": "2026-02-27",
  "end_date": "2026-03-28",
  "provider": "auto",
  "cloud_threshold": 20,
  "max_results": 10
}
```

**Response** (200 OK):
```json
{
  "provider": "landsat",
  "geometry_bounds": { "north": 24.720, "south": 24.710, "east": 46.670, "west": 46.655 },
  "scenes": [
    {
      "scene_id": "LC09_L2SP_161045_20260328_20260328_02_T1",
      "date": "2026-03-28",
      "satellite": "Landsat 9",
      "cloud_percent": 8.3,
      "platform": "Landsat",
      "resolution_m": 30,
      "instrument": "OLI-2",
      "acquisition_time": "2026-03-28T05:35:00Z"
    },
    {
      "scene_id": "LC08_L2SP_160045_20260320_20260328_02_T1",
      "date": "2026-03-20",
      "satellite": "Landsat 8",
      "cloud_percent": 15.2,
      "platform": "Landsat",
      "resolution_m": 30,
      "instrument": "OLI",
      "acquisition_time": "2026-03-20T05:35:00Z"
    }
  ],
  "scene_count": 2,
  "search_time_ms": 1240
}
```

---

## **Async Jobs**

### `GET /api/jobs/{job_id}`
Check the status and result of an async analysis job (auth required).

**Request**:
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/jobs/job-20260328-def456
```

**Response** (200 OK, pending):
```json
{
  "job_id": "job-20260328-def456",
  "status": "running",
  "progress_percent": 65,
  "created_at": "2026-03-28T10:15:00Z",
  "started_at": "2026-03-28T10:15:05Z",
  "updated_at": "2026-03-28T10:15:25Z",
  "result": null,
  "error": null,
  "cancel_url": "/api/jobs/job-20260328-def456/cancel"
}
```

**Response** (200 OK, completed):
```json
{
  "job_id": "job-20260328-def456",
  "status": "completed",
  "progress_percent": 100,
  "created_at": "2026-03-28T10:15:00Z",
  "started_at": "2026-03-28T10:15:05Z",
  "completed_at": "2026-03-28T10:17:30Z",
  "result": {
    "analysis_id": "ana-20260328-def456",
    "changes": [...],
    "statistics": {...}
  },
  "error": null
}
```

**Response** (200 OK, failed):
```json
{
  "job_id": "job-20260328-def456",
  "status": "failed",
  "progress_percent": 0,
  "created_at": "2026-03-28T10:15:00Z",
  "started_at": "2026-03-28T10:15:05Z",
  "failed_at": "2026-03-28T10:15:35Z",
  "result": null,
  "error": {
    "code": "provider_unavailable",
    "message": "All imagery providers unavailable"
  }
}
```

**Error Responses**:

- **404 Not Found**: Job does not exist
  ```json
  {
    "error": "job_not_found",
    "job_id": "job-20260328-unknown"
  }
  ```

---

### `DELETE /api/jobs/{job_id}/cancel`
Cancel an in-progress async analysis job (auth required).

**Request**:
```bash
curl -X DELETE -H "X-API-Key: your-api-key" \
  http://localhost:8000/api/jobs/job-20260328-def456/cancel
```

**Response** (200 OK):
```json
{
  "job_id": "job-20260328-def456",
  "status": "cancelled",
  "message": "Job cancelled successfully",
  "cancelled_at": "2026-03-28T10:16:00Z"
}
```

**Error Responses**:

- **409 Conflict**: Job already completed/failed
  ```json
  {
    "error": "job_not_cancellable",
    "message": "Job is already completed (status: completed)"
  }
  ```

---

## **Error Format**

All errors follow this structure:

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "additional context"
  }
}
```

**Common Error Codes**:
- `invalid_request`: Malformed request
- `unauthorized`: Missing/invalid API key
- `rate_limited`: Rate limit exceeded
- `area_exceeds_limit`: AOI too large
- `date_range_exceeded`: Date range > 365 days
- `no_providers_available`: All providers down
- `provider_unavailable`: Specific provider unavailable
- `unsupported_geometry`: Geometry type not supported (only Polygon/MultiPolygon)
- `internal_error`: Unexpected server error

---

## **Rate Limits**

Rate limits are per API key (or per IP if anonymous):

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /api/analyze` | 5 | 1 minute |
| `POST /api/search` | 10 | 1 minute |
| `GET/DELETE /api/jobs/*` | 20 | 1 minute |

**Rate Limit Headers**:
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 2
X-RateLimit-Reset: 1711607700
```

When limit exceeded: **429 Too Many Requests** with `Retry-After` header.

---

## **Authentication**

### API Key
If `API_KEY_REQUIRED=true`, include API key in all protected endpoints:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/analyze
```

### CORS
Allowed origins configured via `ALLOWED_ORIGINS` env (default: `http://localhost:3000`).

---

## **Examples**

### Example 1: Analyze AOI (Sync)
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[46.655, 24.710], [46.670, 24.710], [46.670, 24.720], [46.655, 24.720], [46.655, 24.710]]]
    },
    "start_date": "2026-02-27",
    "end_date": "2026-03-28"
  }'
```

### Example 2: Analyze AOI (Async)
```bash
# Start job
JOB_ID=$(curl -s -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"geometry": {...}, "async_execution": true}' \
  | jq -r '.job_id')

# Poll status
curl http://localhost:8000/api/jobs/$JOB_ID

# Cancel if needed
curl -X DELETE http://localhost:8000/api/jobs/$JOB_ID/cancel
```

### Example 3: Search Imagery
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "geometry": {...},
    "start_date": "2026-02-27",
    "end_date": "2026-03-28",
    "cloud_threshold": 20
  }'
```

---

## **Changelog**

### v2.0.0 (2026-03-28)
- Added async job management (`/api/jobs/*`)
- Added provider registry endpoint (`/api/providers`)
- Added credits/quota endpoint (`/api/credits`)
- Rate limiting on analyze (5/min), search (10/min), jobs (20/min)
- Improved error responses with structured codes

### v1.0.0 (2026-01-15)
- Initial release: sync analyze + health check
