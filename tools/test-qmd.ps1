#Requires -Version 5.1
<#
.SYNOPSIS
    Test QMD installation and functionality
#>

$ErrorActionPreference = 'Stop'

# Define qmd function
function qmd {
    $env:XDG_CACHE_HOME = 'C:\tmp\.cache'
    $env:NODE_NO_WARNINGS = '1'
    & node "$env:APPDATA\npm\node_modules\@tobilu\qmd\dist\cli\qmd.js" @args
}

Write-Host "`n=== QMD Installation Test ===" -ForegroundColor Cyan

# Test 1: Check QMD version
Write-Host "`n1. Checking QMD version..." -ForegroundColor Yellow
$version = qmd --version 2>&1
Write-Host "   $version" -ForegroundColor Green

# Test 2: Check daemon status
Write-Host "`n2. Checking daemon on port 8181..." -ForegroundColor Yellow
$daemon = Get-NetTCPConnection -LocalPort 8181 -State Listen -ErrorAction SilentlyContinue
if ($daemon) {
    Write-Host "   ✓ Daemon running on port 8181" -ForegroundColor Green
} else {
    Write-Host "   ✗ Daemon NOT running on port 8181" -ForegroundColor Red
}

# Test 3: List collections
Write-Host "`n3. Listing collections..." -ForegroundColor Yellow
$collections = qmd collection list 2>&1 | Select-String -Pattern "^(docs|demo) \("
if ($collections) {
    $collections | ForEach-Object { Write-Host "   ✓ $_" -ForegroundColor Green }
} else {
    Write-Host "   No collections found for this project" -ForegroundColor Yellow
}

# Test 4: Test HTTP endpoint
Write-Host "`n4. Testing MCP HTTP endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8181/mcp" -Method POST `
        -ContentType "application/json" `
        -Body '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' `
        -TimeoutSec 5
    if ($response.result.tools) {
        Write-Host "   ✓ MCP server responding" -ForegroundColor Green
        Write-Host "   Found $($response.result.tools.Count) tools" -ForegroundColor Green
    }
} catch {
    Write-Host "   ✗ MCP server not responding: $_" -ForegroundColor Red
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan
Write-Host "`nTo use QMD in VS Code:" -ForegroundColor White
Write-Host "  1. Reload VS Code window (Ctrl+Shift+P: Developer: Reload Window)" -ForegroundColor Yellow
Write-Host "  2. QMD MCP tools will be available as mcp_qmd_*" -ForegroundColor Yellow
Write-Host ""
