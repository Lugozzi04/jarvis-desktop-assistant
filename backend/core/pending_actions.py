"""Pending Actions Queue — security gate for confirmation/dangerous actions.

Every dangerous action is placed in the pending queue.
The user must approve from the UI before the action executes.
Integrates with PermissionGuard and all skill execution paths.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.logger import logger


class PendingAction(BaseModel):
    id: str = Field(default_factory=lambda: f"pa_{int(time.time() * 1000)}")
    skill: str
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk: str = "dangerous"  # confirmation | dangerous
    reason: str = ""
    source: str = "user"  # user | automation | workflow
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "pending"  # pending | approved | rejected | expired
    resolved_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    timeout_minutes: int = 60  # auto-reject after this many minutes


class PendingActionsQueue:
    """Thread-safe pending actions queue with file persistence."""

    MAX_PENDING = 100

    def __init__(self):
        self._lock = Lock()
        self._actions: dict[str, PendingAction] = {}
        self._storage_path = Path(settings.data_dir) / "pending_actions.json"
        self._load()

    def _load(self):
        if self._storage_path.exists():
            try:
                data = json.loads(self._storage_path.read_text())
                self._actions = {
                    k: PendingAction(**v)
                    for k, v in data.items()
                    if v.get("status") == "pending"
                }
            except Exception as e:
                logger.warning("Could not load pending actions: {}", e)

    def _save(self):
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._storage_path.write_text(
                json.dumps(
                    {k: v.model_dump() for k, v in self._actions.items()},
                    indent=2,
                )
            )

    def add(
        self,
        skill: str,
        action: str,
        parameters: dict[str, Any],
        risk: str = "dangerous",
        reason: str = "",
        source: str = "user",
        timeout_minutes: int = 60,
    ) -> PendingAction:
        """Add a pending action requiring approval."""
        with self._lock:
            # Purge old
            self._auto_reject_expired()

            if len(self._actions) >= self.MAX_PENDING:
                # Remove oldest
                oldest = min(self._actions.values(), key=lambda a: a.created_at)
                oldest.status = "expired"
                del self._actions[oldest.id]

            pa = PendingAction(
                skill=skill,
                action=action,
                parameters=parameters,
                risk=risk,
                reason=reason,
                source=source,
                timeout_minutes=timeout_minutes,
            )
            self._actions[pa.id] = pa
            self._save()
            logger.info("Pending action created: {}.{} (risk={}, id={})", skill, action, risk, pa.id)
            return pa

    def approve(self, action_id: str) -> bool:
        """Approve a pending action. Returns True if found and approved."""
        with self._lock:
            pa = self._actions.get(action_id)
            if not pa or pa.status != "pending":
                return False
            pa.status = "approved"
            pa.resolved_at = datetime.utcnow().isoformat()
            self._save()
            logger.info("Pending action approved: {}.{} ({})", pa.skill, pa.action, action_id)
            return True

    def reject(self, action_id: str) -> bool:
        """Reject a pending action. Returns True if found and rejected."""
        with self._lock:
            pa = self._actions.get(action_id)
            if not pa or pa.status != "pending":
                return False
            pa.status = "rejected"
            pa.resolved_at = datetime.utcnow().isoformat()
            self._save()
            logger.info("Pending action rejected: {}.{} ({})", pa.skill, pa.action, action_id)
            return True

    def get_pending(self) -> list[PendingAction]:
        """Get all pending (not yet resolved) actions."""
        with self._lock:
            self._auto_reject_expired()
            return sorted(
                [a for a in self._actions.values() if a.status == "pending"],
                key=lambda a: a.created_at,
                reverse=True,
            )

    def get_all(self) -> list[PendingAction]:
        """Get all actions including resolved ones."""
        with self._lock:
            return sorted(
                list(self._actions.values()),
                key=lambda a: a.created_at,
                reverse=True,
            )

    def get(self, action_id: str) -> PendingAction | None:
        return self._actions.get(action_id)

    def count(self) -> int:
        return len(self.get_pending())

    def execute_approved(self, action_id: str):
        """Execute an approved action and store the result."""
        pa = self._actions.get(action_id)
        if not pa or pa.status != "approved":
            return

        try:
            from backend.core.registry import skill_registry
            result = skill_registry.execute(pa.skill, pa.action, pa.parameters)
            pa.result = result.model_dump() if result else {"success": False}
            if not result or not result.success:
                pa.error = result.error if result else "Action failed"
        except Exception as e:
            pa.error = str(e)
            pa.result = {"success": False}

        self._save()

    def clear_resolved(self):
        """Remove resolved actions older than 1 hour."""
        with self._lock:
            cutoff = datetime.utcnow().timestamp() - 3600
            to_remove = []
            for k, a in self._actions.items():
                if a.status in ("approved", "rejected", "expired") and a.resolved_at:
                    try:
                        ts = datetime.fromisoformat(a.resolved_at).timestamp()
                        if ts < cutoff:
                            to_remove.append(k)
                    except Exception:
                        pass
            for k in to_remove:
                del self._actions[k]
            if to_remove:
                self._save()

    def _auto_reject_expired(self):
        now = datetime.utcnow()
        for a in self._actions.values():
            if a.status != "pending":
                continue
            try:
                created = datetime.fromisoformat(a.created_at)
                if (now - created).total_seconds() > a.timeout_minutes * 60:
                    a.status = "expired"
                    a.resolved_at = now.isoformat()
                    a.error = f"Auto-rejected: exceeded {a.timeout_minutes}min timeout"
                    logger.info("Pending action expired: {}.{} ({})", a.skill, a.action, a.id)
            except Exception:
                pass


# ── Singleton ──

pending_queue = PendingActionsQueue()
