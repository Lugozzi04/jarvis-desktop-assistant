#!/usr/bin/env bash
# Jarvis Desktop Assistant — One-Click Launcher (Linux/macOS)
# Usage: bash start.sh
# NO npm, NO Electron, NO browser. Just Python + native webview.

set -e
cd "$(dirname "$0")"

echo ""
echo -e "\033[36m╔══════════════════════════════════════╗\033[0m"
echo -e "\033[36m║  JARVIS Desktop Assistant v0.3.0    ║\033[0m"
echo -e "\033[36m╚══════════════════════════════════════╝\033[0m"
echo ""

# ── Step 1: Git pull ──
echo -e "\033[33m[1/5] Updating code...\033[0m"
if [ -d ".git" ]; then
    git fetch origin 2>/dev/null
    git checkout main 2>/dev/null || true
    git reset --hard origin/main 2>/dev/null
    git clean -fd 2>/dev/null || true
    echo -e "   \033[32m✅ Code up to date\033[0m"
else
    echo -e "   \033[33m⚠️  Not a git repo — skipping pull\033[0m"
fi

# ── Step 2: Check Python ──
echo -e "\033[33m[2/5] Checking Python...\033[0m"
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo -e "\033[31m❌ Python not found.\033[0m"
    exit 1
fi
echo -e "   \033[32m✅ $PY\033[0m"

# ── Step 3: Setup venv + deps ──
echo -e "\033[33m[3/5] Installing dependencies...\033[0m"
if [ ! -d ".venv" ]; then
    $PY -m venv .venv
fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
echo -e "   \033[32m✅ Dependencies up to date\033[0m"

# ── Step 4: Build Frontend ──
echo -e "\033[33m[4/5] Building frontend...\033[0m"
if command -v npm &>/dev/null; then
    if [ -f "frontend/package.json" ]; then
        # Install frontend deps if needed
        if [ ! -d "frontend/node_modules" ]; then
            echo "   📦 Installing frontend deps..."
            (cd frontend && npm install --silent)
        fi
        # Build
        (cd frontend && npm run build) && echo -e "   \033[32m✅ Frontend built\033[0m" || echo -e "   \033[33m⚠️  Build failed — using existing build\033[0m"
    else
        echo -e "   \033[33m⚠️  No frontend/package.json\033[0m"
    fi
else
    echo -e "   \033[33m⚠️  npm not found — skipping build\033[0m"
    if [ ! -f "frontend/dist/index.html" ]; then
        echo -e "   \033[31m❌ No pre-built frontend. Install Node.js.\033[0m"
    fi
fi

# ── Step 5: Launch Desktop App ──
echo -e "\033[33m[5/5] Launching Jarvis...\033[0m"
echo -e "   🖥️  Opening native window — close it to exit."

# Check Ollama
if curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo -e "   \033[32m🤖 Ollama connected\033[0m"
else
    echo -e "   \033[33m💡 Run: ollama pull qwen2.5:7b  (for LLM chat)\033[0m"
fi

# Check Voice
echo -e "   🎤 Checking voice..."
if .venv/bin/python -c "import faster_whisper; print('ok')" 2>/dev/null | grep -q ok; then
    echo -e "   \033[32m🎤 faster-whisper ready — speech-to-text enabled\033[0m"
else
    echo -e "   \033[33m💡 Voice STT not available (auto-installed next run)\033[0m"
fi

echo ""
.venv/bin/python -m backend.desktop

echo ""
echo -e "\033[32m✅ Jarvis closed. See you next time! ⚡\033[0m"
