#!/usr/bin/env bash
# setup_ollama_linux.sh — Install Ollama and pull the recommended model on Linux
# Run this on your LOCAL PC, not on a VPS/server.
# Usage: bash scripts/setup_ollama_linux.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

RECOMMENDED_MODEL="${JARVIS_OLLAMA_MODEL:-qwen2.5:7b}"

echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   JARVIS — Ollama Setup (Linux)         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check if Ollama is installed
echo -e "${YELLOW}[1/4] Checking Ollama installation...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓ Ollama is installed${NC}"
    ollama --version 2>/dev/null || true
else
    echo -e "${YELLOW}⚠ Ollama is not installed.${NC}"
    echo ""
    echo "Install Ollama with:"
    echo "  curl -fsSL https://ollama.com/install.sh | sh"
    echo ""
    echo "Or visit: https://ollama.com/download/linux"
    echo ""
    read -rp "Do you want to install Ollama now? [y/N] " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        echo "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        echo -e "${GREEN}✓ Ollama installed${NC}"
    else
        echo "Skipping installation. Exiting."
        exit 1
    fi
fi

# Step 2: Check if Ollama service is running
echo ""
echo -e "${YELLOW}[2/4] Checking Ollama service...${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama service is running${NC}"
else
    echo -e "${YELLOW}⚠ Ollama service is not responding.${NC}"
    echo "Start it with: ollama serve"
    echo "Starting ollama serve in background..."
    ollama serve &
    sleep 3
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama service started${NC}"
    else
        echo -e "${RED}✗ Could not start Ollama. Check manually.${NC}"
        exit 1
    fi
fi

# Step 3: Pull recommended model
echo ""
echo -e "${YELLOW}[3/4] Pulling recommended model: ${RECOMMENDED_MODEL}${NC}"
echo "This may take a few minutes (~4.7 GB)..."
ollama pull "$RECOMMENDED_MODEL"
echo -e "${GREEN}✓ Model pulled: ${RECOMMENDED_MODEL}${NC}"

# Step 4: Verify
echo ""
echo -e "${YELLOW}[4/4] Verifying...${NC}"
echo "Available models:"
ollama list

if ollama list | grep -q "${RECOMMENDED_MODEL}"; then
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✓ Setup complete!                      ║${NC}"
    echo -e "${GREEN}║   Ollama is running with ${RECOMMENDED_MODEL}${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Ensure your .env file has:"
    echo "     LLM_DEFAULT_PROVIDER=ollama"
    echo "     LLM_DEFAULT_MODEL=${RECOMMENDED_MODEL}"
    echo "  2. Start JARVIS backend"
    echo "  3. Open the LLM Settings page and click 'Test Connection'"
else
    echo -e "${RED}✗ Model not found after pull. Something went wrong.${NC}"
fi
