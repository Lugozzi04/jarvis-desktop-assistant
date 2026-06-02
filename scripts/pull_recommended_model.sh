#!/usr/bin/env bash
# pull_recommended_model.sh — Pull only the recommended model
# Does NOT install Ollama — assumes it's already installed.
# Run this on your LOCAL PC.
# Usage: bash scripts/pull_recommended_model.sh [model_name]

set -euo pipefail

MODEL="${1:-qwen2.5:7b}"

echo "Pulling model: ${MODEL}"
echo "This may take a few minutes..."

if ! command -v ollama &> /dev/null; then
    echo "ERROR: ollama is not installed."
    echo "Install from: https://ollama.com/download"
    echo "Or run: bash scripts/setup_ollama_linux.sh"
    exit 1
fi

# Pull the model
ollama pull "$MODEL"

echo ""
echo "✓ Model pulled successfully: ${MODEL}"
echo ""
echo "Verify with: ollama list"
ollama list
