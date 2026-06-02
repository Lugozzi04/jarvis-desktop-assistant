# Jarvis Desktop Assistant — One-click Desktop Launcher (Windows)
# Run: .\start.ps1
# Opens a native Electron window — NOT a browser tab.
# Handles: venv check → npm install → build frontend → launch Electron

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   JARVIS Desktop Assistant v0.3.0   ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check Python ──
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
$py = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $py = "python3" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $py = "py" }
else {
    Write-Host "❌ Python not found. Install from https://python.org" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "   ✅ $py" -ForegroundColor Green

# ── Step 2: Setup venv ──
Write-Host "[2/4] Setting up Python environment..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    & $py -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
    Write-Host "   ✅ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "   ✅ .venv found" -ForegroundColor Green
}

# ── Step 3: Check Node.js + build frontend + install Electron ──
Write-Host "[3/4] Preparing frontend + Electron..." -ForegroundColor Yellow
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "   ❌ Node.js not found — install with: winget install OpenJS.NodeJS.LTS" -ForegroundColor Red
    pause
    exit 1
}

Push-Location frontend

# Install deps (includes Electron)
if (-not (Test-Path "node_modules")) {
    Write-Host "   Installing dependencies..." -ForegroundColor Yellow
    npm install
}

# Build frontend (Electron loads from dist/)
if (-not (Test-Path "dist") -or (Get-Item "dist" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddHours(-1) })) {
    Write-Host "   Building frontend..." -ForegroundColor Yellow
    npm run build
}

Pop-Location

Write-Host "   ✅ Frontend + Electron ready" -ForegroundColor Green

# ── Step 4: Launch Electron Desktop App ──
Write-Host "[4/4] Launching Jarvis Desktop App..." -ForegroundColor Yellow
Write-Host "   ℹ️  The backend starts automatically in the background." -ForegroundColor DarkGray
Write-Host "   ℹ️  A native window will open — NOT a browser tab." -ForegroundColor DarkGray
Write-Host ""

Push-Location frontend
# npx is a .cmd script on Windows — must run via cmd
if ($IsWindows -or $env:OS -eq "Windows_NT") {
    cmd /c "npx electron ."
} else {
    npx electron .
}
Pop-Location

Write-Host ""
Write-Host "✅ Jarvis closed. See you next time! ⚡" -ForegroundColor Green
