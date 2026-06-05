# Jarvis Desktop Assistant — One-Click Launcher (Windows)
# Run: .\start.ps1
# NO npm, NO Electron, NO browser. Just Python + native webview.

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  JARVIS Desktop Assistant v0.3.0    ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Git pull (force-update to latest) ──
Write-Host "[1/5] Updating code..." -ForegroundColor Yellow
if (Test-Path ".git") {
    # Fetch latest and force-reset to remote main (avoids stash/merge issues)
    git fetch origin 2>&1 | Out-Null
    git checkout main 2>&1 | Out-Null
    git reset --hard origin/main 2>&1 | Out-Null
    git clean -fd 2>&1 | Out-Null
    Write-Host "   ✅ Code up to date" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Not a git repo — skipping pull" -ForegroundColor Yellow
}

# ── Step 2: Check Python ──
Write-Host "[2/5] Setting up Python..." -ForegroundColor Yellow
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

# ── Step 3: Setup venv + install deps ──
Write-Host "[3/5] Installing dependencies..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    & $py -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -q --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
Write-Host "   ✅ Dependencies up to date" -ForegroundColor Green

# ── Step 4: Build Frontend (CRITICAL — rebuilds UI after code changes) ──
Write-Host "[4/5] Building frontend..." -ForegroundColor Yellow
if (Get-Command npm -ErrorAction SilentlyContinue) {
    if (Test-Path "frontend/package.json") {
        # Install frontend deps if needed
        if (-not (Test-Path "frontend/node_modules")) {
            Write-Host "   📦 Installing frontend deps..." -ForegroundColor DarkGray
            Push-Location frontend
            npm install --silent 2>&1 | Out-Null
            Pop-Location
        }
        # Build frontend
        Push-Location frontend
        $buildResult = npm run build 2>&1
        Pop-Location
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ Frontend built" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  Frontend build failed — using existing build if available" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ⚠️  No frontend/package.json found" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠️  npm not found — skipping build (install Node.js for UI)" -ForegroundColor Yellow
    if (-not (Test-Path "frontend/dist/index.html")) {
        Write-Host "   ❌ No pre-built frontend found. Install Node.js and run: cd frontend && npm install && npm run build" -ForegroundColor Red
    }
}

# ── Step 5: Launch Jarvis Desktop App ──
Write-Host "[5/5] Launching Jarvis..." -ForegroundColor Yellow
Write-Host "   🖥️  Opening native window — close it to exit." -ForegroundColor DarkGray

# Check Ollama
$ollamaRunning = $false
try {
    $r = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($r.StatusCode -eq 200) {
        $ollamaRunning = $true
        Write-Host "   🤖 Ollama connected" -ForegroundColor Green
    }
} catch {
    Write-Host "   💡 Start Ollama from Start Menu for LLM chat: ollama pull qwen2.5:7b" -ForegroundColor Yellow
}

# Check Voice / Whisper
Write-Host "   🎤 Checking voice..."
$whisperOk = $false
try {
    $r = & .\.venv\Scripts\python.exe -c "import faster_whisper; print('ok')" 2>&1
    if ($r -eq "ok") {
        $whisperOk = $true
        Write-Host "   🎤 faster-whisper ready — speech-to-text enabled" -ForegroundColor Green
    }
} catch {
    Write-Host "   💡 Voice STT not available (auto-installed next run)" -ForegroundColor Yellow
}

# Check Screen Capture & OCR
Write-Host "   📸 Checking screen capture..."
try {
    $r = & .\.venv\Scripts\python.exe -c "import mss; print('ok')" 2>&1
    if ($r -eq "ok") { Write-Host "   📸 mss ready — screen capture enabled" -ForegroundColor Green }
} catch {
    Write-Host "   💡 Screen capture not available" -ForegroundColor Yellow
}

try {
    $r = & .\.venv\Scripts\python.exe -c "import pynput; print('ok')" 2>&1
    if ($r -eq "ok") { Write-Host "   ⌨️  pynput ready — global hotkey enabled" -ForegroundColor Green }
} catch {
    Write-Host "   ⚠️  pynput not found — installing..." -ForegroundColor Yellow
    & .\.venv\Scripts\python.exe -m pip install -q pynput
    Write-Host "   ✅ pynput installed" -ForegroundColor Green
}

try {
    $r = & .\.venv\Scripts\python.exe -c "import pytesseract; print('ok')" 2>&1
    if ($r -eq "ok") { Write-Host "   🔤 pytesseract ready — OCR enabled" -ForegroundColor Green }
} catch {
    Write-Host "   💡 OCR not available (install Tesseract-OCR for screen reading)" -ForegroundColor Yellow
}

try {
    $r = & .\.venv\Scripts\python.exe -c "import pystray; print('ok')" 2>&1
    if ($r -eq "ok") { Write-Host "   🔔 pystray ready — system tray enabled" -ForegroundColor Green }
} catch {
    Write-Host "   💡 System tray not available" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "   🖥️  Launch mode:" -ForegroundColor White
Write-Host "      • Windowed (full UI) — default" -ForegroundColor DarkGray
Write-Host "      • Tray (Ctrl+Shift overlay) — use 'start.ps1 --tray'" -ForegroundColor DarkGray
Write-Host ""

if ($args[0] -eq "--tray") {
    Write-Host "   🔔 Starting in SYSTEM TRAY mode — Ctrl+Shift to open overlay" -ForegroundColor Cyan
    & .\.venv\Scripts\python.exe -m backend.desktop_tray
} else {
    Write-Host "   🖥️  Starting in WINDOWED mode — full UI" -ForegroundColor Cyan
    & .\.venv\Scripts\python.exe -m backend.desktop
}

Write-Host ""
Write-Host "✅ Jarvis closed. See you next time! ⚡" -ForegroundColor Green
pause
