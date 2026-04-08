# ============================================================
# ARGUS — Start API Server (Local Development)
# ============================================================
# Starts FastAPI with hot-reload for rapid development
# Prerequisites: Infrastructure services running in Docker
#   docker-compose -f docker-compose.infra.yml up -d
# ============================================================

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "     ARGUS API SERVER - LOCAL DEVELOPMENT MODE" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment if not already active
if (-not $env:VIRTUAL_ENV) {
    Write-Host "πŸ" Activating virtual environment..." -ForegroundColor Yellow
    & "$PSScriptRoot\.venv\Scripts\Activate.ps1"
}

# Check infrastructure services
Write-Host "πŸ"Œ Checking infrastructure services..." -ForegroundColor Yellow
$servicesOk = $true

try {
    $redis = Test-NetConnection -ComputerName localhost -Port 6379 -WarningAction SilentlyContinue
    if ($redis.TcpTestSucceeded) {
        Write-Host "  βœ… Redis: Running on port 6379" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Redis: Not responding on port 6379" -ForegroundColor Red
        $servicesOk = $false
    }
} catch {
    Write-Host "  ❌ Redis: Not available" -ForegroundColor Red
    $servicesOk = $false
}

try {
    $postgres = Test-NetConnection -ComputerName localhost -Port 5432 -WarningAction SilentlyContinue
    if ($postgres.TcpTestSucceeded) {
        Write-Host "  βœ… PostgreSQL: Running on port 5432" -ForegroundColor Green
    } else {
        Write-Host "  ❌ PostgreSQL: Not responding on port 5432" -ForegroundColor Red
        $servicesOk = $false
    }
} catch {
    Write-Host "  ❌ PostgreSQL: Not available" -ForegroundColor Red
    $servicesOk = $false
}

try {
    $minio = Test-NetConnection -ComputerName localhost -Port 9000 -WarningAction SilentlyContinue
    if ($minio.TcpTestSucceeded) {
        Write-Host "  βœ… MinIO: Running on port 9000" -ForegroundColor Green
    } else {
        Write-Host "  ❌ MinIO: Not responding on port 9000" -ForegroundColor Red
        $servicesOk = $false
    }
} catch {
    Write-Host "  ❌ MinIO: Not available" -ForegroundColor Red
    $servicesOk = $false
}

Write-Host ""

if (-not $servicesOk) {
    Write-Host "⚠️  WARNING: Some infrastructure services are not running!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To start infrastructure services, run:" -ForegroundColor Yellow
    Write-Host "  docker-compose -f docker-compose.infra.yml up -d" -ForegroundColor White
    Write-Host ""
    Write-Host "Press Ctrl+C to cancel or wait 5 seconds to continue anyway..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

Write-Host "πŸš€ Starting FastAPI server with auto-reload..." -ForegroundColor Cyan
Write-Host "   API: http://localhost:8000" -ForegroundColor White
Write-Host "   Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "   OpenAPI: http://localhost:8000/openapi.json" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start uvicorn with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
