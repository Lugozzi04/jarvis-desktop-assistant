#!/usr/bin/env bash
# setup_ollama_macos.sh — Install Ollama and pull the recommended model on macOS
# Run this on your LOCAL Mac, not on a VPS/server.
# Usage: bash scripts/setup_ollama_macos.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

RECOMMENDED_MODEL="${JARVIS_OLLAMA_MODEL:-qwen2.5:7b}"

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}   JARVIS — Ollama Setup (macOS)${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Step 1: Check if Homebrew is available (required for easy install)
echo -e "${YELLOW}[1/4] Checking prerequisites...${NC}"
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}⚠ Homebrew is not installed.${NC}"
    echo "Install it from: https://brew.sh"
    echo "Or install Ollama manually from: https://ollama.com/download/mac"
fi

# Step 2: Check if Ollama is installed
echo ""
echo -e "${YELLOW}[2/4] Checking Ollama installation...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓ Ollama is installed${NC}"
else
    echo -e "${YELLOW}⚠ Ollama is not installed.${NC}"
    if command -v brew &> /dev/null; then
        echo "Installing with Homebrew..."
        brew install ollama
        echo -e "${GREEN}✓ Ollama installed${NC}"
    else
        echo "Download from: https://ollama.com/download/mac"
        echo "After installation, re-run this script."
        exit 1
    fi
fi

# Step 3: Start Ollama and pull model
echo ""
echo -e "${YELLOW}[3/4] Starting Ollama and pulling model...${NC}"

# Check if running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Starting ollama serve..."
    ollama serve &
    sleep 3
fi

echo "Pulling ${RECOMMENDED_MODEL} (this may take a few minutes)..."
ollama pull "$RECOMMENDED_MODEL"
echo -e "${GREEN}✓ Model pulled: ${RECOMMENDED_MODEL}${NC}"

# Step 4: Verify
echo ""
echo -e "${YELLOW}[4/4] Verifying...${NC}"
ollama list

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}   ✓ Setup complete!${NC}"
echo -e "${GREEN}   Ollama running with ${RECOMMENDED_MODEL}${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Next: Set up .env, restart JARVIS, test connection in LLM Settings."
