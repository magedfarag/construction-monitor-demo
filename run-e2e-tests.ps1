#!/usr/bin/env pwsh
#Requires -Version 7.0

<#
.SYNOPSIS
    Run Playwright E2E tests with various parallelization options.

.DESCRIPTION
    Helper script for running E2E tests with common configurations.
    Supports parallel execution, sharding, debugging, and performance modes.

.PARAMETER Mode
    Test execution mode:
    - parallel (default): Run with auto-detected workers
    - fast: Run with 4 workers
    - serial: Run with 1 worker (slowest, original behavior)
    - debug: Run in debug mode with UI
    - ui: Run with Playwright UI mode
    - headed: Run in headed mode (visible browser)

.PARAMETER Workers
    Number of parallel workers to use. Overrides mode-based worker count.

.PARAMETER Shard
    Run a specific shard (e.g., "1/4" for shard 1 of 4 total shards).

.PARAMETER Grep
    Pattern to filter test names.

.PARAMETER File
    Specific test file to run (e.g., "smoke.spec.ts").

.PARAMETER Headed
    Run tests in headed mode (visible browser).

.PARAMETER Report
    Show the HTML test report.

.EXAMPLE
    .\run-e2e-tests.ps1
    Run tests with default parallel configuration

.EXAMPLE
    .\run-e2e-tests.ps1 -Mode fast
    Run tests with 4 workers

.EXAMPLE
    .\run-e2e-tests.ps1 -Mode debug -File smoke.spec.ts
    Debug smoke tests interactively

.EXAMPLE
    .\run-e2e-tests.ps1 -Shard "1/4"
    Run first shard of 4 (for distributed CI)

.EXAMPLE
    .\run-e2e-tests.ps1 -Workers 2 -Grep "accessibility"
    Run accessibility tests with 2 workers
#>

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateSet('parallel', 'fast', 'serial', 'debug', 'ui', 'headed')]
    [string]$Mode = 'parallel',

    [Parameter()]
    [ValidateRange(1, 100)]
    [int]$Workers,

    [Parameter()]
    [ValidatePattern('^\d+/\d+$')]
    [string]$Shard,

    [Parameter()]
    [string]$Grep,

    [Parameter()]
    [string]$File,

    [Parameter()]
    [switch]$Headed,

    [Parameter()]
    [switch]$Report
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Change to frontend directory
$scriptDir = Split-Path -Parent $PSCommandPath
$frontendDir = Join-Path $scriptDir "frontend"
if (-not (Test-Path $frontendDir)) {
    $frontendDir = $PSCommandPath | Split-Path | Split-Path | Join-Path -ChildPath "frontend"
}

if (-not (Test-Path $frontendDir)) {
    Write-Error "Cannot find frontend directory. Expected at: $frontendDir"
    exit 1
}

Push-Location $frontendDir
try {
    # Show report and exit if requested
    if ($Report) {
        Write-Host "Opening test report..." -ForegroundColor Cyan
        npx playwright show-report
        exit 0
    }

    # Check if backend is running
    Write-Host "Checking backend health..." -ForegroundColor Cyan
    $backendUrls = @("http://127.0.0.1:8000/api/health", "http://localhost:8000/api/health")
    $backendHealthy = $false
    foreach ($url in $backendUrls) {
        try {
            $response = Invoke-WebRequest -Uri $url -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $backendHealthy = $true
                Write-Host "βœ" Backend is running at $url" -ForegroundColor Green
                break
            }
        } catch {
            # Continue to next URL
        }
    }

    if (-not $backendHealthy) {
        Write-Warning "Backend doesn't appear to be running. E2E tests require the backend API."
        Write-Host "To start the backend, run:" -ForegroundColor Yellow
        Write-Host "  python -m uvicorn app.main:app --reload" -ForegroundColor Yellow
        $continue = Read-Host "Continue anyway? (y/N)"
        if ($continue -notmatch '^y(es)?$') {
            exit 1
        }
    }

    # Build playwright command
    $playwrightArgs = @('playwright', 'test')

    # Configure workers based on mode
    switch ($Mode) {
        'fast' {
            if (-not $Workers) {
                $playwrightArgs += @('--workers=4')
                Write-Host "Running in FAST mode (4 workers)..." -ForegroundColor Cyan
            }
        }
        'serial' {
            if (-not $Workers) {
                $playwrightArgs += @('--workers=1', '--fully-parallel=false')
                Write-Host "Running in SERIAL mode (1 worker)..." -ForegroundColor Cyan
            }
        }
        'debug' {
            $playwrightArgs += @('--debug')
            Write-Host "Running in DEBUG mode..." -ForegroundColor Cyan
        }
        'ui' {
            $playwrightArgs += @('--ui')
            Write-Host "Running in UI mode..." -ForegroundColor Cyan
        }
        'headed' {
            $playwrightArgs += @('--headed')
            Write-Host "Running in HEADED mode..." -ForegroundColor Cyan
        }
        'parallel' {
            Write-Host "Running in PARALLEL mode (auto workers)..." -ForegroundColor Cyan
        }
    }

    # Override workers if specified
    if ($Workers) {
        $playwrightArgs += @("--workers=$Workers")
        Write-Host "Using $Workers worker(s)..." -ForegroundColor Cyan
    }

    # Add shard configuration
    if ($Shard) {
        $playwrightArgs += @("--shard=$Shard")
        Write-Host "Running shard $Shard..." -ForegroundColor Cyan
    }

    # Add grep filter
    if ($Grep) {
        $playwrightArgs += @("--grep=$Grep")
        Write-Host "Filtering tests matching: $Grep" -ForegroundColor Cyan
    }

    # Add headed flag
    if ($Headed) {
        $playwrightArgs += @('--headed')
    }

    # Add specific file
    if ($File) {
        $playwrightArgs += $File
        Write-Host "Running test file: $File" -ForegroundColor Cyan
    }

    # Display command
    $commandStr = "npx $($playwrightArgs -join ' ')"
    Write-Host "`nExecuting: $commandStr" -ForegroundColor Gray
    Write-Host ""

    # Run playwright
    $startTime = Get-Date
    & npx @playwrightArgs

    $exitCode = $LASTEXITCODE
    $duration = (Get-Date) - $startTime

    Write-Host ""
    if ($exitCode -eq 0) {
        Write-Host "βœ" Tests passed in $([math]::Round($duration.TotalMinutes, 1)) minutes" -ForegroundColor Green
        Write-Host "`nTo view the HTML report, run:" -ForegroundColor Cyan
        Write-Host "  .\run-e2e-tests.ps1 -Report" -ForegroundColor Cyan
    } else {
        Write-Host "βœ— Tests failed after $([math]::Round($duration.TotalMinutes, 1)) minutes" -ForegroundColor Red
        Write-Host "`nTo view the failure report, run:" -ForegroundColor Cyan
        Write-Host "  .\run-e2e-tests.ps1 -Report" -ForegroundColor Cyan
    }

    exit $exitCode

} finally {
    Pop-Location
}
