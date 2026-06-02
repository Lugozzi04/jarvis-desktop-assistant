#!/usr/bin/env bash
# Jarvis Desktop Assistant — One-click Desktop Launcher (Linux/macOS)
# Usage: bash start.sh
# Opens a native Electron window — NOT a browser tab.

set -e
cd "$(dirname "$0")"

echo ""
echo -e "\033[36m╔══════════════════════════════════════╗\033[0m"
echo -e "\033[36m║   JARVIS Desktop Assistant v0.3.0   ║\033[0m"
echo -e "\033[36m╚══════════════════════════════════════╝\033[0m"
echo ""

# ── Step 1: Check Python ──
echo -e "\033[33m[1/4] Checking Python...\033[0m"
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
echo -e "\033[33m[2/4] Setting up Python environment...\033[0m"
if [ ! -d ".venv" ]; then
    $PY -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
    echo -e "   \033[32m✅ Virtual environment created\033[0m"
else
    echo -e "   \033[32m✅ .venv found\033[0m"
fi

# ── Step 3: Node.js + frontend + Electron ──
echo -e "\033[33m[3/4] Preparing frontend + Electron...\033[0m"
if ! command -v node &>/dev/null; then
    echo -e "   \033[31m❌ Node.js not found.\033[0m"
    echo "   Install: https://nodejs.org  or  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -"
    exit 1
fi

cd frontend

# Install deps (includes Electron)
if [ ! -d "node_modules" ]; then
    echo "   Installing dependencies..."
    npm install
fi

# Build frontend
if [ ! -d "dist" ] || [ "$(find dist -maxdepth 0 -mmin +60 2>/dev/null)" ]; then
    echo "   Building frontend..."
    npm run build
fi

cd ..

echo -e "   \033[32m✅ Frontend + Electron ready\033[0m"

# ── Step 4: Launch Electron Desktop App ──
echo -e "\033[33m[4/4] Launching Jarvis Desktop App...\033[0m"
echo -e "   ℹ️  The backend starts automatically in the background."
echo -e "   ℹ️  A native window will open — NOT a browser tab."
echo ""

cd frontend && npx electron . ; cd ..

echo ""
echo -e "\033[32m✅ Jarvis closed. See you next time! ⚡\033[0m"
