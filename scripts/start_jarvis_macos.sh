#!/usr/bin/env bash
# Jarvis Desktop Assistant — Start (macOS)
# Usage: bash scripts/start_jarvis_macos.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
echo "⚡ Starting Jarvis Desktop Assistant..."

[ ! -d ".venv" ] && echo "❌ .venv not found. Run: bash scripts/setup_local_macos.sh" && exit 1
[ ! -d "frontend/node_modules" ] && echo "❌ Dependencies missing. Run: bash scripts/setup_local_macos.sh" && exit 1
[ ! -d "frontend/dist" ] && echo "📦 Building frontend..." && cd frontend && npm run build 2>&1 | tail -1 && cd ..

source .venv/bin/activate
echo "🚀 Launching..."
cd frontend
npx electron . 2>&1 &
cd "$PROJECT_DIR"
