"""Setup Wizard state management for Jarvis Desktop Assistant.

Tracks first-run wizard completion and individual component readiness.
Stores state in a JSON file (simple, no DB dependency at setup time).
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.logger import logger

STATE_FILE = Path(settings.data_dir) / "setup_state.json"


class SetupStatus(BaseModel):
    first_run: bool = True
    completed: bool = False
    completed_at: str | None = None
    llm_ready: bool = False
    llm_provider: str = "none"
    documents_ready: bool = False
    documents_provider: str = "none"
    voice_ready: bool = False
    voice_provider: str = "none"
    integrations_configured: dict[str, bool] = Field(default_factory=lambda: {
        "obs": False, "discord": False, "spotify": False, "github": False,
    })
    security_reviewed: bool = False
    desktop_ready: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class SetupState:
    """Manages setup wizard state with file persistence."""

    def __init__(self):
        self._state: SetupStatus | None = None

    def _ensure_loaded(self):
        if self._state is not None:
            return
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                self._state = SetupStatus(**data)
            except Exception as e:
                logger.warning("Could not load setup state: {}", e)
                self._state = SetupStatus()
        else:
            self._state = SetupStatus()

    def _save(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(self._state.model_dump_json(indent=2))

    def get_status(self) -> SetupStatus:
        self._ensure_loaded()
        # Refresh dynamic fields
        self._refresh_dynamic()
        return self._state

    def _refresh_dynamic(self):
        """Update dynamic readiness fields based on current system state."""
        # LLM status
        try:
            from backend.llm.gateway import llm_gateway
            self._state.llm_ready = llm_gateway._providers and any(
                p.available for p in llm_gateway._providers.values()
            )
            active = llm_gateway.get_active_provider()
            self._state.llm_provider = active.name if active else "none"
        except Exception:
            pass

        # Documents status
        try:
            from backend.memory.vector_store import get_vector_store
            store = get_vector_store()
            s = store.get_status()
            self._state.documents_ready = s.get("documents", 0) > 0
            from backend.memory.embeddings import get_embedding_provider
            self._state.documents_provider = get_embedding_provider().name
        except Exception:
            pass

        # Voice status
        try:
            from backend.voice.gateway import voice_gateway
            self._state.voice_ready = voice_gateway.stt_available and voice_gateway.tts_available
            self._state.voice_provider = f"stt={voice_gateway.stt_provider or 'none'},tts={voice_gateway.tts_provider or 'none'}"
        except Exception:
            pass

        # Desktop ready
        self._state.desktop_ready = True  # Always true if backend is running

        # Recommendations
        steps = []
        if not self._state.llm_ready:
            steps.append("ollama_pull_model")
        if not self._state.documents_ready:
            steps.append("index_documents")
        if not self._state.voice_ready:
            steps.append("setup_voice")
        if self._state.first_run:
            steps.append("run_setup_wizard")
        self._state.recommended_next_steps = steps

    def mark_completed(self):
        self._ensure_loaded()
        self._state.first_run = False
        self._state.completed = True
        self._state.completed_at = datetime.utcnow().isoformat()
        self._save()
        logger.info("Setup wizard marked as completed")

    def mark_component(self, component: str, ready: bool = True):
        self._ensure_loaded()
        if component == "llm":
            self._state.llm_ready = ready
        elif component == "documents":
            self._state.documents_ready = ready
        elif component == "voice":
            self._state.voice_ready = ready
        elif component == "security":
            self._state.security_reviewed = ready
        elif component in self._state.integrations_configured:
            self._state.integrations_configured[component] = ready
        self._save()

    def reset(self):
        self._state = SetupStatus()
        self._save()
        logger.info("Setup state reset — wizard will show on next run")

    def get_recommendations(self) -> dict[str, Any]:
        self._ensure_loaded()
        self._refresh_dynamic()

        recs = {
            "llm": {
                "status": "ready" if self._state.llm_ready else "not_configured",
                "provider": self._state.llm_provider,
                "recommended": "",
                "commands": [],
            },
            "documents": {
                "status": "ready" if self._state.documents_ready else "empty",
                "provider": self._state.documents_provider,
            },
            "voice": {
                "status": "ready" if self._state.voice_ready else "not_configured",
                "provider": self._state.voice_provider,
            },
        }

        if not self._state.llm_ready:
            recs["llm"]["recommended"] = "qwen2.5:7b"
            recs["llm"]["commands"] = [
                "ollama pull qwen2.5:7b",
                "# Then restart Jarvis or run: POST /api/setup/refresh",
            ]

        return recs


# ── Singleton ──

setup_state = SetupState()
