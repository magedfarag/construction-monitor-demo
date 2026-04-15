# ============================================================
# ARGUS — Start Celery Beat Scheduler (Local Development)
# ============================================================
# Starts Celery beat scheduler for periodic tasks
# Prerequisites: Infrastructure services running in Docker
#   docker-compose -f docker-compose.infra.yml up -d
# ============================================================

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "     ARGUS CELERY BEAT - LOCAL DEVELOPMENT MODE" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

# Activate virtual environment if not already active
if ((-not $env:VIRTUAL_ENV) -and (Test-Path $venvPython)) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & (Join-Path $venvDir "Scripts\Activate.ps1")
}

# Check Redis (required for Celery broker)
Write-Host "Checking Redis broker..." -ForegroundColor Yellow
try {
    $redis = Test-NetConnection -ComputerName localhost -Port 6379 -WarningAction SilentlyContinue
    if ($redis.TcpTestSucceeded) {
        Write-Host "  [OK] Redis: Running on port 6379" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Redis: Not responding on port 6379" -ForegroundColor Red
        Write-Host ""
        Write-Host "CRITICAL: Redis is required for Celery broker!" -ForegroundColor Red
        Write-Host "Start infrastructure services first:" -ForegroundColor Yellow
        Write-Host "  docker-compose -f docker-compose.infra.yml up -d" -ForegroundColor White
        Write-Host ""
        exit 1
    }
} catch {
    Write-Host "  ❌ Redis: Not available" -ForegroundColor Red
    Write-Host ""
    Write-Host "CRITICAL: Redis is required for Celery broker!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting Celery beat scheduler..." -ForegroundColor Cyan
Write-Host "   Broker: redis://localhost:6379/0" -ForegroundColor White
Write-Host "   Schedule: $env:TEMP\celerybeat-schedule" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  NOTE: Make sure a Celery worker is also running!" -ForegroundColor Yellow
Write-Host "   Run in another terminal: .\run_worker.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the scheduler" -ForegroundColor Yellow
Write-Host ""

# Start Celery beat scheduler
if (Test-Path $venvPython) {
    & $venvPython -m celery -A app.workers.celery_app.celery_app beat --loglevel=info --schedule="$env:TEMP\celerybeat-schedule"
} else {
    python -m celery -A app.workers.celery_app.celery_app beat --loglevel=info --schedule="$env:TEMP\celerybeat-schedule"
}
