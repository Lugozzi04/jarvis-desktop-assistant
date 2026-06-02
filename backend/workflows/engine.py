"""Workflow Engine — storage, CRUD, and execution.

Storage: JSON file-based for MVP (migratable to SQLite later).
Runner: executes each step via SkillRegistry, with error handling and logging.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.core.logger import logger
from backend.core.permissions import permission_guard
from backend.core.registry import skill_registry
from backend.workflows.models import (
    SEED_WORKFLOWS,
    StepResult,
    Workflow,
    WorkflowRunResult,
    WorkflowStep,
)


def _workflows_file() -> Path:
    """Get the path to the workflows JSON file (lazy, respects config changes)."""
    return Path(settings.data_dir) / "workflows.json"


class WorkflowEngine:
    """Manages workflow definitions, storage, and execution."""

    def __init__(self):
        self._workflows: dict[str, Workflow] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Load workflows from storage, seeding defaults on first run."""
        if self._loaded:
            return
        self._load()
        if not self._workflows:
            self._seed_defaults()
        self._loaded = True

    def _load(self) -> None:
        """Load workflows from JSON file."""
        try:
            if _workflows_file().exists():
                data = json.loads(_workflows_file().read_text())
                for wf_data in data:
                    try:
                        wf = Workflow(**wf_data)
                        self._workflows[wf.id] = wf
                    except Exception as exc:
                        logger.warning("Skipping invalid workflow in storage: {}", exc)
                logger.info("Loaded {} workflows from storage", len(self._workflows))
        except Exception as exc:
            logger.warning("Failed to load workflows: {}", exc)

    def _save(self) -> None:
        """Persist workflows to JSON file."""
        try:
            _workflows_file().parent.mkdir(parents=True, exist_ok=True)
            data = [wf.model_dump() for wf in self._workflows.values()]
            _workflows_file().write_text(json.dumps(data, indent=2))
        except Exception as exc:
            logger.error("Failed to save workflows: {}", exc)

    def _seed_defaults(self) -> None:
        """Create seed workflows on first run."""
        logger.info("Seeding default workflows...")
        for seed in SEED_WORKFLOWS:
            try:
                wf = Workflow(**seed)
                self._workflows[wf.id] = wf
                logger.info("Seeded workflow: {} ({})", wf.name, wf.id)
            except Exception as exc:
                logger.error("Failed to seed workflow {}: {}", seed.get("id"), exc)
        self._save()

    # ── CRUD ──

    def list_all(self) -> list[dict[str, Any]]:
        """List all workflows (summary)."""
        self._ensure_loaded()
        return [
            {
                "id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "step_count": len(wf.steps),
                "created_at": wf.created_at,
            }
            for wf in self._workflows.values()
        ]

    def get(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a single workflow with full details."""
        self._ensure_loaded()
        wf = self._workflows.get(workflow_id)
        if wf is None:
            return None
        return wf.model_dump()

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new workflow."""
        self._ensure_loaded()

        # Auto-generate ID if not provided
        if "id" not in data or not data["id"]:
            data["id"] = data.get("name", "workflow").lower().replace(" ", "-")

        if data["id"] in self._workflows:
            return {"error": f"Workflow '{data['id']}' already exists"}

        try:
            wf = Workflow(**data)
            self._workflows[wf.id] = wf
            self._save()
            logger.info("Created workflow: {} ({})", wf.name, wf.id)
            return wf.model_dump()
        except Exception as exc:
            return {"error": str(exc)}

    def delete(self, workflow_id: str) -> dict[str, Any]:
        """Delete a workflow."""
        self._ensure_loaded()
        if workflow_id not in self._workflows:
            return {"error": f"Workflow '{workflow_id}' not found"}
        wf = self._workflows.pop(workflow_id)
        self._save()
        logger.info("Deleted workflow: {} ({})", wf.name, workflow_id)
        return {"status": "deleted", "id": workflow_id, "name": wf.name}

    def update(self, workflow_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing workflow."""
        self._ensure_loaded()
        if workflow_id not in self._workflows:
            return {"error": f"Workflow '{workflow_id}' not found"}

        try:
            existing = self._workflows[workflow_id]
            updated_data = existing.model_dump()
            updated_data.update(data)
            updated_data["id"] = workflow_id  # Keep original ID
            updated_data["updated_at"] = datetime.utcnow().isoformat()
            wf = Workflow(**updated_data)
            self._workflows[workflow_id] = wf
            self._save()
            return wf.model_dump()
        except Exception as exc:
            return {"error": str(exc)}

    # ── Execution ──

    def run(self, workflow_id: str) -> dict[str, Any]:
        """Execute a workflow — runs all steps sequentially.

        Each step is executed via SkillRegistry. Errors in a step
        do NOT stop the workflow; they are recorded and the workflow
        continues (partial success mode).

        Returns:
            WorkflowRunResult as dict
        """
        self._ensure_loaded()
        wf = self._workflows.get(workflow_id)
        if wf is None:
            return {"status": "error", "error": f"Workflow '{workflow_id}' not found"}

        started_at = datetime.utcnow().isoformat()
        t0 = time.monotonic()
        step_results: list[StepResult] = []
        successful = 0
        failed = 0

        logger.info("Running workflow: {} ({} steps)", wf.name, len(wf.steps))

        # Ensure skills are loaded
        if not skill_registry.loaded:
            skill_registry.discover_and_load()

        for step in sorted(wf.steps, key=lambda s: s.order):
            step_t0 = time.monotonic()
            logger.debug(
                "Workflow step {}/{}: {}.{}",
                step.order, len(wf.steps), step.skill, step.action,
            )

            try:
                # Risk check
                try:
                    risk = skill_registry.get_risk(step.skill, step.action)
                    perm = permission_guard.check(risk, f"{step.skill}.{step.action}")
                    if perm.get("needs_confirmation"):
                        # In workflow context, auto-skip dangerous steps
                        step_results.append(StepResult(
                            order=step.order,
                            skill=step.skill,
                            action=step.action,
                            status="skipped",
                            error="Requires user confirmation — skipped in workflow",
                            duration_ms=(time.monotonic() - step_t0) * 1000,
                        ))
                        failed += 1
                        continue
                except Exception:
                    pass  # Risk check failure is non-fatal

                # Execute
                result = skill_registry.execute(
                    step.skill, step.action, step.parameters,
                )
                elapsed = (time.monotonic() - step_t0) * 1000

                if result.success:
                    step_results.append(StepResult(
                        order=step.order,
                        skill=step.skill,
                        action=step.action,
                        status="success",
                        result=result.result,
                        duration_ms=round(elapsed, 1),
                    ))
                    successful += 1
                else:
                    step_results.append(StepResult(
                        order=step.order,
                        skill=step.skill,
                        action=step.action,
                        status="failed",
                        error=result.error or "Unknown error",
                        duration_ms=round(elapsed, 1),
                    ))
                    failed += 1

            except Exception as exc:
                elapsed = (time.monotonic() - step_t0) * 1000
                logger.warning("Workflow step failed: {}.{} — {}", step.skill, step.action, exc)
                step_results.append(StepResult(
                    order=step.order,
                    skill=step.skill,
                    action=step.action,
                    status="failed",
                    error=str(exc),
                    duration_ms=round(elapsed, 1),
                ))
                failed += 1

        # Determine overall status
        total = len(wf.steps)
        if failed == 0:
            status = "success"
        elif successful > 0:
            status = "partial"
        else:
            status = "failed"

        total_duration = (time.monotonic() - t0) * 1000

        logger.info(
            "Workflow '{}' completed: {} ({}/{}) in {:.0f}ms",
            wf.name, status, successful, total, total_duration,
        )

        run_result = WorkflowRunResult(
            workflow_id=workflow_id,
            workflow_name=wf.name,
            status=status,
            steps=step_results,
            started_at=started_at,
            finished_at=datetime.utcnow().isoformat(),
            total_duration_ms=round(total_duration, 1),
        )

        return run_result.model_dump()


# Singleton
workflow_engine = WorkflowEngine()
