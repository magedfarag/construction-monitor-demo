@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "ENV_FILE=%ROOT%.env"
set "VENV_PYTHON=%ROOT%.venv\Scripts\python.exe"
set "FRONTEND_DIR=%ROOT%frontend"
set "COMPOSE_FILE=%ROOT%docker-compose.infra.yml"
set "DRY_RUN=%ARGUS_DEMO_DRY_RUN%"

rem Set localhost infra defaults only when not already defined.
rem APP_MODE and all credentials are read exclusively from .env.
if not defined REDIS_URL              set "REDIS_URL=redis://localhost:6379/0"
if not defined DATABASE_URL           set "DATABASE_URL=postgresql+psycopg2://geoint:geoint@localhost:5432/geoint"
if not defined CELERY_BROKER_URL      set "CELERY_BROKER_URL=redis://localhost:6379/0"
if not defined CELERY_RESULT_BACKEND  set "CELERY_RESULT_BACKEND=redis://localhost:6379/1"
if not defined OBJECT_STORAGE_ENDPOINT set "OBJECT_STORAGE_ENDPOINT=http://localhost:9000"
if not defined OBJECT_STORAGE_BUCKET  set "OBJECT_STORAGE_BUCKET=geoint-raw"
if not defined OBJECT_STORAGE_ACCESS_KEY set "OBJECT_STORAGE_ACCESS_KEY=minioadmin"
if not defined OBJECT_STORAGE_SECRET_KEY set "OBJECT_STORAGE_SECRET_KEY=minioadmin123"
if not defined ALLOWED_ORIGINS        set "ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8000,http://127.0.0.1:8000"
if not defined ARGUS_BACKEND_TARGET   set "ARGUS_BACKEND_TARGET=http://127.0.0.1:8000"

echo.
echo ================================================================
echo      ARGUS DEMO LAUNCHER - INFRA + BACKEND + WORKER + UI
echo ================================================================
echo.

call :ensure_demo_env || exit /b 1
call :ensure_python || exit /b 1
call :install_backend_deps || exit /b 1
call :detect_frontend_pm || exit /b 1
call :install_frontend_deps || exit /b 1
call :detect_compose || exit /b 1
call :start_infra || exit /b 1
call :wait_for_infra || exit /b 1
call :launch_backend || exit /b 1
call :launch_worker || exit /b 1
call :launch_frontend || exit /b 1
call :wait_for_app_surfaces || exit /b 1

echo.
echo [OK] ARGUS demo services are launching.
echo.
echo   Frontend UI:          http://localhost:5173
echo   Backend API:          http://localhost:8000
echo   Backend API docs:     http://localhost:8000/docs
echo   MinIO console:        http://localhost:9001
echo.
echo   Optional scheduler:   powershell -NoLogo -NoExit -ExecutionPolicy Bypass -File "%ROOT%tools\run_beat.ps1"
echo.

if /I "%DRY_RUN%"=="1" (
  echo [dry-run] Browser launch skipped.
) else (
  start "" "http://localhost:8000/docs"
  start "" "http://localhost:5173"
)

exit /b 0

:ensure_demo_env
if exist "%ENV_FILE%" (
  echo [OK] Using existing .env file ^(demo-mode process overrides are applied for this launcher^).
  exit /b 0
)

echo [*] Creating local .env with demo-friendly defaults...
if /I "%DRY_RUN%"=="1" (
  echo [dry-run] would create "%ENV_FILE%"
  exit /b 0
)

