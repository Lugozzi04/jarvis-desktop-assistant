# Jarvis Desktop Assistant — One-Click Launcher (Windows)
# Run: .\start.ps1
# NO npm, NO Electron, NO browser. Just Python + native webview.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  JARVIS Desktop Assistant v0.3.0    ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Git pull (auto-stash local changes) ──
Write-Host "[1/4] Updating code..." -ForegroundColor Yellow
$stashed = $false
if (Test-Path ".git") {
    $status = git status --porcelain 2>$null
    if ($status) {
        git stash push -m "auto-stash by start.ps1" 2>&1 | Out-Null
        $stashed = $true
    }
    git pull --ff-only 2>&1 | Out-Null
    if ($stashed) {
        git stash pop 2>&1 | Out-Null
    }
    Write-Host "   ✅ Code up to date" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Not a git repo — skipping pull" -ForegroundColor Yellow
}

# ── Step 2: Check Python ──
Write-Host "[2/4] Setting up Python..." -ForegroundColor Yellow
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
Write-Host "[3/4] Installing dependencies..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    & $py -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -q --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
Write-Host "   ✅ Dependencies up to date" -ForegroundColor Green

# ── Step 4: Launch Jarvis Desktop App ──
Write-Host "[4/4] Launching Jarvis..." -ForegroundColor Yellow
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

Write-Host ""
& .\.venv\Scripts\python.exe -m backend.desktop

Write-Host ""
Write-Host "✅ Jarvis closed. See you next time! ⚡" -ForegroundColor Green
pause
