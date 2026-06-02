# Jarvis Desktop Assistant — One-click Launcher (Windows)
# Run: .\start.ps1
# Does everything: git pull → deps → Electron fix → launch

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   JARVIS Desktop Assistant v0.3.0   ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Git Pull ──
Write-Host "[1/6] Updating code..." -ForegroundColor Yellow
$stashNeeded = $false
$dirty = git status --porcelain 2>$null
if ($dirty) {
    Write-Host "   Stashing local changes..." -ForegroundColor DarkGray
    git stash push -m "auto-stash by start.ps1" 2>$null
    $stashNeeded = $true
}
git pull 2>&1 | Out-Null
Write-Host "   ✅ Code up to date" -ForegroundColor Green

# ── Python ──
Write-Host "[2/6] Setting up Python environment..." -ForegroundColor Yellow
$py = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $py = "python3" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $py = "py" }
else {
    Write-Host "   ❌ Python not found. Install: winget install Python.Python.3.11" -ForegroundColor Red
    pause; exit 1
}

if (-not (Test-Path ".venv")) {
    & $py -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
    Write-Host "   ✅ Virtual environment created" -ForegroundColor Green
} else {
    & .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt 2>$null
    Write-Host "   ✅ Python deps up to date" -ForegroundColor Green
}

# ── Node.js ──
Write-Host "[3/6] Checking Node.js..." -ForegroundColor Yellow
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "   ❌ Node.js not found. Install: winget install OpenJS.NodeJS.LTS" -ForegroundColor Red
    pause; exit 1
}
Write-Host "   ✅ Node v$(node --version)" -ForegroundColor Green

# ── Frontend + Electron ──
Write-Host "[4/6] Installing frontend dependencies..." -ForegroundColor Yellow
Push-Location frontend

# Install all deps (including electron)
npm install 2>$null

# Fix Electron if binary missing (common Windows issue)
$electronDist = "node_modules\electron\dist\electron.exe"
if (-not (Test-Path $electronDist)) {
    Write-Host "   ⚡ Electron binary missing — downloading..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force node_modules\electron -ErrorAction SilentlyContinue | Out-Null
    npm install electron@35.0.0 2>$null
    
    if (-not (Test-Path $electronDist)) {
        # Last-resort: run install script manually
        Write-Host "   ⚡ Retrying Electron install..." -ForegroundColor Yellow
        try {
            node "node_modules\electron\install.js" 2>$null
        } catch {}
    }
}

if (Test-Path $electronDist) {
    Write-Host "   ✅ Electron ready" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Electron binary still missing (network/proxy issue)" -ForegroundColor Yellow
    Write-Host "   ⚠️  Falling back to browser mode" -ForegroundColor Yellow
}

# Build frontend
npm run build 2>$null
Pop-Location
Write-Host "   ✅ Frontend built" -ForegroundColor Green

# ── Ollama check ──
Write-Host "[5/6] Checking Ollama..." -ForegroundColor Yellow
$ollamaOk = $false
try {
    $ollamaRsp = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    if ($ollamaRsp) { $ollamaOk = $true }
} catch {}

if ($ollamaOk) {
    Write-Host "   ✅ Ollama running" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Ollama not running" -ForegroundColor Yellow
    Write-Host "   💡 Start Ollama from Start Menu, then: ollama pull qwen2.5:7b" -ForegroundColor DarkGray
}

# ── Launch ──
Write-Host "[6/6] Launching Jarvis..." -ForegroundColor Yellow

if (Test-Path "frontend\$electronDist") {
    Write-Host "   🖥️  Opening native Electron window..." -ForegroundColor Cyan
    Push-Location frontend
    $env:ELECTRON_RUN_AS_NODE = "0"
    $electronPath = Resolve-Path $electronDist
    Start-Process -FilePath $electronPath -ArgumentList "." -Wait
    Pop-Location
} else {
    # Browser fallback
    Write-Host "   🌐 Opening in browser: http://localhost:8400" -ForegroundColor Cyan
    Write-Host "   ℹ️  Backend runs in background. Close this window to stop." -ForegroundColor DarkGray
    Start-Process -NoNewWindow .\.venv\Scripts\python.exe -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8400"
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:8400"
    Write-Host "   Press any key to stop backend..." -ForegroundColor DarkGray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

Write-Host ""
Write-Host "✅ Done! ⚡" -ForegroundColor Green
pause
