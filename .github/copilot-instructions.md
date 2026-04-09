# ARGUS — Multi-Domain Surveillance Intelligence — Guidelines

## Project Structure

```
argus-intel/
├── .github/                      # GitHub configuration, workflows, instructions, skills
├── .vscode/                      # VSCode workspace settings
├── alembic/                      # Database migration scripts (versions/)
├── app/                         # Legacy FastAPI backend (being phased out)
│   ├── cache/                   # Query caching layer
│   ├── models/                  # Pydantic request/response models
│   ├── providers/               # Satellite imagery provider stubs
│   ├── resilience/              # Circuit breakers, rate limiters, retry logic
│   ├── routers/                 # API route handlers
│   ├── services/                # Business logic services
│   └── workers/                 # Celery background workers
├── docs/                        # All project documentation
│   ├── archive/                 # Archived/historical docs
│   ├── delivery/                # Delivery and release documentation
│   ├── domain/                  # Domain-specific technical docs
│   ├── geoint-platform-architecture-and-plan/  # Architecture decisions, ADRs, schemas
│   ├── getting-started/         # Setup and onboarding guides
│   ├── images/                  # Screenshots, diagrams, assets
│   ├── reports/                 # Status reports, verification outputs
│   ├── roadmaps/                # Feature roadmaps and planning
│   ├── testing/                 # Testing strategies and guides
│   ├── v2/                      # V2 platform documentation
│   ├── worldview-platform-plan/ # Multi-phase platform plan
│   └── worldview-transformation-plan/  # Transformation roadmap
├── frontend/                    # React + TypeScript operational UI
│   ├── e2e/                     # Playwright end-to-end tests
│   ├── public/                  # Static assets
│   ├── src/                     # React application source
│   │   ├── api/                 # API client and types
│   │   ├── components/          # React components
│   │   ├── config/              # Frontend configuration
│   │   ├── hooks/               # React custom hooks
│   │   ├── lib/                 # Utility libraries
│   │   ├── services/            # Frontend services
│   │   └── styles/              # Global styles
│   └── playwright-report/       # Test execution reports (gitignored)
├── scripts/                     # Operational and development scripts
│   ├── data/                    # Reference data files (ne_10m_land.geojson, etc.)
│   ├── debug_stac.py            # STAC API debugging tool
│   ├── generate_status_report.py  # Infrastructure status reporting
│   ├── organize_project.py      # File organization utility
│   ├── status_check.py          # Service health checks
│   ├── test_connectivity.py     # API connectivity testing
│   ├── test_playback.py         # Playback service validation
│   ├── validate_ships.py        # Ship data validation
│   ├── verify_data_sources.py   # Data source verification
│   ├── verify_ships_no_land.py  # Geospatial validation
│   └── write_docs.py            # Documentation generation
├── src/                         # Core V2 platform (canonical models, connectors, services)
│   ├── api/                     # V2 FastAPI endpoints
│   ├── connectors/              # External data source connectors
│   ├── models/                  # Canonical event models and domain entities
│   ├── normalization/           # Data normalization pipelines
│   ├── services/                # Core business logic
│   └── storage/                 # Database models and persistence
├── tests/                       # Test suite
│   ├── fixtures/                # Test data fixtures (JSON, images, etc.)
│   ├── integration/             # Integration tests
│   └── unit/                    # Unit tests
├── alembic.ini                  # Alembic configuration
├── docker-compose.yml           # Local development infrastructure
├── docker-compose.infra.yml     # Infrastructure-only compose
├── Dockerfile                   # Application container image
├── pyproject.toml               # Python project metadata and dependencies
├── pytest.ini                   # Pytest configuration
├── README.md                    # Project overview and quick start
├── requirements.txt             # Python dependencies
└── requirements-dev.txt         # Development dependencies
```

## Architecture

Single FastAPI service (`app/main.py`) that:
- Serves the static frontend from `app/static/`
- Exposes `GET /api/health`, `GET /api/config`, `POST /api/analyze`
- Returns curated deterministic results — **no live imagery**

Provider stubs live in `app/providers/`. Each extends `SatelliteProvider` and implements `search_imagery()`. The demo ignores them; they document the real integration contract.

See [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) and [docs/API.md](../docs/API.md) for full details.

## Build and Run

```bash
# Install
pip install -r requirements.txt

# Run (auto-reload)
uvicorn app.main:app --reload
```

Windows shortcut: `run_demo.bat` (creates `.venv`, installs, starts server).

No build step for the frontend — all static files are served as-is.

## Conventions

- All Python files use `from __future__ import annotations`.
- Request/response models use **Pydantic v2** (`model_validator(mode='after')`).
- `TODAY = date(2026, 3, 28)` is hardcoded in `main.py`; the demo's 30-day window is relative to it.
- Curated detection scenarios are defined in the `SCENARIOS` list in `main.py`. Add or modify entries there to change demo output.
- Frontend is vanilla JS + Leaflet + Turf.js — no transpilation, no bundler.

## Key Extension Points

| Intent | Where to edit |
|--------|--------------|
| Real imagery search | `Sentinel2StacProvider.search_scenes()` / `LandsatStacProvider.search_scenes()` in `providers.py` |
| Change detection scenarios | `SCENARIOS` list in `main.py` |
| API shape | `AnalyzeRequest` / `AnalyzeResponse` / `ChangeRecord` models in `main.py` |
| Frontend map behaviour | `backend/app/static/app.js` |

## File Organization Rules

**BLOCKING: Files must never escape proper directory structure**

- **Temporary files**: `*.log`, `*-output.txt`, `*.err` → must be gitignored, never committed
- **Debug scripts**: `debug_*.py`, `test_*.py` → must live in `scripts/` directory
- **Test data**: JSON/GeoJSON test fixtures → must live in `tests/fixtures/`
- **Reference data**: Large data files (ne_10m_land.geojson, etc.) → must live in `scripts/data/`
- **Documentation**: All markdown, reports, guides → must live in appropriate `docs/` subdirectory
- **Screenshots/Images**: PNG, JPG assets → must live in `docs/images/`
- **Reports**: Status reports, verification outputs → must live in `docs/reports/`

Run `python scripts/organize_project.py` to auto-organize misplaced files.

## Pitfalls

- There are **no tests**. Add a `tests/` directory when introducing new logic.
- Do not hardcode new dates or time windows independent of `TODAY`; keep temporal logic relative to it.
- Area calculation in `_polygon_area_km2()` uses a flat-earth approximation — sufficient for a demo, not for production.
- Circle selections are converted to 64-step polygons client-side before the geometry is posted; the backend only accepts `Polygon` / `MultiPolygon`.
- Never commit temporary output files, logs, or build artifacts - they belong in .gitignore.
