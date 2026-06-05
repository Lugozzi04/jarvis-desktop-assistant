"""Models API — list installed Ollama models, recommendations, and dynamic switching."""

from __future__ import annotations

import requests
from fastapi import APIRouter

from backend.core.logger import logger

router = APIRouter(tags=["models"])

# ── Recommended models ──

RECOMMENDED_MODELS = [
    {
        "name": "mistral:7b",
        "display": "Mistral 7B",
        "size_gb": 4.1,
        "category": "fast",
        "description": "Miglior compromesso — veloce, ottimo italiano, 4 GB",
        "speed": "⚡⚡⚡⚡",
        "quality": "⭐⭐⭐⭐",
        "recommended": True,
        "reason": "Ideale per uso quotidiano",
    },
    {
        "name": "qwen2.5:7b",
        "display": "Qwen 2.5 7B",
        "size_gb": 4.4,
        "category": "fast",
        "description": "Veloce, multilingua, 4.4 GB — già installato",
        "speed": "⚡⚡⚡⚡⚡",
        "quality": "⭐⭐",
        "recommended": False,
        "reason": "Buono per test veloci, italiano OK",
    },
    {
        "name": "llama3.1:8b",
        "display": "Llama 3.1 8B",
        "size_gb": 4.9,
        "category": "balanced",
        "description": "Meta — bilanciato, buona cultura generale, 5 GB",
        "speed": "⚡⚡⚡",
        "quality": "⭐⭐⭐",
        "recommended": True,
        "reason": "Solido tuttofare",
    },
    {
        "name": "gemma2:9b",
        "display": "Gemma 2 9B",
        "size_gb": 5.5,
        "category": "balanced",
        "description": "Google — compatto ma potente, 5.5 GB",
        "speed": "⚡⚡⚡",
        "quality": "⭐⭐⭐",
        "recommended": False,
        "reason": "Alternativa Google a Llama",
    },
    {
        "name": "deepseek-r1:8b",
        "display": "DeepSeek R1 8B",
        "size_gb": 4.9,
        "category": "reasoning",
        "description": "🧠 RAGIONAMENTO — pensa prima di rispondere, 5 GB",
        "speed": "⚡",
        "quality": "⭐⭐⭐⭐⭐",
        "recommended": True,
        "reason": "Il più intelligente — per domande complesse",
    },
    {
        "name": "qwen2.5:14b",
        "display": "Qwen 2.5 14B",
        "size_gb": 8.5,
        "category": "smart",
        "description": "14B parametri — risposte ricche e dettagliate, 8.5 GB",
        "speed": "⚡⚡",
        "quality": "⭐⭐⭐⭐",
        "recommended": True,
        "reason": "Ottima qualità senza esagerare",
    },
    {
        "name": "deepseek-r1:14b",
        "display": "DeepSeek R1 14B",
        "size_gb": 8.9,
        "category": "reasoning",
        "description": "🧠 RAGIONAMENTO potente — 14B, risposte approfondite, 9 GB",
        "speed": "⚡",
        "quality": "⭐⭐⭐⭐⭐",
        "recommended": False,
        "reason": "Ragionamento top, per analisi profonde",
    },
    {
        "name": "phi4:14b",
        "display": "Phi-4 14B",
        "size_gb": 8.4,
        "category": "smart",
        "description": "Microsoft — eccellente per coding e logica, 8.4 GB",
        "speed": "⚡⚡",
        "quality": "⭐⭐⭐⭐",
        "recommended": False,
        "reason": "Perfetto per codice e ragionamento logico",
    },
    {
        "name": "qwen2.5:32b",
        "display": "Qwen 2.5 32B",
        "size_gb": 19.5,
        "category": "heavy",
        "description": "32B parametri — qualità quasi GPT-4, 19.5 GB",
        "speed": "⚡",
        "quality": "⭐⭐⭐⭐⭐",
        "recommended": False,
        "reason": "Qualità eccelsa — solo se hai RAM",
    },
    {
        "name": "llama3.1:70b",
        "display": "Llama 3.1 70B",
        "size_gb": 40,
        "category": "heavy",
        "description": "70B parametri — qualità GPT-4 level, 40 GB",
        "speed": "⚡",
        "quality": "⭐⭐⭐⭐⭐",
        "recommended": False,
        "reason": "Il top assoluto — richiede 64 GB RAM",
    },
]

CATEGORIES = {
    "fast": {"label": "⚡ Veloci", "order": 0},
    "balanced": {"label": "⚖️ Bilanciati", "order": 1},
    "smart": {"label": "🧠 Intelligenti", "order": 2},
    "reasoning": {"label": "💭 Ragionamento", "order": 3},
    "heavy": {"label": "🏋️ Pesanti", "order": 4},
}


# ── Ollama API ──

def _get_ollama_tags() -> list[str]:
    """Get list of installed models from Ollama."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code == 200:
            models = r.json().get("models", [])
            return [m["name"] for m in models]
    except Exception:
        pass
    return []


def _ollama_running() -> bool:
    """Check if Ollama is running."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


# ── API Routes ──

@router.get("/models")
def list_models():
    """List all available models — installed + recommended.

    Returns models grouped by category, with:
    - name, display, size_gb, description
    - installed: true/false
    - recommended: true/false
    - download_command: ollama pull <name>
    """
    ollama_running = _ollama_running()
    installed = _get_ollama_tags() if ollama_running else []
    installed_set = set(installed)

    # Build model list
    models_by_category: dict[str, list] = {}
    for cat_key in CATEGORIES:
        models_by_category[cat_key] = []

    for rec in RECOMMENDED_MODELS:
        cat = rec["category"]
        entry = {
            **rec,
            "installed": rec["name"] in installed_set,
            "download_command": f"ollama pull {rec['name']}",
        }
        models_by_category[cat].append(entry)

    # Add any installed models not in recommendations
    for name in installed:
        found = any(r["name"] == name for r in RECOMMENDED_MODELS)
        if not found:
            models_by_category.setdefault("other", []).append({
                "name": name,
                "display": name,
                "size_gb": 0,
                "category": "other",
                "description": "",
                "speed": "?",
                "quality": "?",
                "recommended": False,
                "installed": True,
                "download_command": f"ollama pull {name}",
                "reason": "",
            })

    if "other" not in models_by_category:
        models_by_category["other"] = []

    # Sort categories
    sorted_cats = sorted(
        models_by_category.items(),
        key=lambda x: CATEGORIES.get(x[0], {"order": 99})["order"],
    )

    return {
        "ollama_running": ollama_running,
        "installed_count": len(installed),
        "total_recommended": len(RECOMMENDED_MODELS),
        "categories": [
            {
                "key": cat_key,
                "label": CATEGORIES.get(cat_key, {"label": cat_key})["label"],
                "models": models,
            }
            for cat_key, models in sorted_cats
        ],
    }


@router.post("/models/download")
def download_model(name: str):
    """Trigger a model download via Ollama (non-blocking notice).

    Returns the command to run — actual download must be done by user in terminal
    since it can take several minutes.
    """
    return {
        "command": f"ollama pull {name}",
        "note": "Run this in your terminal. Download can take 5-20 minutes depending on model size.",
    }
