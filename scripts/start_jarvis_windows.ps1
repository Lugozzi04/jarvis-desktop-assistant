# Jarvis Desktop Assistant — Start (Windows)
# Opens Jarvis as a desktop app. Backend auto-managed by Electron.
# Usage: .\scripts\start_jarvis_windows.ps1

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectDir

Write-Host "⚡ Starting Jarvis Desktop Assistant..." -ForegroundColor Cyan

# Quick checks
if (-not (Test-Path ".venv")) {
    Write-Host "❌ .venv not found. Run: .\scripts\setup_local_windows.ps1" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "❌ Dependencies missing. Run: .\scripts\setup_local_windows.ps1" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "frontend\dist")) {
    Write-Host "📦 Building frontend..." -ForegroundColor Yellow
    Set-Location frontend
    npm run build
    Set-Location ..
}

Write-Host "🚀 Launching Jarvis..." -ForegroundColor Green
Set-Location frontend
npx electron .
Set-Location ..
