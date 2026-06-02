#!/usr/bin/env python3
"""
check_ollama.py — Check Ollama status and available models.

Does NOT install or download anything. Just reports status.
Run this on your LOCAL PC to verify Ollama is set up correctly.

Usage:
    python scripts/check_ollama.py
    python scripts/check_ollama.py --url http://localhost:11434
    python scripts/check_ollama.py --model qwen2.5:7b
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

RECOMMENDED_MODEL = "qwen2.5:7b"
FALLBACK_MODELS = ["llama3.2:3b", "llama3.1:8b"]


def check_ollama(base_url: str) -> dict:
    """Check if Ollama is reachable and list models."""
    result = {
        "reachable": False,
        "base_url": base_url,
        "error": None,
        "models": [],
        "recommended_available": False,
        "any_model_available": False,
    }

    try:
        req = urllib.request.Request(
            f"{base_url}/api/tags",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            models = [m.get("name", "") for m in data.get("models", [])]
            result["reachable"] = True
            result["models"] = models
            result["any_model_available"] = len(models) > 0

            # Check for recommended model
            for model in models:
                if model == RECOMMENDED_MODEL or model.startswith(RECOMMENDED_MODEL.split(":")[0]):
                    result["recommended_available"] = True
                    result["recommended_model"] = model
                    break

    except urllib.error.URLError as e:
        result["error"] = f"Cannot connect to Ollama at {base_url}: {e.reason}"
    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Check Ollama status and available models"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--model",
        default=RECOMMENDED_MODEL,
        help=f"Model to check for (default: {RECOMMENDED_MODEL})",
    )
    args = parser.parse_args()

    target_model = args.model
    result = check_ollama(args.url.rstrip("/"))

    print("=" * 50)
    print("  JARVIS — Ollama Status Check")
    print("=" * 50)
    print()

    if not result["reachable"]:
        print(f"❌ Ollama is NOT reachable at {result['base_url']}")
        print(f"   Error: {result['error']}")
        print()
        print("To fix:")
        print("  1. Install Ollama: https://ollama.com/download")
        print("  2. Start Ollama: ollama serve")
        print("  3. Re-run this script")
        sys.exit(1)

    print(f"✅ Ollama is reachable at {result['base_url']}")
    print()

    if not result["models"]:
        print("⚠️  No models installed.")
        print()
        print("Pull the recommended model:")
        print(f"  ollama pull {target_model}")
        print()
        print("Or run the setup script:")
        print("  bash scripts/setup_ollama_linux.sh")
        sys.exit(1)

    print(f"Available models: {len(result['models'])}")
    for m in result["models"]:
        marker = ""
        if m == target_model or m.startswith(target_model.split(":")[0]):
            marker = " ✅ (recommended)"
        print(f"  - {m}{marker}")

    print()

    if result["recommended_available"]:
        print("✅ Recommended model is available!")
        print(f"   Model: {result.get('recommended_model', target_model)}")
        print()
        print("JARVIS is ready to use with Ollama.")
        print("Start the backend and frontend, then test connection.")
    else:
        print(f"⚠️  Recommended model '{target_model}' is not installed.")
        print()
        print("Pull it with:")
        print(f"  ollama pull {target_model}")
        print()
        print("Or pull a lighter alternative:")
        for fm in FALLBACK_MODELS:
            print(f"  ollama pull {fm}")

    print()
    print("=" * 50)


if __name__ == "__main__":
    main()
