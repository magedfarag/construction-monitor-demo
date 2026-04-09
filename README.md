# ARGUS

ARGUS is a production-oriented FastAPI + React intelligence platform for AOI-based monitoring across imagery, telemetry, contextual events, and analyst workflows. The current codebase combines a V1 change-detection pipeline with a larger V2 operational intelligence API surface, plus Celery-backed background processing, RBAC, audit logging, and connector health monitoring.

## Stack

- Backend: Python 3.12, FastAPI, Pydantic v2, Celery, Redis, SQLAlchemy/Alembic, rasterio
- Frontend: React 18, TypeScript, Vite, MapLibre GL JS, deck.gl, TanStack Query
- Data sources: Sentinel-2, Landsat, Earth Search, Planetary Computer, GDELT, OpenSky, AISStream, USGS, NASA, NOAA, OpenAQ, NGA MSI, OSM

## Quick Start

### Backend only

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/health`

### Local analyst workflow

```powershell
.\start_infra.ps1
.\run_api.ps1
.\run_worker.ps1
# optional
.\run_beat.ps1

cd frontend
npm install
npm run dev
```

Open:

- React UI: `http://localhost:5173`
- Backend API docs: `http://localhost:8000/docs`

### Full backend stack with Docker Compose

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The Compose file starts the backend services and infrastructure. It does not start a Vite frontend service, so run the React app separately if you need the browser UI.

## Runtime Modes

| `APP_MODE` | Behavior |
|---|---|
| `demo` | Demo provider only, seeded synthetic data, auth bypass |
| `staging` | Real providers when available with demo fallback |
| `production` | Real providers only, no demo fallback |

If `API_KEY` is unset outside demo mode, the app runs in an insecure developer-friendly bypass mode. See [docs/API.md](docs/API.md) and [docs/reference/environment.md](docs/reference/environment.md).

## Documentation

Start with [docs/README.md](docs/README.md). The key current docs are:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/API.md](docs/API.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md)
- [docs/getting-started/local-development.md](docs/getting-started/local-development.md)
- [docs/reference/environment.md](docs/reference/environment.md)
- [docs/testing/strategy.md](docs/testing/strategy.md)

Delivery reports, handover material, and historical validation snapshots live under [docs/delivery](docs/delivery/README.md). Longer-range plans and transformation papers live under [docs/roadmaps](docs/roadmaps/README.md).


