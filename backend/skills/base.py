"""Base Skill class — every skill inherits from this.

Skills are loaded from the skills/ directory. Each skill has:
- A manifest.json declaring its name, actions, permissions, and risk levels
- A skill.py module with a class inheriting from BaseSkill

The core NEVER hardcodes skill-specific logic.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.core.logger import audit_log, logger
from backend.core.schemas import ActionResult, RiskLevel


class BaseSkill(ABC):
    """Abstract base for all JARVIS skills.

    Subclasses override:
      - can_handle(intent) → bool
      - execute(action, parameters) → ActionResult
    """

    # Class-level, set from manifest or subclass
    name: str = ""
    display_name: str = ""
    description: str = ""
    version: str = "0.1.0"
    author: str = ""
    actions: list[dict[str, Any]] = []

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def can_handle(self, skill_name: str, action: str) -> bool:
        """Check if this skill can handle the given action.

        Override for more complex routing logic.
        """
        if skill_name != self.name:
            return False
        action_names = [a["name"] for a in self.actions]
        return action in action_names

    @abstractmethod
    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        """Execute a skill action. Must be implemented by subclasses.

        Args:
            action: The action name (e.g., 'open', 'search')
            parameters: Action-specific parameters

        Returns:
            ActionResult with success/error/confirmation info
        """
        ...

    def get_risk(self, action: str) -> RiskLevel:
        """Get the risk level for a specific action."""
        for a in self.actions:
            if a.get("name") == action:
                risk_str = a.get("risk", "safe")
                try:
                    return RiskLevel(risk_str)
                except ValueError:
                    return RiskLevel.safe
        return RiskLevel.safe

    def _result(
        self,
        action: str,
        success: bool = True,
        result: Any = None,
        error: str | None = None,
    ) -> ActionResult:
        """Helper to build a standard ActionResult."""
        return ActionResult(
            success=success,
            skill=self.name,
            action=action,
            risk=self.get_risk(action),
            result=result,
            error=error,
        )


# ── Manifest Loading ──

def load_manifest(skill_dir: Path) -> dict[str, Any]:
    """Load and validate a skill's manifest.json."""
    manifest_path = skill_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {skill_dir}")

    with open(manifest_path) as f:
        manifest = json.load(f)

    required = ["name", "display_name", "description", "actions"]
    for key in required:
        if key not in manifest:
            raise ValueError(f"manifest.json missing required key: {key}")

    if not isinstance(manifest["actions"], list) or len(manifest["actions"]) == 0:
        raise ValueError("manifest.json must have at least one action")

    return manifest


__all__ = ["BaseSkill", "load_manifest"]
