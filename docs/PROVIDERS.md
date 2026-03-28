# Provider Setup Guide

The application supports three providers. Priority order (when `provider=auto`):
`sentinel2 → landsat → demo`

---

## 1. Demo Provider

**Always available.** No credentials required.

Returns three deterministic construction scenarios:
1. Site clearing / earthwork
2. Foundation work
3. Roofing / enclosure

The demo provider is the final fallback in the chain. Set `APP_MODE=demo` to
force demo mode regardless of what credentials are present.

---

## 2. Sentinel-2 (Copernicus Data Space Ecosystem)

**Resolution:** 10 m  
**Revisit:** ~5 days  
**Auth:** OAuth2 `client_credentials`

### 2.1 Register

1. Go to https://dataspace.copernicus.eu
2. Click **Register** and create a free account
3. Verify your email address
4. Log in to the dashboard
5. Navigate to **User settings → OAuth clients**
6. Create a new client with `client_credentials` grant
7. Note your `Client ID` and `Client Secret`

### 2.2 Configure

```env
SENTINEL2_CLIENT_ID=your-client-id
SENTINEL2_CLIENT_SECRET=your-client-secret
```

### 2.3 How it works

`Sentinel2Provider._get_token()` exchanges credentials for a bearer token at:

```
POST https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token
  grant_type=client_credentials
  client_id=…
  client_secret=…
```

Tokens are cached with a 30-second buffer before expiry.

Then `search_imagery()` POSTs to the STAC search endpoint:

```
POST https://catalogue.dataspace.copernicus.eu/stac/v1/search
  {
    "collections": ["SENTINEL-2"],
    "intersects": <GeoJSON geometry>,
    "datetime": "2026-02-26T00:00:00Z/2026-03-28T23:59:59Z",
    "limit": 10,
    "query": {"eo:cloud_cover": {"lte": 20}}
  }
```

### 2.4 COG asset access

Change detection reads scene assets as Cloud-Optimised GeoTIFFs streamed via HTTPS.
The bearer token is passed as `GDAL_HTTP_BEARER` via `rasterio.Env()`.

### 2.5 Troubleshooting

| Error | Likely cause |
|---|---|
| `401 Unauthorized` on token endpoint | Wrong `CLIENT_ID` or `CLIENT_SECRET` |
| `Token request failed` | Copernicus outage or wrong `SENTINEL2_TOKEN_URL` |
| Empty scene list | AOI outside Europe/Africa coverage, or cloud threshold too strict |
| `Circuit breaker OPEN` | 5+ consecutive failures; waits 60 s before retry |

---

## 3. Landsat (USGS LandsatLook STAC)

**Resolution:** 30 m  
**Revisit:** ~16 days  
**Auth:** None required for search

### 3.1 No setup required for scene search

Landsat STAC search is publicly accessible. The `LandsatProvider` works
out-of-the-box with no credentials.

### 3.2 Optional — USGS ERS credentials for M2M bulk download

If you need to download full-resolution Landsat scenes via the M2M API:

1. Register at https://ers.cr.usgs.gov
2. Log in and request M2M access (may require approval)
3. Set in `.env`:

```env
LANDSAT_USERNAME=your-ers-username
LANDSAT_PASSWORD=your-ers-password
```

> The current `LandsatProvider` implementation does not use M2M. These fields
> are reserved for a future bulk-download extension.

### 3.3 How it works

`search_imagery()` POSTs to:

```
POST https://landsatlook.usgs.gov/stac-server/search
  {
    "collections": ["landsat-c2l2-sr"],
    "intersects": <GeoJSON geometry>,
    "datetime": "…/…",
    "limit": 10,
    "query": {"eo:cloud_cover": {"lte": 20}},
    "sortby": [{"field": "datetime", "direction": "desc"}]
  }
```

### 3.4 Note on resolution

At 30 m resolution, Landsat is most useful for larger developments (> 5 km²).
For small urban parcels, Sentinel-2 (10 m) provides significantly better detail.
The system always selects the best available provider for the requested AOI.

---

## 4. Registering a custom provider

1. Create `backend/app/providers/my_provider.py`
2. Extend `SatelliteProvider` (see `base.py`)
3. Implement all 6 abstract methods: `validate_credentials`, `search_imagery`,
   `fetch_scene_metadata`, `healthcheck`, `get_quota_status`, `download_assets`
4. Register in `main.py` lifespan:

```python
from backend.app.providers.my_provider import MyProvider
if settings.my_provider_is_configured():
    registry.register(MyProvider(settings))
```

5. Add any new env vars to `config.py` and `.env.example`
