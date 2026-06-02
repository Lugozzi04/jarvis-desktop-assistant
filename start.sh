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
echo -e "\033[33m[1/4] Updating code...\033[0m"
if [ -d ".git" ]; then
    git stash push -m "auto-stash by start.sh" 2>/dev/null || true
    git pull --ff-only 2>/dev/null || true
    git stash pop 2>/dev/null || true
    echo -e "   \033[32m✅ Code up to date\033[0m"
else
    echo -e "   \033[33m⚠️  Not a git repo — skipping pull\033[0m"
fi

# ── Step 2: Check Python ──
echo -e "\033[33m[2/4] Checking Python...\033[0m"
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
echo -e "\033[33m[3/4] Installing dependencies...\033[0m"
if [ ! -d ".venv" ]; then
    $PY -m venv .venv
fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
echo -e "   \033[32m✅ Dependencies up to date\033[0m"

# ── Step 4: Launch Desktop App ──
echo -e "\033[33m[4/4] Launching Jarvis...\033[0m"
echo -e "   🖥️  Opening native window — close it to exit."

# Check Ollama
if curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo -e "   \033[32m🤖 Ollama connected\033[0m"
else
    echo -e "   \033[33m💡 Run: ollama pull qwen2.5:7b  (for LLM chat)\033[0m"
fi

echo ""
.venv/bin/python -m backend.desktop

echo ""
echo -e "\033[32m✅ Jarvis closed. See you next time! ⚡\033[0m"
