# Jarvis Desktop Assistant — Local Setup (Windows)
# Installs all dependencies. Does NOT install Ollama or download models.
# Usage: Right-click → Run with PowerShell
#    or: powershell -ExecutionPolicy Bypass -File scripts/setup_local_windows.ps1

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectDir

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  ⚡ Jarvis Desktop Assistant — Setup (Windows)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# ── Check Python ──
Write-Host "1️⃣  Checking Python..." -ForegroundColor White
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $v = & $cmd --version 2>&1
        if ($v -match "Python 3") {
            $pythonCmd = $cmd
            Write-Host "   ✅ $v"
            break
        }
    } catch {}
}
if (-not $pythonCmd) {
    Write-Host "   ❌ Python 3 not found." -ForegroundColor Red
    Write-Host "   Install from: https://www.python.org/downloads/"
    Write-Host "   Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

# ── Check Node ──
Write-Host "2️⃣  Checking Node.js..." -ForegroundColor White
try {
    $nv = node --version 2>&1
    Write-Host "   ✅ $nv"
} catch {
    Write-Host "   ❌ Node.js not found." -ForegroundColor Red
    Write-Host "   Install from: https://nodejs.org/ (LTS recommended)"
    exit 1
}

# ── Create venv ──
Write-Host "3️⃣  Setting up Python virtual environment..." -ForegroundColor White
if (-not (Test-Path ".venv")) {
    & $pythonCmd -m venv .venv
    Write-Host "   ✅ Created .venv"
} else {
    Write-Host "   ✅ .venv already exists"
}

# ── Install Python deps ──
Write-Host "4️⃣  Installing Python dependencies..." -ForegroundColor White
& .\.venv\Scripts\python.exe -m pip install -q --upgrade pip 2>&1 | Out-Null
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
Write-Host "   ✅ Python dependencies installed"

# ── Install Node deps ──
Write-Host "5️⃣  Installing frontend dependencies..." -ForegroundColor White
Set-Location frontend
npm install --silent 2>$null
if ($LASTEXITCODE -ne 0) { npm install }
Set-Location ..
Write-Host "   ✅ Frontend dependencies installed"

# ── Create .env ──
Write-Host "6️⃣  Setting up configuration..." -ForegroundColor White
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "   ✅ Created .env from .env.example"
} else {
    Write-Host "   ✅ .env already exists"
}

# ── Build frontend ──
Write-Host "7️⃣  Building frontend..." -ForegroundColor White
Set-Location frontend
npm run build 2>&1 | Select-Object -Last 1
Set-Location ..
Write-Host "   ✅ Frontend built"

# ── Done ──
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  ✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Optional — install Ollama for AI features:" -ForegroundColor Yellow
Write-Host "    winget install Ollama.Ollama"
Write-Host "    ollama pull qwen2.5:7b"
Write-Host "    ollama pull nomic-embed-text"
Write-Host ""
Write-Host "  Optional — voice setup (PowerShell as Admin):" -ForegroundColor Yellow
Write-Host "    pip install faster-whisper"
Write-Host ""
Write-Host "  Start Jarvis:" -ForegroundColor Green
Write-Host "    .\scripts\start_jarvis_windows.ps1"
Write-Host "==========================================" -ForegroundColor Cyan
