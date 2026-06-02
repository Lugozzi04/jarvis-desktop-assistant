#!/usr/bin/env pwsh
# setup_ollama_windows.ps1 — Install Ollama and pull the recommended model on Windows
# Run this on your LOCAL PC, not on a VPS/server.
# Usage: .\scripts\setup_ollama_windows.ps1

$ErrorActionPreference = "Stop"

$RecommendedModel = if ($env:JARVIS_OLLAMA_MODEL) { $env:JARVIS_OLLAMA_MODEL } else { "qwen2.5:7b" }

Write-Host "=========================================" -ForegroundColor Blue
Write-Host "   JARVIS — Ollama Setup (Windows)" -ForegroundColor Blue
Write-Host "=========================================" -ForegroundColor Blue
Write-Host ""

# Step 1: Check if Ollama is installed
Write-Host "[1/4] Checking Ollama installation..." -ForegroundColor Yellow
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaPath) {
    Write-Host "✓ Ollama is installed at: $($ollamaPath.Source)" -ForegroundColor Green
} else {
    Write-Host "⚠ Ollama is not installed." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Download and install Ollama from:" -ForegroundColor White
    Write-Host "  https://ollama.com/download/windows" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "After installation, re-run this script." -ForegroundColor Yellow
    exit 1
}

# Step 2: Check if Ollama service is running
Write-Host ""
Write-Host "[2/4] Checking Ollama service..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✓ Ollama service is running" -ForegroundColor Green
} catch {
    Write-Host "⚠ Ollama service is not responding at http://localhost:11434" -ForegroundColor Yellow
    Write-Host "Make sure Ollama is launched from the Start Menu." -ForegroundColor White
    Write-Host ""
    Write-Host "Waiting for you to start Ollama... (check your system tray)" -ForegroundColor Yellow
    Write-Host "Press Enter once Ollama is running..."
    Read-Host
}

# Step 3: Pull recommended model
Write-Host ""
Write-Host "[3/4] Pulling recommended model: $RecommendedModel" -ForegroundColor Yellow
Write-Host "This may take a few minutes (~4.7 GB)..." -ForegroundColor White
ollama pull $RecommendedModel
Write-Host "✓ Model pulled: $RecommendedModel" -ForegroundColor Green

# Step 4: Verify
Write-Host ""
Write-Host "[4/4] Verifying..." -ForegroundColor Yellow
Write-Host "Available models:"
ollama list

$modelList = ollama list
if ($modelList -match $RecommendedModel) {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "   ✓ Setup complete!" -ForegroundColor Green
    Write-Host "   Ollama is running with $RecommendedModel" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Ensure your .env file has:"
    Write-Host "     LLM_DEFAULT_PROVIDER=ollama"
    Write-Host "     LLM_DEFAULT_MODEL=$RecommendedModel"
    Write-Host "  2. Start JARVIS backend"
    Write-Host "  3. Open the LLM Settings page and click 'Test Connection'"
} else {
    Write-Host "✗ Model not found after pull. Something went wrong." -ForegroundColor Red
}
