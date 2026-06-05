"""Models API — list installed Ollama models, recommendations by PC tier, and dynamic switching."""

from __future__ import annotations

import requests
from fastapi import APIRouter

from backend.core.logger import logger

router = APIRouter(tags=["models"])

# ── PC Tiers ──

TIERS = {
    "buon_pc": {"label": "💻 Buon PC (8-16 GB RAM)", "order": 0, "max_ram_gb": 16},
    "pc_medio": {"label": "🖥️ PC Medio (16-32 GB RAM)", "order": 1, "max_ram_gb": 32},
    "pc_potente": {"label": "🚀 PC Potente (32+ GB RAM)", "order": 2, "max_ram_gb": 999},
}

# ── Recommended models — each assigned to a tier ──

RECOMMENDED_MODELS = [
    # ── Buon PC (8-16 GB RAM) ──
    {
        "name": "mistral:7b",
        "display": "Mistral 7B",
        "size_gb": 4.1,
        "category": "fast",
        "description": "Miglior compromesso — veloce, ottimo italiano, 4 GB",
        "speed": "⚡⚡⚡⚡",
        "quality": "⭐⭐⭐⭐",
        "tier": "buon_pc",
        "recommended": True,
        "reason": "Ideale per uso quotidiano",
        "tier_badge": "⭐ Miglior Compromesso",
    },
    {
        "name": "llama3.1:8b",
        "display": "Llama 3.1 8B",
        "size_gb": 4.9,
        "category": "balanced",
        "description": "Meta — bilanciato, buona cultura generale, 5 GB",
        "speed": "⚡⚡⚡",
        "quality": "⭐⭐⭐",
        "tier": "buon_pc",
        "recommended": True,
        "reason": "Solido tuttofare",
        "tier_badge": "",
    },
    {
        "name": "qwen2.5:7b",
        "display": "Qwen 2.5 7B",
        "size_gb": 4.4,
        "category": "fast",
        "description": "Veloce, multilingua, 4.4 GB",
        "speed": "⚡⚡⚡⚡⚡",
        "quality": "⭐⭐",
        "tier": "buon_pc",
        "recommended": False,
        "reason": "Buono per test veloci, italiano OK",
        "tier_badge": "",
    },

    # ── PC Medio (16-32 GB RAM) ──
    {
        "name": "deepseek-r1:8b",
        "display": "DeepSeek R1 8B",
        "size_gb": 4.9,
        "category": "reasoning",
        "description": "🧠 RAGIONAMENTO — pensa prima di rispondere, 5 GB",
        "speed": "⚡",
        "quality": "⭐⭐⭐⭐⭐",
        "tier": "pc_medio",
        "recommended": True,
        "reason": "Il più intelligente — per domande complesse",
        "tier_badge": "⭐ Consigliato",
    },
    {
        "name": "qwen2.5:14b",
        "display": "Qwen 2.5 14B",
        "size_gb": 8.5,
        "category": "smart",
        "description": "14B parametri — risposte ricche e dettagliate, 8.5 GB",
        "speed": "⚡⚡",
        "quality": "⭐⭐⭐⭐",
        "tier": "pc_medio",
        "recommended": True,
        "reason": "Ottima qualità senza esagerare",
        "tier_badge": "⭐ Qualità Premium",
    },
    {
        "name": "phi4:14b",
        "display": "Phi-4 14B",
        "size_gb": 8.4,
        "category": "smart",
        "description": "Microsoft — eccellente per coding e logica, 8.4 GB",
        "speed": "⚡⚡",
        "quality": "⭐⭐⭐⭐",
        "tier": "pc_medio",
        "recommended": False,
        "reason": "Perfetto per codice e ragionamento logico",
        "tier_badge": "",
    },
    {
        "name": "deepseek-r1:14b",
        "display": "DeepSeek R1 14B",
        "size_gb": 8.9,
        "category": "reasoning",
        "description": "🧠 RAGIONAMENTO potente — 14B, risposte approfondite, 9 GB",
        "speed": "⚡",
        "quality": "⭐⭐⭐⭐⭐",
        "tier": "pc_medio",
        "recommended": False,
        "reason": "Ragionamento top, per analisi profonde",
        "tier_badge": "",
    },
    {
        "name": "gemma2:9b",
        "display": "Gemma 2 9B",
        "size_gb": 5.5,
        "category": "balanced",
        "description": "Google — compatto ma potente, 5.5 GB",
        "speed": "⚡⚡⚡",
        "quality": "⭐⭐⭐",
        "tier": "pc_medio",
        "recommended": False,
        "reason": "Alternativa Google a Llama",
        "tier_badge": "",
    },

    # ── PC Potente (32+ GB RAM) ──
    {
        "name": "qwen2.5:32b",
        "display": "Qwen 2.5 32B",
        "size_gb": 19.5,
        "category": "heavy",
        "description": "32B parametri — qualità quasi GPT-4, 19.5 GB",
        "speed": "⚡",
        "quality": "⭐⭐⭐⭐⭐",
        "tier": "pc_potente",
        "recommended": True,
        "reason": "Qualità eccelsa — solo se hai RAM",
        "tier_badge": "⭐ Qualità Massima",
    },
    {
        "name": "llama3.1:70b",
        "display": "Llama 3.1 70B",
        "size_gb": 40,
        "category": "heavy",
        "description": "70B parametri — qualità GPT-4 level, 40 GB",
        "speed": "⚡",
        "quality": "⭐⭐⭐⭐⭐",
        "tier": "pc_potente",
        "recommended": False,
        "reason": "Il top assoluto — richiede 64 GB RAM",
        "tier_badge": "",
    },
]

