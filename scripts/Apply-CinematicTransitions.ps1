#Requires -Version 5.1
<#
.SYNOPSIS
    Apply cinematic camera transitions to ARGUS demo Playwright template
.DESCRIPTION
    Replaces standard mapFlyTo calls with cinematic mapFlyToCinematic for smooth,
    dramatic camera movements in key demo scenes.
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$templatePath = Join-Path $PSScriptRoot '..' 'demo' 'templates' 'playwright-template.js'

if (-not (Test-Path $templatePath)) {
    Write-Error "Template not found: $templatePath"
    exit 1
}

Write-Host "Applying cinematic camera transitions..." -ForegroundColor Cyan

$content = Get-Content $templatePath -Raw

# Count original mapFlyTo calls for progress tracking
$originalCount = ([regex]::Matches($content, 'mapFlyTo\(p, HORMUZ\.')).Count
Write-Host "  Found $originalCount camera movements to enhance" -ForegroundColor Gray

# Globe scene - Hero opening (make it DRAMATIC)
$content = $content -replace `
    '(\[\s*3000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.gulf, 0\.8\)', `
    '$1mapFlyToCinematic(p, HORMUZ.gulf, 3500, ''dramatic'')'

$content = $content -replace `
    '(\[\s*5000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.strait, 0\.7\)\],\s*//', `
    '$1mapFlyToCinematic(p, HORMUZ.strait, 3500, ''dramatic'')],  //'

$content = $content -replace `
    '(\[\s*8500,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.aircraft, 0\.6\)', `
    '$1mapFlyToCinematic(p, HORMUZ.aircraft, 3000, ''smooth'')'

$content = $content -replace `
    '(\[13000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.vesselCluster, 0\.5\)\],\s*// Zoom to suspicious vessel cluster', `
    '$1mapFlyToCinematic(p, HORMUZ.vesselCluster, 3500, ''dramatic'')], // Dramatic zoom to vessel cluster'

$content = $content -replace `
    '(\[18000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.chokepoint, 0\.5\)\],\s*// Extreme zoom on chokepoint', `
    '$1mapFlyToCinematic(p, HORMUZ.chokepoint, 4000, ''dramatic'')], // Extreme cinematic zoom'

$content = $content -replace `
    '(\[22000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.tacticalView, 0\.6\)\],\s*// Tactical overview', `
    '$1mapFlyToCinematic(p, HORMUZ.tacticalView, 2500, ''gentle'')], // Smooth tactical pull-back'

$content = $content -replace `
    '(\[27000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.strait, 0\.7\)\],\s*// Return to strait view', `
    '$1mapFlyToCinematic(p, HORMUZ.strait, 2500)],    // Smooth return to strait'

# Animation scene - Pattern-of-life
$content = $content -replace `
    '(\[\s*5000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.strait, 0\.7\)\]', `
    '$1mapFlyToCinematic(p, HORMUZ.strait, 2500)]'

$content = $content -replace `
    '(\[10000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.vesselTrack, 0\.6\)\],\s*// Follow vessel', `
    '$1mapFlyToCinematic(p, HORMUZ.vesselTrack, 3000, ''smooth'')], // Cinematic vessel track follow'

$content = $content -replace `
    '(\[15000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.vesselCluster, 0\.5\)\],\s*// Zoom to anomalous cluster', `
    '$1mapFlyToCinematic(p, HORMUZ.vesselCluster, 3000, ''dramatic'')], // Dramatic cluster zoom'

$content = $content -replace `
    '(\[20000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.tacticalView, 0\.6\)\],\s*// Tactical view', `
    '$1mapFlyToCinematic(p, HORMUZ.tacticalView, 2500, ''gentle'')], // Smooth tactical view'

$content = $content -replace `
    '(\[28000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.chokepoint, 0\.5\)\],\s*// Extreme zoom', `
    '$1mapFlyToCinematic(p, HORMUZ.chokepoint, 3500, ''dramatic'')], // Extreme cinematic zoom'

$content = $content -replace `
    '(\[32000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.overview\)\]', `
    '$1mapFlyToCinematic(p, HORMUZ.overview, 2500)]'

# Dark Ships scene - Threat detection
$content = $content -replace `
    '(\[\s*4000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.chokepoint, 0\.6\)\],\s*// Extreme zoom to conflict zone', `
    '$1mapFlyToCinematic(p, HORMUZ.chokepoint, 3000, ''dramatic'')], // Dramatic zoom to threat'

$content = $content -replace `
    '(\[\s*9500,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.vesselCluster, 0\.5\)\],\s*// Zoom to vessel cluster', `
    '$1mapFlyToCinematic(p, HORMUZ.vesselCluster, 3500, ''dramatic'')], // Dramatic cluster zoom'

$content = $content -replace `
    '(\[16000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.tacticalView, 0\.6\)\],\s*// Tactical threat', `
    '$1mapFlyToCinematic(p, HORMUZ.tacticalView, 2500, ''gentle'')], // Smooth tactical view'

# Vessel Profile scene
$content = $content -replace `
    '(\[\s*6500,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.vesselTrack, 0\.6\)\],\s*// Show historical track', `
    '$1mapFlyToCinematic(p, HORMUZ.vesselTrack, 2500, ''smooth'')], // Smooth track follow'

$content = $content -replace `
    '(\[19000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.chokepoint, 0\.5\)\],\s*// Zoom to show transit', `
    '$1mapFlyToCinematic(p, HORMUZ.chokepoint, 3000, ''dramatic'')], // Dramatic transit zoom'

# Routes scene - Chokepoints
$content = $content -replace `
    '(\[\s*2000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.strait\)\]', `
    '$1mapFlyToCinematic(p, HORMUZ.strait, 2000)]'

$content = $content -replace `
    '(\[\s*8000,\s*p\s*=>\s*)mapFlyTo\(p, \{ center: \[103\.80', `
    '$1mapFlyToCinematic(p, { center: [103.80'

$content = $content -replace `
    '(\[13000,\s*p\s*=>\s*)mapFlyTo\(p, \{ center: \[32\.50', `
    '$1mapFlyToCinematic(p, { center: [32.50'

# Cases scene
$content = $content -replace `
    '(\[\s*6000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.strait\)\]', `
    '$1mapFlyToCinematic(p, HORMUZ.strait, 2000)]'

$content = $content -replace `
    '(\[15000,\s*p\s*=>\s*)mapFlyTo\(p, HORMUZ\.chokepoint, 0\.6\)\]', `
    '$1mapFlyToCinematic(p, HORMUZ.chokepoint, 2500, ''dramatic'')]'

# Count enhanced moves
$enhancedCount = ([regex]::Matches($content, 'mapFlyToCinematic\(p, HORMUZ\.')).Count
Write-Host "  ✓ Enhanced $enhancedCount camera movements with cinematic transitions" -ForegroundColor Green

# Save changes
Set-Content $templatePath $content -NoNewline
Write-Host "  ✓ Template updated: $templatePath" -ForegroundColor Green

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Build frontend: npm run build (in frontend/)" -ForegroundColor Gray
Write-Host "  2. Start both servers (backend + frontend)" -ForegroundColor Gray
Write-Host "  3. Regenerate demo: .\scripts\New-ManagementDemoVideo-Simple.ps1 -SkipVoice" -ForegroundColor Gray
