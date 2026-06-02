# Jarvis Desktop Assistant — Dev Start (Windows)
# Starts backend + frontend in dev mode.
# Usage: Right-click → Run with PowerShell, or: .\scripts\dev_start_windows.ps1

$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectDir

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  ⚡ Jarvis Desktop Assistant — Dev Start" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check Python venv
if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1

# Install backend deps
Write-Host "Installing backend dependencies..."
pip install -q -r requirements.txt

# Copy .env if missing
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item .env.example .env
    Write-Host "⚠️  Edit .env with your settings if needed." -ForegroundColor Yellow
}

# Check frontend node_modules
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..."
    Set-Location frontend
    npm install
    Set-Location ..
}

Write-Host ""
Write-Host "Starting backend on http://localhost:8400 ..." -ForegroundColor Green
$BackendJob = Start-Process -NoNewWindow -PassThru `
    .venv\Scripts\python -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8400", "--reload"

Start-Sleep -Seconds 2

Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Green
Set-Location frontend
$FrontendJob = Start-Process -NoNewWindow -PassThru npm -ArgumentList "run", "dev"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  ✅ Jarvis is running!" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend:  http://localhost:8400"
Write-Host "  Frontend: http://localhost:5173"
Write-Host "  API Docs: http://localhost:8400/docs"
Write-Host ""
Write-Host "  Close this window to stop both servers."
Write-Host "==========================================" -ForegroundColor Cyan

# Wait for user to press Ctrl+C
try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    Write-Host "Shutting down..." -ForegroundColor Yellow
    Stop-Process -Id $BackendJob.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $FrontendJob.Id -Force -ErrorAction SilentlyContinue
    Write-Host "👋 Jarvis stopped."
}
