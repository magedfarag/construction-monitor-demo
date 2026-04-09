# ============================================================
# ARGUS - Start Infrastructure Services
# ============================================================
# Starts only stable services (Redis, PostgreSQL, MinIO) in Docker
# Run application services (API, Worker, Beat) from console for fast iteration
# ============================================================

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "     ARGUS INFRASTRUCTURE SERVICES STARTUP" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[*] Starting infrastructure services (Redis, PostgreSQL, MinIO)..." -ForegroundColor Yellow
Write-Host ""

# Start infrastructure services in detached mode
docker-compose -f docker-compose.infra.yml up -d

Write-Host ""
Write-Host "[*] Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Check service status
Write-Host ""
Write-Host "[*] Service Status:" -ForegroundColor Yellow
docker-compose -f docker-compose.infra.yml ps

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Check each service
Write-Host "[*] Connectivity Check:" -ForegroundColor Yellow
Write-Host ""

$allHealthy = $true

# Redis check
try {
    $redis = Test-NetConnection -ComputerName localhost -Port 6379 -WarningAction SilentlyContinue
    if ($redis.TcpTestSucceeded) {
        Write-Host "  [OK] Redis: localhost:6379" -ForegroundColor Green
    } else {
        Write-Host "  [X] Redis: Not responding" -ForegroundColor Red
        $allHealthy = $false
    }
} catch {
    Write-Host "  [X] Redis: Connection failed" -ForegroundColor Red
    $allHealthy = $false
}

# PostgreSQL check
try {
    $postgres = Test-NetConnection -ComputerName localhost -Port 5432 -WarningAction SilentlyContinue
    if ($postgres.TcpTestSucceeded) {
        Write-Host "  [OK] PostgreSQL: localhost:5432 (geoint/geoint)" -ForegroundColor Green
    } else {
        Write-Host "  [X] PostgreSQL: Not responding" -ForegroundColor Red
        $allHealthy = $false
    }
} catch {
    Write-Host "  [X] PostgreSQL: Connection failed" -ForegroundColor Red
    $allHealthy = $false
}

# MinIO check
try {
    $minio = Test-NetConnection -ComputerName localhost -Port 9000 -WarningAction SilentlyContinue
    if ($minio.TcpTestSucceeded) {
        Write-Host "  [OK] MinIO API: localhost:9000" -ForegroundColor Green
        Write-Host "       Console: http://localhost:9001 (minioadmin/minioadmin123)" -ForegroundColor Gray
    } else {
        Write-Host "  [X] MinIO: Not responding" -ForegroundColor Red
        $allHealthy = $false
    }
} catch {
    Write-Host "  [X] MinIO: Connection failed" -ForegroundColor Red
    $allHealthy = $false
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

if ($allHealthy) {
    Write-Host "[OK] All infrastructure services are healthy!" -ForegroundColor Green
    Write-Host ""
    Write-Host "[*] Next Steps - Start Application Services:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1. Start API Server (Terminal 1):" -ForegroundColor Yellow
    Write-Host "     .\run_api.ps1" -ForegroundColor White
    Write-Host "     -> http://localhost:8000/docs" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Start Celery Worker (Terminal 2):" -ForegroundColor Yellow
    Write-Host "     .\run_worker.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "  3. Start Celery Beat [Optional] (Terminal 3):" -ForegroundColor Yellow
    Write-Host "     .\run_beat.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "[i] Benefits of this approach:" -ForegroundColor Cyan
    Write-Host "    - Fast code reload (no Docker rebuild)" -ForegroundColor Gray
    Write-Host "    - Direct console output for debugging" -ForegroundColor Gray
    Write-Host "    - Easy to restart individual services" -ForegroundColor Gray
    Write-Host "    - Infrastructure services isolated in Docker" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "[!] Some services are not healthy yet." -ForegroundColor Yellow
    Write-Host "    Wait a few seconds and check logs:" -ForegroundColor Yellow
    Write-Host "    docker-compose -f docker-compose.infra.yml logs" -ForegroundColor White
    Write-Host ""
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[*] Useful Commands:" -ForegroundColor Yellow
Write-Host "    View logs:  docker-compose -f docker-compose.infra.yml logs -f" -ForegroundColor White
Write-Host "    Stop all:   docker-compose -f docker-compose.infra.yml down" -ForegroundColor White
Write-Host "    Restart:    docker-compose -f docker-compose.infra.yml restart" -ForegroundColor White
Write-Host ""
