# ARGUS Local Development Guide

## Overview

This guide describes the **hybrid development approach** for ARGUS, which separates stable infrastructure services from frequently updated application code for faster iteration cycles.

## Architecture

### Infrastructure Services (Docker)
These services run in Docker and rarely change:
- **Redis** (port 6379) - Cache, Celery broker/backend
- **PostgreSQL/PostGIS** (port 5432) - Persistent storage
- **MinIO** (ports 9000, 9001) - S3-compatible object storage

### Application Services (Console)
These services run directly from the console for fast reload:
- **API Server** (port 8000) - FastAPI with auto-reload
- **Celery Worker** - Background task processor
- **Celery Beat** - Periodic task scheduler

## Quick Start

### 1. Start Infrastructure Services

```powershell
.\start_infra.ps1
```

This will:
- Start Redis, PostgreSQL, and MinIO in Docker
- Verify all services are healthy
- Create MinIO buckets (raw, exports, thumbnails, artifacts)

**Wait for all health checks to pass** (usually 10-15 seconds).

### 2. Start Application Services

Open **3 separate terminals** in the project directory:

#### Terminal 1: API Server
```powershell
.\run_api.ps1
```
- Access API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Auto-reloads on code changes

#### Terminal 2: Celery Worker
```powershell
.\run_worker.ps1
```
- Processes background tasks
- Required for async operations

#### Terminal 3: Celery Beat (Optional)
```powershell
.\run_beat.ps1
```
- Schedules periodic tasks (polling external APIs)
- Only needed for scheduled jobs

## Benefits of This Approach

| Aspect | Traditional Docker | Hybrid Approach |
|--------|-------------------|-----------------|
| **Code Changes** | Rebuild images (~2-5 min) | Instant reload (<1 sec) |
| **Logging** | `docker logs` indirection | Direct console output |
| **Debugging** | Attach to container | Native debugger support |
| **Restart Speed** | Container restart (~10 sec) | Ctrl+C + restart (~2 sec) |
| **Resource Usage** | 6 containers | 3 containers + 3 processes |

## Configuration

All configuration is in `.env`. Key settings for local development:

```bash
# Infrastructure (localhost when running from console)
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql+psycopg2://geoint:geoint@localhost:5432/geoint
OBJECT_STORAGE_ENDPOINT=http://localhost:9000
OBJECT_STORAGE_ACCESS_KEY=minioadmin
OBJECT_STORAGE_SECRET_KEY=minioadmin123

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

**Note:** Docker Compose automatically overrides these with service names (redis, db, minio) inside containers.

## Common Operations

### View Infrastructure Logs
```powershell
docker-compose -f docker-compose.infra.yml logs -f
```

### Stop Infrastructure
```powershell
docker-compose -f docker-compose.infra.yml down
```

### Restart a Specific Service
```powershell
docker-compose -f docker-compose.infra.yml restart redis
```

### Reset Database
```powershell
docker-compose -f docker-compose.infra.yml down -v  # Remove volumes
.\start_infra.ps1  # Recreate fresh
```

### Access MinIO Console
Open http://localhost:9001 in browser:
- Username: `minioadmin`
- Password: `minioadmin123`

### Connect to PostgreSQL
```powershell
docker exec -it world-view-db-1 psql -U geoint -d geoint
```

Or use any PostgreSQL client:
- Host: localhost
- Port: 5432
- Database: geoint
- Username: geoint
- Password: geoint

### Check Redis
```powershell
docker exec -it world-view-redis-1 redis-cli ping
```

## Troubleshooting

### Port Already in Use
If you see "port already allocated" errors:

```powershell
# Find process using the port
netstat -ano | findstr "6379"  # Redis
netstat -ano | findstr "5432"  # PostgreSQL
netstat -ano | findstr "9000"  # MinIO

# Stop the process or use different ports in docker-compose.infra.yml
```

### Services Not Healthy
```powershell
# Check service status
docker-compose -f docker-compose.infra.yml ps

# View logs for specific service
docker-compose -f docker-compose.infra.yml logs redis
docker-compose -f docker-compose.infra.yml logs db
docker-compose -f docker-compose.infra.yml logs minio
```

### Application Can't Connect to Infrastructure
1. Verify infrastructure services are running:
   ```powershell
   docker-compose -f docker-compose.infra.yml ps
   ```

2. Check `.env` uses `localhost` URLs (not service names)

3. Restart the application service

### Celery Worker Won't Start on Windows
The worker uses `--pool=solo` which is Windows-compatible. If you still have issues:

```powershell
# Add to .env
FORKED_BY_MULTIPROCESSING=1
```

## Full Docker Mode (Production/Testing)

To run **everything** in Docker (including API/worker/beat):

```powershell
docker-compose up -d --build
```

This uses the original `docker-compose.yml` with all 6 services.

Use this for:
- Production deployment
- Integration testing
- Testing with fresh environment
- When you don't need fast iteration

## Migration from Old Workflow

If you were using the old `run_demo.bat` or `docker-compose up`:

**Old:**
```powershell
docker-compose up -d --build  # Rebuild everything
# Wait 10-15 minutes for build
# Edit code
# docker-compose restart api  # Restart to see changes
```

**New:**
```powershell
.\start_infra.ps1             # Start infrastructure (once)
.\run_api.ps1                 # Start API with hot reload
# Edit code
# Changes apply instantly!
```

## File Reference

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Full stack (all 6 services) |
| `docker-compose.infra.yml` | Infrastructure only (redis, db, minio) |
| `start_infra.ps1` | Start infrastructure with health checks |
| `run_api.ps1` | Start API server with auto-reload |
| `run_worker.ps1` | Start Celery worker |
| `run_beat.ps1` | Start Celery beat scheduler |
| `.env` | Configuration (shared by all modes) |

## Tips

- Keep infrastructure running between sessions (no need to restart daily)
- Use `docker-compose -f docker-compose.infra.yml down` only when updating Docker images
- Run API/worker/beat in VS Code integrated terminals for click-to-trace
- Use separate PowerShell profiles for each service to avoid confusion
- Set VS Code launch configs to attach to localhost:8000 for debugging

## Next Steps

After starting services:
1. Verify external APIs: `python verify_data_sources.py`
2. Access API docs: http://localhost:8000/docs
3. Check system health: http://localhost:8000/health
4. Review platform status: See `SERVICES_STATUS_REPORT.md`
