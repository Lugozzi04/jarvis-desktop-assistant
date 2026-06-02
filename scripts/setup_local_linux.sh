#!/usr/bin/env bash
# Jarvis Desktop Assistant — Local Setup (Linux/macOS)
# Installs all dependencies. Does NOT install Ollama or download models.
# Usage: bash scripts/setup_local_linux.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=========================================="
echo "  ⚡ Jarvis Desktop Assistant — Setup"
echo "=========================================="
echo ""

# ── Check Python ──
echo "1️⃣  Checking Python..."
if command -v python3 &>/dev/null; then
  PYTHON=$(command -v python3)
  echo "   ✅ Python found: $($PYTHON --version)"
else
  echo "   ❌ Python 3 not found. Install Python 3.10+"
  echo "   Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
  echo "   Fedora: sudo dnf install python3"
  echo "   macOS: brew install python@3.11"
  exit 1
fi

# ── Check Node ──
echo "2️⃣  Checking Node.js..."
if command -v node &>/dev/null; then
  echo "   ✅ Node.js found: $(node --version)"
else
  echo "   ❌ Node.js not found. Install Node 18+"
  echo "   https://nodejs.org/ or use nvm"
  exit 1
fi

# ── Create venv ──
echo "3️⃣  Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
  $PYTHON -m venv .venv
  echo "   ✅ Created .venv"
else
  echo "   ✅ .venv already exists"
fi

source .venv/bin/activate

# ── Install Python deps ──
echo "4️⃣  Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "   ✅ Python dependencies installed"

# ── Install Node deps ──
echo "5️⃣  Installing frontend dependencies..."
cd frontend
npm install --silent 2>/dev/null || npm install
cd ..
echo "   ✅ Frontend dependencies installed"

# ── Create .env ──
echo "6️⃣  Setting up configuration..."
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "   ✅ Created .env from .env.example"
else
  echo "   ✅ .env already exists"
fi

# ── Build frontend ──
echo "7️⃣  Building frontend..."
cd frontend && npm run build 2>&1 | tail -1
cd ..
echo "   ✅ Frontend built"

# ── Optional: Ollama ──
echo ""
echo "=========================================="
echo "  ✅ Setup complete!"
echo ""
echo "  Optional — install Ollama for AI features:"
echo "    curl -fsSL https://ollama.com/install.sh | sh"
echo "    ollama pull qwen2.5:7b"
echo "    ollama pull nomic-embed-text"
echo ""
echo "  Optional — voice setup:"
echo "    pip install faster-whisper"
echo ""
echo "  Start Jarvis:"
echo "    bash scripts/start_jarvis_linux.sh"
echo "=========================================="
