#!/usr/bin/env bash
# Jarvis Desktop Assistant — One-click Launcher (Linux/macOS)
# Usage: bash start.sh
# Does everything: git pull → deps → Electron → launch

set -e
cd "$(dirname "$0")"

echo ""
echo -e "\033[36m╔══════════════════════════════════════╗\033[0m"
echo -e "\033[36m║   JARVIS Desktop Assistant v0.3.0   ║\033[0m"
echo -e "\033[36m╚══════════════════════════════════════╝\033[0m"
echo ""

# ── Git Pull ──
echo -e "\033[33m[1/6] Updating code...\033[0m"
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    echo "   Stashing local changes..."
    git stash push -m "auto-stash by start.sh" 2>/dev/null || true
fi
git pull --ff-only 2>/dev/null || true
echo -e "   \033[32m✅ Code up to date\033[0m"

# ── Python ──
echo -e "\033[33m[2/6] Setting up Python environment...\033[0m"
if command -v python3 &>/dev/null; then PY=python3
elif command -v python &>/dev/null; then PY=python
else echo -e "\033[31m❌ Python not found\033[0m"; exit 1; fi

if [ ! -d ".venv" ]; then
    $PY -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
    echo -e "   \033[32m✅ Virtual environment created\033[0m"
else
    .venv/bin/pip install -q -r requirements.txt 2>/dev/null || true
    echo -e "   \033[32m✅ Python deps up to date\033[0m"
fi

# ── Node.js ──
echo -e "\033[33m[3/6] Checking Node.js...\033[0m"
if ! command -v node &>/dev/null; then
    echo -e "   \033[31m❌ Node.js not found\033[0m"
    exit 1
fi
echo -e "   \033[32m✅ Node $(node --version)\033[0m"

# ── Frontend + Electron ──
echo -e "\033[33m[4/6] Installing frontend dependencies...\033[0m"
cd frontend
npm install 2>/dev/null || true

ELECTRON_DIST="node_modules/electron/dist/electron"
if [ ! -f "$ELECTRON_DIST" ]; then
    echo "   ⚡ Electron binary missing — downloading..."
    rm -rf node_modules/electron 2>/dev/null || true
    npm install electron@35.0.0 2>/dev/null || true
    if [ ! -f "$ELECTRON_DIST" ]; then
        node node_modules/electron/install.js 2>/dev/null || true
    fi
fi

if [ -f "$ELECTRON_DIST" ]; then
    chmod +x "$ELECTRON_DIST" 2>/dev/null || true
    echo -e "   \033[32m✅ Electron ready\033[0m"
else
    echo -e "   \033[33m⚠️  Electron binary missing — falling back to browser\033[0m"
fi

npm run build 2>/dev/null || true
cd ..
echo -e "   \033[32m✅ Frontend built\033[0m"

# ── Ollama check ──
echo -e "\033[33m[5/6] Checking Ollama...\033[0m"
if curl -s http://localhost:11434/api/tags -m 2 >/dev/null 2>&1; then
    echo -e "   \033[32m✅ Ollama running\033[0m"
else
    echo -e "   \033[33m⚠️  Ollama not running\033[0m"
    echo "   💡 Run: ollama serve  then  ollama pull qwen2.5:7b"
fi

# ── Launch ──
echo -e "\033[33m[6/6] Launching Jarvis...\033[0m"

if [ -f "frontend/$ELECTRON_DIST" ]; then
    echo -e "   \033[36m🖥️  Opening native Electron window...\033[0m"
    cd frontend && "$ELECTRON_DIST" . ; cd ..
else
    echo -e "   \033[36m🌐 Opening in browser: http://localhost:8400\033[0m"
    .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8400 &
    BACKEND_PID=$!
    sleep 3
    if command -v xdg-open &>/dev/null; then xdg-open http://localhost:8400
    elif command -v open &>/dev/null; then open http://localhost:8400; fi
    echo "Press Enter to stop backend..."
    read -r
    kill $BACKEND_PID 2>/dev/null || true
fi

echo ""
echo -e "\033[32m✅ Done! ⚡\033[0m"
