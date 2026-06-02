#!/usr/bin/env bash
# Jarvis Desktop Assistant — Dev Start (macOS)
# Starts backend + frontend in dev mode.
# Usage: bash scripts/dev_start_macos.sh

# Same as Linux, but with macOS-specific notes
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=========================================="
echo "  ⚡ Jarvis Desktop Assistant — Dev Start"
echo "=========================================="

# Check Python venv
if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# Install backend deps
echo "Installing backend dependencies..."
pip install -q -r requirements.txt

# Copy .env if missing
if [ ! -f ".env" ]; then
  echo "Creating .env from .env.example..."
  cp .env.example .env
  echo "⚠️  Edit .env with your settings if needed."
fi

# Check frontend node_modules
if [ ! -d "frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  cd frontend && npm install && cd ..
fi

# Start backend
echo ""
echo "Starting backend on http://localhost:8400 ..."
uvicorn backend.main:app --host 127.0.0.1 --port 8400 --reload &
BACKEND_PID=$!
sleep 2

# Start frontend
echo "Starting frontend on http://localhost:5173 ..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "  ✅ Jarvis is running!"
echo ""
echo "  Backend:  http://localhost:8400"
echo "  Frontend: http://localhost:5173"
echo "  API Docs: http://localhost:8400/docs"
echo ""
echo "  Desktop mode: npm run desktop:dev  (requires Electron)"
echo "  Press Ctrl+C to stop both servers."
echo "=========================================="

cleanup() {
  echo ""
  echo "Shutting down..."
  kill $BACKEND_PID 2>/dev/null
  kill $FRONTEND_PID 2>/dev/null
  wait
  echo "👋 Jarvis stopped."
}
trap cleanup EXIT INT TERM

wait