(
  echo # Local demo defaults created by run_demo.bat
  echo APP_MODE=demo
  echo LOG_LEVEL=INFO
  echo LOG_FORMAT=text
  echo REDIS_URL=redis://localhost:6379/0
  echo DATABASE_URL=postgresql+psycopg2://geoint:geoint@localhost:5432/geoint
  echo CELERY_BROKER_URL=redis://localhost:6379/0
  echo CELERY_RESULT_BACKEND=redis://localhost:6379/1
  echo OBJECT_STORAGE_ENDPOINT=http://localhost:9000
  echo OBJECT_STORAGE_BUCKET=geoint-raw
  echo OBJECT_STORAGE_ACCESS_KEY=minioadmin
  echo OBJECT_STORAGE_SECRET_KEY=minioadmin123
  echo ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8000,http://127.0.0.1:8000
  echo API_KEY=
  echo JWT_SECRET=
  echo OPENAQ_API_KEY=replace-with-openaq-api-key
  echo ACLED_EMAIL=replace-with-acled-email@example.com
  echo ACLED_PASSWORD=replace-with-acled-password
) > "%ENV_FILE%"

exit /b 0

:ensure_python
where python >nul 2>nul
if errorlevel 1 (
  echo [X] Python is required but was not found on PATH.
  exit /b 1
)

if exist "%VENV_PYTHON%" (
  echo [OK] Reusing Python virtual environment.
  exit /b 0
)

echo [*] Creating Python virtual environment...
if /I "%DRY_RUN%"=="1" (
  echo [dry-run] python -m venv "%ROOT%.venv"
  exit /b 0
)

python -m venv "%ROOT%.venv"
if errorlevel 1 (
  echo [X] Failed to create the Python virtual environment.
  exit /b 1
)
exit /b 0

:install_backend_deps
echo [*] Ensuring backend dependencies are installed...
if /I "%DRY_RUN%"=="1" (
  echo [dry-run] "%VENV_PYTHON%" -m pip install -r "%ROOT%requirements.txt"
  exit /b 0
)

"%VENV_PYTHON%" -m pip install -r "%ROOT%requirements.txt"
if errorlevel 1 (
  echo [X] Failed to install backend dependencies.
  exit /b 1
)
exit /b 0

:detect_frontend_pm
set "FRONTEND_PM="
where pnpm >nul 2>nul
if not errorlevel 1 set "FRONTEND_PM=pnpm"
if not defined FRONTEND_PM (
  where npm >nul 2>nul
  if not errorlevel 1 set "FRONTEND_PM=npm"
)

if defined FRONTEND_PM (
  echo [OK] Frontend package manager: %FRONTEND_PM%
  exit /b 0
)

echo [X] Neither pnpm nor npm was found on PATH.
exit /b 1

:install_frontend_deps
echo [*] Ensuring frontend dependencies are installed...
if /I "%DRY_RUN%"=="1" (
  if /I "%FRONTEND_PM%"=="pnpm" (
    echo [dry-run] pushd "%FRONTEND_DIR%" ^&^& pnpm install ^&^& popd
  ) else (
    echo [dry-run] pushd "%FRONTEND_DIR%" ^&^& npm install ^&^& popd
  )
  exit /b 0
)

pushd "%FRONTEND_DIR%"
if errorlevel 1 (
  echo [X] Failed to change directory to the frontend workspace.
  exit /b 1
)

if /I "%FRONTEND_PM%"=="pnpm" (
  call pnpm install
) else (
  call npm install
)
set "FRONTEND_INSTALL_EXIT=%ERRORLEVEL%"
popd

if not "%FRONTEND_INSTALL_EXIT%"=="0" (
  echo [X] Failed to install frontend dependencies.
  exit /b 1
)
exit /b 0

:detect_compose
set "COMPOSE_CMD="
docker compose version >nul 2>nul
if not errorlevel 1 set "COMPOSE_CMD=docker compose"
if not defined COMPOSE_CMD (
  docker-compose version >nul 2>nul
  if not errorlevel 1 set "COMPOSE_CMD=docker-compose"
)

if defined COMPOSE_CMD (
  echo [OK] Docker Compose command: %COMPOSE_CMD%
  exit /b 0
)

echo [X] Docker Compose is required but was not found.
exit /b 1

