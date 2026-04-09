# Quick Start

This project has three practical startup paths depending on whether you need only the API, the full local analyst workflow, or the backend stack in containers.

## Option 1: Backend Only

Use this when you want the API and OpenAPI docs without Redis, workers, or the React UI.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/api/health`

Notes:

- Default mode is `APP_MODE=staging`.
- Without `API_KEY`, auth checks are bypassed for developer convenience.
- Without `REDIS_URL`, async Celery-backed jobs are unavailable.

## Option 2: Local Analyst Workflow

Use this when you want the backend, worker, optional beat scheduler, and the React UI.

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

- UI: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/api/health`

The frontend dev server proxies `/api`, `/healthz`, `/readyz`, `/static`, and `/demo` to the backend. Override the backend target with `ARGUS_BACKEND_TARGET` if needed.

## Option 3: Full Backend Compose Stack

Use this when you want Redis, Postgres/PostGIS, MinIO, API, worker, and beat managed together by Docker Compose.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open:

- Backend API docs: `http://localhost:8000/docs`
- MinIO console: `http://localhost:9001`

Notes:

- The Compose stack does not include the Vite frontend.
- Run `cd frontend && npm install && npm run dev` separately if you want the UI.
- Compose injects container-friendly service URLs for Redis, Postgres, and MinIO.

## Mode Selection

| Mode | When to use it |
|---|---|
| `demo` | Fully synthetic data, demos, and safe offline exploration |
| `staging` | Default local mode with real providers when credentials are present |
| `production` | Real-provider-only execution with no demo fallback |

See [local-development.md](local-development.md), [../DEPLOYMENT.md](../DEPLOYMENT.md), and [../reference/environment.md](../reference/environment.md) for the full setup model.
