#!/usr/bin/env bash
# Jarvis Desktop Assistant — Setup (macOS)
# Same as Linux setup with macOS-specific notes.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=========================================="
echo "  ⚡ Jarvis Desktop Assistant — Setup (macOS)"
echo "=========================================="

echo "1️⃣  Checking Python..."
if command -v python3 &>/dev/null; then
  PYTHON=$(command -v python3)
  echo "   ✅ $($PYTHON --version)"
else
  echo "   ❌ Python 3 not found. Install: brew install python@3.11"
  exit 1
fi

echo "2️⃣  Checking Node.js..."
if command -v node &>/dev/null; then
  echo "   ✅ $(node --version)"
else
  echo "   ❌ Node.js not found. Install: brew install node"
  exit 1
fi

echo "3️⃣  Setting up venv..."
if [ ! -d ".venv" ]; then
  $PYTHON -m venv .venv
  echo "   ✅ Created"
else
  echo "   ✅ Already exists"
fi
source .venv/bin/activate

echo "4️⃣  Installing Python deps..."
pip install -q --upgrade pip && pip install -q -r requirements.txt
echo "   ✅ Done"

echo "5️⃣  Installing frontend deps..."
cd frontend && npm install --silent 2>/dev/null || npm install && cd ..
echo "   ✅ Done"

echo "6️⃣  Config..."
[ ! -f ".env" ] && cp .env.example .env && echo "   ✅ Created .env" || echo "   ✅ .env exists"

echo "7️⃣  Building frontend..."
cd frontend && npm run build 2>&1 | tail -1 && cd ..
echo "   ✅ Done"

echo ""
echo "=========================================="
echo "  ✅ Setup complete!"
echo ""
echo "  Optional:"
echo "    brew install ollama && ollama pull qwen2.5:7b"
echo "    ollama pull nomic-embed-text"
echo "    pip install faster-whisper"
echo ""
echo "  Start: bash scripts/start_jarvis_macos.sh"
echo "=========================================="