:start_infra
echo [*] Starting Docker infrastructure services...
if /I "%DRY_RUN%"=="1" (
  echo [dry-run] %COMPOSE_CMD% -f "%COMPOSE_FILE%" up -d
  exit /b 0
)

%COMPOSE_CMD% -f "%COMPOSE_FILE%" up -d
if errorlevel 1 (
  echo [X] Failed to start Docker infrastructure services.
  exit /b 1
)
exit /b 0

:wait_for_infra
echo [*] Waiting for Redis, PostgreSQL, and MinIO to accept connections...
if /I "%DRY_RUN%"=="1" (
  echo [dry-run] would wait for ports 6379, 5432, and 9000
  exit /b 0
)

powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ports = 6379,5432,9000; $deadline = (Get-Date).AddMinutes(2); while ((Get-Date) -lt $deadline) { $ready = $true; foreach ($port in $ports) { try { $result = Test-NetConnection -ComputerName 'localhost' -Port $port -WarningAction SilentlyContinue; if (-not $result.TcpTestSucceeded) { $ready = $false; break } } catch { $ready = $false; break } } if ($ready) { exit 0 } Start-Sleep -Seconds 2 }; exit 1"
if errorlevel 1 (
  echo [X] Infrastructure services did not become ready in time.
  exit /b 1
)
echo [OK] Infrastructure services are reachable.
exit /b 0

:launch_backend
if /I "%DRY_RUN%"=="1" (
  echo [dry-run] start "ARGUS Demo Backend" powershell -NoLogo -NoExit -ExecutionPolicy Bypass -File "%ROOT%tools\run_api.ps1"
  exit /b 0
)

start "ARGUS Demo Backend" powershell -NoLogo -NoExit -ExecutionPolicy Bypass -File "%ROOT%tools\run_api.ps1"
exit /b 0

:launch_worker
if /I "%DRY_RUN%"=="1" (
  echo [dry-run] start "ARGUS Demo Worker" powershell -NoLogo -NoExit -ExecutionPolicy Bypass -File "%ROOT%tools\run_worker.ps1"
  exit /b 0
)

start "ARGUS Demo Worker" powershell -NoLogo -NoExit -ExecutionPolicy Bypass -File "%ROOT%tools\run_worker.ps1"
exit /b 0

:launch_frontend
if /I "%FRONTEND_PM%"=="pnpm" (
  set "FRONTEND_RUN_CMD=cd /d ""%FRONTEND_DIR%"" && pnpm dev"
) else (
  set "FRONTEND_RUN_CMD=cd /d ""%FRONTEND_DIR%"" && npm run dev"
)

if /I "%DRY_RUN%"=="1" (
  echo [dry-run] start "ARGUS Demo Frontend" cmd /k "!FRONTEND_RUN_CMD!"
  exit /b 0
)

start "ARGUS Demo Frontend" cmd /k "!FRONTEND_RUN_CMD!"
exit /b 0

:wait_for_app_surfaces
echo [*] Waiting for Backend API and Frontend UI to become reachable...
if /I "%DRY_RUN%"=="1" (
  echo [dry-run] would wait for ports 8000 and 5173
  exit /b 0
)

powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ports = 8000,5173; $deadline = (Get-Date).AddMinutes(3); while ((Get-Date) -lt $deadline) { $ready = $true; foreach ($port in $ports) { try { $result = Test-NetConnection -ComputerName 'localhost' -Port $port -WarningAction SilentlyContinue; if (-not $result.TcpTestSucceeded) { $ready = $false; break } } catch { $ready = $false; break } } if ($ready) { exit 0 } Start-Sleep -Seconds 2 }; exit 1"
if errorlevel 1 (
  echo [X] Backend API and Frontend UI did not become reachable in time.
  echo [X] Check the launched backend and frontend terminals for startup errors.
  exit /b 1
)

echo [OK] Backend API and Frontend UI are reachable.
exit /b 0
