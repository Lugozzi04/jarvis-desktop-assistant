#!/usr/bin/env bash
# Jarvis — One-click launcher (Linux/macOS)
# Usage: bash start.sh
# Does everything: check deps → install → build → start backend → open browser

set -e
cd "$(dirname "$0")"

echo ""
echo -e "\033[36m╔══════════════════════════════════════╗\033[0m"
echo -e "\033[36m║        JARVIS Desktop Assistant      ║\033[0m"
echo -e "\033[36m╚══════════════════════════════════════╝\033[0m"
echo ""

# ── Step 1: Check Python ──
echo -e "\033[33m[1/5] Checking Python...\033[0m"
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo -e "\033[31m❌ Python not found. Install from https://python.org\033[0m"
    exit 1
fi
echo -e "   \033[32m✅ $PY\033[0m"

# ── Step 2: Setup venv ──
echo -e "\033[33m[2/5] Setting up Python environment...\033[0m"
if [ ! -d ".venv" ]; then
    $PY -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
    echo -e "   \033[32m✅ Virtual environment created\033[0m"
else
    echo -e "   \033[32m✅ .venv found\033[0m"
fi

# ── Step 3: Node.js & frontend ──
echo -e "\033[33m[3/5] Checking Node.js...\033[0m"
if ! command -v node &>/dev/null; then
    echo -e "   \033[33m⚠️  Node.js not found — API-only mode\033[0m"
else
    if [ ! -d "frontend/node_modules" ]; then
        echo "   Installing frontend dependencies..."
        cd frontend && npm install && cd ..
    fi
    if [ ! -d "frontend/dist" ]; then
        echo "   Building frontend..."
        cd frontend && npm run build && cd ..
    fi
    echo -e "   \033[32m✅ Frontend ready\033[0m"
fi

# ── Step 4: Start backend ──
echo -e "\033[33m[4/5] Starting backend on http://localhost:8400 ...\033[0m"
echo "   Press Ctrl+C to stop"
echo ""

.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8400 &
BACKEND_PID=$!
sleep 3

# ── Step 5: Open browser ──
echo -e "\033[33m[5/5] Opening Jarvis...\033[0m"
if command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:8400
elif command -v open &>/dev/null; then
    open http://localhost:8400
fi

echo ""
echo -e "\033[32m✅ Jarvis is running!\033[0m"
echo -e "   Backend: \033[36mhttp://localhost:8400\033[0m"
echo "   Press Ctrl+C to stop"
echo ""

wait $BACKEND_PID
