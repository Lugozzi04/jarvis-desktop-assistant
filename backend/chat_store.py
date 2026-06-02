"""Conversation Store — persists chat conversations as JSON files."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.core.logger import logger


class ConversationStore:
    """JSON-file-based conversation persistence."""

    def __init__(self):
        self._dir = settings.data_path / "conversations"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, conv_id: str) -> Path:
        return self._dir / f"{conv_id}.json"

    def list(self) -> list[dict[str, Any]]:
        """List all conversations (latest first)."""
        convs = []
        for f in sorted(self._dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text())
                convs.append({
                    "id": data.get("id", f.stem),
                    "title": data.get("title", "Untitled"),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len(data.get("messages", [])),
                    "llm_model": data.get("llm_model", ""),
                })
            except Exception:
                pass
        return convs

    def get(self, conv_id: str) -> dict[str, Any] | None:
        """Get a full conversation."""
        p = self._path(conv_id)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            return None

    def create(self, title: str = "New Chat") -> dict[str, Any]:
        """Create a new conversation."""
        conv_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        conv = {
            "id": conv_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "llm_model": "",
            "messages": [],
        }
        self._path(conv_id).write_text(json.dumps(conv, indent=2))
        logger.info("Created conversation {}", conv_id)
        return {"id": conv_id, "title": title, "created_at": now, "updated_at": now, "message_count": 0, "llm_model": ""}

    def add_message(self, conv_id: str, role: str, content: str) -> dict[str, Any] | None:
        """Add a message to a conversation."""
        conv = self.get(conv_id)
        if not conv:
            return None
        msg = {
            "id": len(conv["messages"]) + 1,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        conv["messages"].append(msg)
        conv["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Auto-title: use first user message
        if role == "user" and conv["title"] == "New Chat":
            conv["title"] = content[:50] + ("..." if len(content) > 50 else "")

        self._path(conv_id).write_text(json.dumps(conv, indent=2))
        return msg

    def delete(self, conv_id: str) -> bool:
        """Delete a conversation."""
        p = self._path(conv_id)
        if p.exists():
            p.unlink()
            logger.info("Deleted conversation {}", conv_id)
            return True
        return False

    def update_title(self, conv_id: str, title: str) -> bool:
        """Update conversation title."""
        conv = self.get(conv_id)
        if not conv:
            return False
        conv["title"] = title
        conv["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._path(conv_id).write_text(json.dumps(conv, indent=2))
        return True

    def get_context_messages(self, conv_id: str, max_messages: int = 20) -> list[dict[str, str]]:
        """Get last N messages formatted for LLM context."""
        conv = self.get(conv_id)
        if not conv:
            return []
        msgs = []
        for m in conv.get("messages", [])[-max_messages:]:
            msgs.append({"role": m["role"], "content": m["content"]})
        return msgs


# Singleton
conversation_store = ConversationStore()
