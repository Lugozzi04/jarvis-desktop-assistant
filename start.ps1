# Jarvis — One-click launcher (Windows)
# Run: .\start.ps1
# Does everything: check deps → install → build → start backend → open browser

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        JARVIS Desktop Assistant      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Step 0: Check Python ──
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
$py = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $py = "python3" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $py = "py" }
else {
    Write-Host "❌ Python not found. Install from https://python.org (spunta 'Add to PATH')" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "   ✅ $py" -ForegroundColor Green

# ── Step 1: Setup venv if missing ──
Write-Host "[2/5] Setting up Python environment..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    & $py -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
    Write-Host "   ✅ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "   ✅ .venv found" -ForegroundColor Green
}

# ── Step 2: Check Node.js & build frontend ──
Write-Host "[3/5] Checking Node.js..." -ForegroundColor Yellow
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "   ⚠️  Node.js not found — install with: winget install OpenJS.NodeJS.LTS" -ForegroundColor Yellow
    Write-Host "   Skipping frontend build (API only mode)" -ForegroundColor Yellow
} else {
    if (-not (Test-Path "frontend\node_modules")) {
        Write-Host "   Installing frontend dependencies..." -ForegroundColor Yellow
        Set-Location frontend
        npm install
        Set-Location ..
    }
    if (-not (Test-Path "frontend\dist")) {
        Write-Host "   Building frontend..." -ForegroundColor Yellow
        Set-Location frontend
        npm run build
        Set-Location ..
    }
    Write-Host "   ✅ Frontend ready" -ForegroundColor Green
}

# ── Step 3: Start backend ──
Write-Host "[4/5] Starting backend on http://localhost:8400 ..." -ForegroundColor Yellow
Write-Host "   Press Ctrl+C to stop" -ForegroundColor DarkGray
Write-Host ""

Start-Process -NoNewWindow .\.venv\Scripts\python.exe -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8400"

Start-Sleep -Seconds 3

# ── Step 4: Open browser ──
Write-Host "[5/5] Opening Jarvis... $([Environment]::NewLine)   http://localhost:8400" -ForegroundColor Cyan
Start-Process "http://localhost:8400"

Write-Host ""
Write-Host "✅ Jarvis is running!" -ForegroundColor Green
Write-Host "   UI:  http://localhost:8400" -ForegroundColor Cyan
Write-Host "   API: http://localhost:8400/health" -ForegroundColor DarkGray
Write-Host ""
Write-Host "💡 To enable LLM chat: open Ollama from Start Menu → ollama pull qwen2.5:7b" -ForegroundColor Yellow
Write-Host "   Slash commands work without LLM: /open notepad, /search query, /timer 5m test" -ForegroundColor DarkGray
Write-Host ""
pause