# Old categories for backward compatibility (collapsed into tiers now)
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
    """List all available models — installed + recommended by PC tier.

    Returns models grouped by PC tier with:
    - name, display, size_gb, description
    - installed: true/false
    - recommended: true/false
    - tier_badge: special label for top picks
    - download_command: ollama pull <name>
    """
    ollama_running = _ollama_running()
    installed = _get_ollama_tags() if ollama_running else []
    installed_set = set(installed)

    # Build model list by tier
    models_by_tier: dict[str, list] = {}
    for tier_key in TIERS:
        models_by_tier[tier_key] = []

    for rec in RECOMMENDED_MODELS:
        tier = rec.get("tier", "buon_pc")
        if tier not in models_by_tier:
            models_by_tier[tier] = []
        entry = {
            **rec,
            "installed": rec["name"] in installed_set,
            "download_command": f"ollama pull {rec['name']}",
        }
        models_by_tier[tier].append(entry)

    # Add any installed models not in recommendations (goes in "other" tier)
    for name in installed:
        found = any(r["name"] == name for r in RECOMMENDED_MODELS)
        if not found:
            models_by_tier.setdefault("other", []).append({
                "name": name,
                "display": name,
                "size_gb": 0,
                "category": "other",
                "description": "",
                "speed": "?",
                "quality": "?",
                "tier": "other",
                "recommended": False,
                "installed": True,
                "download_command": f"ollama pull {name}",
                "reason": "",
                "tier_badge": "",
            })

    if "other" not in models_by_tier:
        models_by_tier["other"] = []

    # Sort tiers by order
    sorted_tiers = sorted(
        [(k, v) for k, v in models_by_tier.items() if k != "other"],
        key=lambda x: TIERS.get(x[0], {"order": 99})["order"],
    )
    # "other" always last
    if models_by_tier.get("other"):
        sorted_tiers.append(("other", models_by_tier["other"]))

    # Count installed per tier
    installed_by_tier = {}
    for tier_key, models in sorted_tiers:
        installed_by_tier[tier_key] = sum(1 for m in models if m["installed"])

    return {
        "ollama_running": ollama_running,
        "installed_count": len(installed),
        "total_recommended": len(RECOMMENDED_MODELS),
        "tiers": [
            {
                "key": tier_key if tier_key != "other" else tier_key,
                "label": TIERS.get(tier_key, {"label": "🔧 Altri modelli"})["label"],
                "max_ram_gb": TIERS.get(tier_key, {"max_ram_gb": 0})["max_ram_gb"],
                "models": models,
                "installed_count": installed_by_tier.get(tier_key, 0),
            }
            for tier_key, models in sorted_tiers
        ],
        # Backward compat: also return categories
        "categories": [],  # deprecated, use tiers now
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
