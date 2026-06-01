"""Skill Registry — discovers, loads, and manages all JARVIS skills.

Skills live in backend/skills/<name>/ with:
  - manifest.json (metadata, actions, risk levels)
  - skill.py (class inheriting BaseSkill)

The registry auto-discovers skills at startup, validates manifests,
and provides lookup and execution capabilities to the rest of the system.
"""

from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path
from typing import Any

from backend.core.errors import ActionNotSupportedError, SkillNotFoundError
from backend.core.logger import logger
from backend.core.schemas import ActionResult, RiskLevel
from backend.skills.base import BaseSkill, load_manifest

SKILLS_DIR = Path(__file__).resolve().parent


class SkillRegistry:
    """Central registry for all JARVIS skills.

    Loads skills automatically from the filesystem, validates manifests,
    and provides lookup and health-check functionality.
    """

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}
        self._manifests: dict[str, dict[str, Any]] = {}
        self._loaded = False

    # ── Public API ──

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def skill_names(self) -> list[str]:
        return sorted(self._skills.keys())

    def get(self, name: str) -> BaseSkill:
        """Get a skill by name. Raises SkillNotFoundError if missing."""
        skill = self._skills.get(name)
        if skill is None:
            raise SkillNotFoundError(name)
        if not skill.enabled:
            raise SkillNotFoundError(f"Skill '{name}' is disabled")
        return skill

    def get_manifest(self, name: str) -> dict[str, Any]:
        """Get a skill's manifest."""
        manifest = self._manifests.get(name)
        if manifest is None:
            raise SkillNotFoundError(name)
        return manifest

    def list_skills(self) -> list[dict[str, Any]]:
        """List all registered skills with status."""
        result = []
        for name, skill in self._skills.items():
            manifest = self._manifests.get(name, {})
            result.append({
                "name": name,
                "display_name": skill.display_name,
                "description": skill.description,
                "version": skill.version,
                "enabled": skill.enabled,
                "actions": [a["name"] for a in manifest.get("actions", [])],
            })
        return result

    def get_actions(self, name: str) -> list[dict[str, Any]]:
        """Get the actions for a skill."""
        manifest = self.get_manifest(name)
        return manifest.get("actions", [])

    def find_handler(self, skill_name: str, action: str) -> BaseSkill:
        """Find the skill that handles the given skill_name + action."""
        skill = self.get(skill_name)
        if not skill.can_handle(skill_name, action):
            raise ActionNotSupportedError(skill_name, action)
        return skill

    def get_risk(self, skill_name: str, action: str) -> RiskLevel:
        """Get the risk level for a skill action."""
        skill = self.get(skill_name)
        return skill.get_risk(action)

    # ── Execution ──

    def execute(
        self,
        skill_name: str,
        action: str,
        parameters: dict[str, Any],
    ) -> ActionResult:
        """Execute a skill action with error handling."""
        try:
            skill = self.find_handler(skill_name, action)
            logger.debug("Executing {}.{} params={}", skill_name, action, parameters)
            result = skill.execute(action=action, parameters=parameters)
            return result
        except SkillNotFoundError:
            return ActionResult(
                success=False,
                skill=skill_name,
                action=action,
                risk=RiskLevel.safe,
                error=f"Skill '{skill_name}' not found",
            )
        except ActionNotSupportedError:
            return ActionResult(
                success=False,
                skill=skill_name,
                action=action,
                risk=RiskLevel.safe,
                error=f"Action '{action}' not supported by '{skill_name}'",
            )
        except Exception as exc:
            logger.exception("Skill {}.{} failed", skill_name, action)
            return ActionResult(
                success=False,
                skill=skill_name,
                action=action,
                risk=RiskLevel.safe,
                error=str(exc),
            )

    # ── Discovery & Loading ──

    def discover_and_load(self) -> list[str]:
        """Auto-discover and load all skills from the filesystem."""
        if self._loaded:
            logger.info("Skills already loaded — skipping")
            return self.skill_names

        loaded = []
        for item in sorted(SKILLS_DIR.iterdir()):
            if not item.is_dir():
                continue
            if item.name.startswith("__") or item.name == "base":
                continue

            manifest_path = item / "manifest.json"
            skill_py = item / "skill.py"

            if not manifest_path.exists() or not skill_py.exists():
                logger.debug("Skipping {} — missing manifest or skill.py", item.name)
                continue

            try:
                manifest = load_manifest(item)
                skill_name = manifest["name"]

                # Import the skill module dynamically
                module_name = f"backend.skills.{item.name}.skill"
                if module_name in sys.modules:
                    del sys.modules[module_name]

                module = importlib.import_module(module_name)

                # Find the BaseSkill subclass
                skill_instance = None
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BaseSkill)
                        and obj is not BaseSkill
                        and obj.__module__ == module_name
                    ):
                        skill_instance = obj()
                        break

                if skill_instance is None:
                    logger.error("No BaseSkill subclass found in {}", module_name)
                    continue

                # Set metadata from manifest
                skill_instance.name = skill_name
                skill_instance.display_name = manifest.get("display_name", skill_name)
                skill_instance.description = manifest.get("description", "")
                skill_instance.version = manifest.get("version", "0.1.0")
                skill_instance.author = manifest.get("author", "")
                skill_instance.actions = manifest.get("actions", [])

                self._skills[skill_name] = skill_instance
                self._manifests[skill_name] = manifest
                loaded.append(skill_name)
                logger.info(
                    "Loaded skill: {} (v{}, {} actions)",
                    skill_name,
                    skill_instance.version,
                    len(skill_instance.actions),
                )

            except Exception as exc:
                logger.error("Failed to load skill from {}: {}", item.name, exc)

        self._loaded = True
        logger.info("Skill registry loaded — {} skills: {}", len(loaded), loaded)
        return loaded

    def reload(self) -> list[str]:
        """Reload all skills (useful during development)."""
        self._skills.clear()
        self._manifests.clear()
        self._loaded = False
        return self.discover_and_load()


# Global singleton
skill_registry = SkillRegistry()
