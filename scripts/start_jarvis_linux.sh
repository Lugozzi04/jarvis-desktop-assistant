#!/usr/bin/env bash
# Jarvis Desktop Assistant — Start (Linux/macOS)
# Opens Jarvis as a desktop app. Backend auto-managed by Electron.
# Usage: bash scripts/start_jarvis_linux.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "⚡ Starting Jarvis Desktop Assistant..."

# Quick environment sanity
if [ ! -d ".venv" ]; then
  echo "❌ .venv not found. Run: bash scripts/setup_local_linux.sh"
  exit 1
fi

if [ ! -d "frontend/node_modules" ]; then
  echo "❌ frontend dependencies missing. Run: bash scripts/setup_local_linux.sh"
  exit 1
fi

if [ ! -d "frontend/dist" ]; then
  echo "📦 Building frontend (first time)..."
  cd frontend && npm run build 2>&1 | tail -1 && cd ..
fi

# Activate venv for any direct checks
source .venv/bin/activate

# Check if Electron is installed
if [ ! -d "frontend/node_modules/electron" ]; then
  echo "📦 Installing Electron..."
  cd frontend && npm install electron --save-optional 2>/dev/null || true
  cd ..
fi

echo "🚀 Launching Jarvis..."
cd frontend

# Use Electron directly if available, otherwise fall back to npm
if [ -f "node_modules/.bin/electron" ]; then
  npx electron . 2>&1 &
else
  echo "⚠️  Electron not installed. Starting in web mode..."
  echo ""
  echo "Backend: http://localhost:8400"
  echo "Frontend: http://localhost:5173"
  echo ""
  # Start backend
  cd "$PROJECT_DIR"
  .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8400 &
  BACKEND_PID=$!
  sleep 2
  # Start frontend
  cd frontend && npm run dev &
  FRONTEND_PID=$!
  echo "🌐 Open http://localhost:5173 in your browser"
  echo "Press Ctrl+C to stop."

  cleanup() {
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait
  }
  trap cleanup EXIT INT TERM
  wait
fi

cd "$PROJECT_DIR"
