# Environment Reference

`.env.example` is the canonical exhaustive template for this project.

This page groups the most important variables by concern and highlights the defaults that come directly from `app/config.py`.

## Core Runtime

| Variable | Default | Notes |
|---|---|---|
| `APP_MODE` | `staging` | Valid values: `demo`, `staging`, `production` |
| `LOG_LEVEL` | `INFO` | Uppercased on load |
| `LOG_FORMAT` | `json` | `json` or `text` |
| `ALLOWED_ORIGINS` | localhost set | Parsed as a comma-separated list for CORS |

## Authentication And RBAC

| Variable | Default | Notes |
|---|---|---|
| `API_KEY` | empty | If empty outside demo mode, auth is bypassed for development |
| `JWT_SECRET` | empty | Falls back to `API_KEY` for signed role tokens if unset |
| `ADMIN_API_KEY` | empty | Raw admin role key |
| `OPERATOR_API_KEY` | empty | Raw operator role key |
| `ANALYST_API_KEY` | empty | Raw analyst role key |

Frontend note:

- The Vite frontend stores the key in local storage under `geoint_api_key`.
- When set, the client sends it as `Authorization: Bearer <key>`.
- During local dev, `frontend/vite.config.ts` can inject `API_KEY` into the proxy so it stays out of the browser bundle.

## Infrastructure

| Variable | Default | Notes |
|---|---|---|
| `REDIS_URL` | empty | Required for Celery, async jobs, and distributed cache/state |
| `DATABASE_URL` | empty | Enables optional SQLAlchemy/Postgres initialization |
| `CELERY_BROKER_URL` | empty | Falls back to `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | empty | Falls back to `REDIS_URL` |
| `OBJECT_STORAGE_ENDPOINT` | empty | MinIO/S3-compatible endpoint |
| `OBJECT_STORAGE_BUCKET` | `geoint-raw` | Default object bucket name |
| `OBJECT_STORAGE_ACCESS_KEY` | empty | Required for object storage access |
| `OBJECT_STORAGE_SECRET_KEY` | empty | Required for object storage access |

## Analysis, Cache, And Resilience

| Variable | Default | Notes |
|---|---|---|
| `CACHE_TTL_SECONDS` | `3600` | General analysis cache TTL |
| `CACHE_MAX_ENTRIES` | `256` | In-memory fallback cache size |
| `HTTP_TIMEOUT_SECONDS` | `30` | Outbound provider request timeout |
| `HTTP_MAX_RETRIES` | `3` | Outbound retry count |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Failures before opening a provider circuit |
| `CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | `60` | Seconds before half-open probe |
| `DEFAULT_CLOUD_THRESHOLD` | `20` | Default max cloud cover for imagery search |
| `ASYNC_AREA_THRESHOLD_KM2` | `25` | AOIs larger than this auto-promote to async |
| `RASTER_TEMP_DIR` | unset | Optional override for raster temp storage |

## Primary Imagery Providers

| Variable Group | Notes |
|---|---|
| `SENTINEL2_*` | CDSE credentials and endpoint overrides for live Sentinel-2 |
| `LANDSAT_*` | Landsat STAC is public for search; credentials are optional |
| `MAXAR_*` | Commercial imagery, V1 provider only |
| `PLANET_*` | Commercial imagery, V1 provider only |
| `EARTH_SEARCH_STAC_URL` | Element84 public STAC endpoint |
| `PLANETARY_COMPUTER_*` | Microsoft Planetary Computer endpoint and optional token |

## Operational Connectors

| Variable Group | Notes |
|---|---|
| `AISSTREAM_*` | Maritime AIS connector |
| `OPENSKY_*` | Aviation connector |
| `GDELT_BASE_URL` | Contextual news/events |
| `ACLED_*` | Conflict event connector, only registered when credentials exist |
| `NGA_MSI_*` | Maritime safety warnings |
| `NASA_FIRMS_*` | Thermal anomaly/fire events |
| `USGS_EARTHQUAKE_*` | Public earthquake feed |
| `NASA_EONET_*` | Public natural-event feed |
| `OPEN_METEO_*` | Weather context feed |
| `NOAA_SWPC_*` | Space weather feed |
| `OPENAQ_*` | Air quality observations |
| `OSM_OVERPASS_URL` | OSM military-feature connector |

## Tuning And Governance

| Variable | Default | Notes |
|---|---|---|
| `EVENTS_DENSITY_THRESHOLD` | `500` | Server-side density reduction trigger |
| `EVENTS_DENSITY_MAX_RESULTS` | `200` | Max results after density reduction |
| `RETENTION_ENFORCEMENT_ENABLED` | `true` | Enables Celery beat telemetry retention task |
| `RETENTION_ENFORCEMENT_INTERVAL_SECONDS` | `3600` | Telemetry retention cadence |
| `MAX_BRIEFINGS_PER_HOUR_PER_USER` | `10` | Cost guardrail |
| `MAX_EVIDENCE_PACKS_PER_HOUR_PER_USER` | `20` | Cost guardrail |
| `MAX_EXPORT_SIZE_MB` | `50` | Export size cap |

## Frontend Development

| Variable | Default | Notes |
|---|---|---|
| `ARGUS_BACKEND_TARGET` | `http://127.0.0.1:8000` | Vite proxy backend target |
| `API_KEY` | inherited from env | Optional proxy-injected auth header for local dev |

For the full variable list and inline commentary, use [../../.env.example](../../.env.example).
