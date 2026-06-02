"""Automation Engine — repository, trigger/condition/action evaluators, scheduler.

Storage: JSON file-based (same pattern as WorkflowEngine).
Scheduler: lightweight threading loop, no external dependencies.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.core.logger import logger
from backend.core.permissions import permission_guard
from backend.core.registry import skill_registry
from backend.automation.models import (
    SEED_AUTOMATIONS,
    Action,
    Automation,
    AutomationRunResult,
    Condition,
    ConditionResult,
    ActionResult as AutoActionResult,
    Trigger,
)


def _automations_file() -> Path:
    """Get the path to the automations JSON file (lazy, respects config changes)."""
    return Path(settings.data_dir) / "automations.json"


# ── Trigger Evaluators ──

class TriggerEvaluator:
    """Evaluates whether a trigger should fire."""

    @staticmethod
    def evaluate(trigger: Trigger, context: dict[str, Any] | None = None) -> bool:
        """Evaluate a trigger given optional context."""
        ctx = context or {}
        ttype = trigger.type
        cfg = trigger.config

        if ttype == "manual":
            # Manual trigger always fires when explicitly called
            return True

        if ttype == "startup":
            # Startup triggers fire on engine init
            return ctx.get("startup", False)

        if ttype == "time":
            return _check_time_trigger(cfg)

        if ttype == "interval":
            return _check_interval_trigger(trigger, ctx)

        if ttype == "app_opened":
            return _check_app_opened_trigger(cfg, ctx)

        if ttype == "mode_is":
            return _check_mode_trigger(cfg, ctx)

        return False


def _check_time_trigger(cfg) -> bool:
    """Check if current time matches the configured time."""
    target_time = cfg.time
    if not target_time:
        return False

    now = datetime.now()
    current_hhmm = now.strftime("%H:%M")

    # Check day filter
    if cfg.days:
        day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
        current_day = now.weekday()
        allowed_days = [day_map.get(d.lower(), -1) for d in cfg.days]
        if current_day not in allowed_days:
            return False

    return current_hhmm == target_time


def _check_interval_trigger(trigger: Trigger, ctx: dict[str, Any]) -> bool:
    """Check if enough time has passed since last interval run."""
    interval = trigger.config.interval_minutes
    if not interval:
        return False

    last_run = ctx.get("_last_interval_run", {}).get(trigger.config.interval_minutes, 0)
    elapsed = time.time() - last_run
    return elapsed >= (interval * 60)


def _check_app_opened_trigger(cfg, ctx: dict[str, Any]) -> bool:
    """Check if the configured app was opened."""
    app_name = cfg.app_name
    if not app_name:
        return False
    opened_app = ctx.get("app_opened", "")
    return opened_app.lower() == app_name.lower()


def _check_mode_trigger(cfg, ctx: dict[str, Any]) -> bool:
    """Check if current mode matches."""
    mode_name = cfg.mode_name
    if not mode_name:
        return False
    current_mode = ctx.get("mode", "")
    return current_mode.lower() == mode_name.lower()


# ── Condition Evaluators ──

class ConditionEvaluator:
    """Evaluates whether conditions are met."""

    @staticmethod
    def evaluate(condition: Condition) -> tuple[bool, str]:
        """Evaluate a condition. Returns (passed, message)."""
        ctype = condition.type
        cfg = condition.config

        if ctype == "always":
            return True, "always passes"

        if ctype == "time_after":
            return _check_time_after(cfg)

        if ctype == "time_before":
            return _check_time_before(cfg)

        if ctype == "day_of_week":
            return _check_day_of_week(cfg)

        if ctype == "app_running":
            return _check_app_running(cfg)

        if ctype == "mode_is":
            return _check_mode_condition(cfg)

        return False, f"unknown condition type: {ctype}"


def _check_time_after(cfg) -> tuple[bool, str]:
    target = cfg.time
    if not target:
        return False, "no time configured"
    try:
        target_t = dt_time.fromisoformat(target)
        now_t = datetime.now().time()
        passed = now_t >= target_t
        return passed, f"current {now_t.strftime('%H:%M')} {'>=' if passed else '<'} {target}"
    except ValueError:
        return False, f"invalid time format: {target}"


def _check_time_before(cfg) -> tuple[bool, str]:
    target = cfg.time
    if not target:
        return False, "no time configured"
    try:
        target_t = dt_time.fromisoformat(target)
        now_t = datetime.now().time()
        passed = now_t <= target_t
        return passed, f"current {now_t.strftime('%H:%M')} {'<=' if passed else '>'} {target}"
    except ValueError:
        return False, f"invalid time format: {target}"


def _check_day_of_week(cfg) -> tuple[bool, str]:
    if not cfg.days:
        return True, "no day filter — passes"
    day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
    current_day = datetime.now().weekday()
    current_name = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][current_day]
    allowed = any(day_map.get(d.lower(), -1) == current_day for d in cfg.days)
    if allowed:
        return True, f"today is {current_name} (allowed)"
    return False, f"today is {current_name} (not in {cfg.days})"


def _check_app_running(cfg) -> tuple[bool, str]:
    # Placeholder — would need OS-specific process detection
    return True, "app_running check is placeholder — always passes"


def _check_mode_condition(cfg) -> tuple[bool, str]:
    # Placeholder — mode system not yet implemented
    return True, "mode_is check is placeholder — always passes"


# ── Action Executor ──

class ActionExecutor:
    """Executes automation actions, reusing SkillRegistry and WorkflowEngine."""

    @staticmethod
    def execute(action: Action) -> AutoActionResult:
        """Execute a single action. Returns ActionResult."""
        atype = action.type

        try:
            if atype == "skill_action":
                return _execute_skill_action(action)
            elif atype == "workflow":
                return _execute_workflow_action(action)
            elif atype == "notification":
                return _execute_notification(action)
            elif atype == "chat_response":
                return _execute_chat_response(action)
            else:
                return AutoActionResult(
                    index=0, type=atype, status="failed",
                    error=f"Unknown action type: {atype}",
                )
        except Exception as exc:
            return AutoActionResult(
                index=0, type=atype, status="failed",
                error=str(exc),
            )


def _execute_skill_action(action: Action) -> AutoActionResult:
    skill_name = action.skill or ""
    action_name = action.action or ""
    if not skill_name or not action_name:
        return AutoActionResult(
            index=0, type="skill_action", status="failed",
            error="Missing skill or action name",
        )

    result = skill_registry.execute(skill_name, action_name, action.parameters)
    if result.success:
        return AutoActionResult(
            index=0, type="skill_action", status="success",
            result=result.result,
        )
    return AutoActionResult(
        index=0, type="skill_action", status="failed",
        error=result.error or "Action failed",
    )


def _execute_workflow_action(action: Action) -> AutoActionResult:
    workflow_id = action.workflow_id or ""
    if not workflow_id:
        return AutoActionResult(
            index=0, type="workflow", status="failed",
            error="Missing workflow_id",
        )

    try:
        from backend.workflows.engine import workflow_engine
        result = workflow_engine.run(workflow_id)
        if result.get("status") == "error":
            return AutoActionResult(
                index=0, type="workflow", status="failed",
                error=result.get("error", "Workflow failed"),
            )
        status = result.get("status", "unknown")
        return AutoActionResult(
            index=0, type="workflow",
            status="success" if status == "success" else "partial",
            result=result,
        )
    except Exception as exc:
        return AutoActionResult(
            index=0, type="workflow", status="failed",
            error=str(exc),
        )


def _execute_notification(action: Action) -> AutoActionResult:
    message = action.parameters.get("message", "Notification")
    # Log the notification — in future, could trigger desktop notification
    logger.info("Automation notification: {}", message)
    return AutoActionResult(
        index=0, type="notification", status="success",
        result={"message": message},
    )


def _execute_chat_response(action: Action) -> AutoActionResult:
    message = action.parameters.get("message", "")
    logger.info("Automation chat response: {}", message)
    return AutoActionResult(
        index=0, type="chat_response", status="success",
        result={"message": message},
    )


# ── Automation Engine ──

class AutomationEngine:
    """Manages automation definitions, evaluation, and execution.

    Includes a lightweight background scheduler for time/interval triggers.
    """

    def __init__(self):
        self._automations: dict[str, Automation] = {}
        self._loaded = False
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_tick: str | None = None
        self._errors: list[str] = []
        self._last_interval_run: dict[int, float] = {}  # interval_minutes → timestamp
        self._startup_run = False

    # ── Loading ──

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._load()
        if not self._automations:
            self._seed_defaults()
        self._loaded = True

    def _load(self) -> None:
        try:
            if _automations_file().exists():
                data = json.loads(_automations_file().read_text())
                for auto_data in data:
                    try:
                        auto = Automation(**auto_data)
                        self._automations[auto.id] = auto
                    except Exception as exc:
                        logger.warning("Skipping invalid automation in storage: {}", exc)
                logger.info("Loaded {} automations from storage", len(self._automations))
        except Exception as exc:
            logger.warning("Failed to load automations: {}", exc)

    def _save(self) -> None:
        try:
            _automations_file().parent.mkdir(parents=True, exist_ok=True)
            data = [a.model_dump() for a in self._automations.values()]
            _automations_file().write_text(json.dumps(data, indent=2))
        except Exception as exc:
            logger.error("Failed to save automations: {}", exc)

    def _seed_defaults(self) -> None:
        logger.info("Seeding default automations...")
        for seed in SEED_AUTOMATIONS:
            try:
                auto = Automation(**seed)
                self._automations[auto.id] = auto
                logger.info("Seeded automation: {} ({}) enabled={}", auto.name, auto.id, auto.enabled)
            except Exception as exc:
                logger.error("Failed to seed automation {}: {}", seed.get("id"), exc)
        self._save()

    # ── CRUD ──

    def list_all(self) -> list[dict[str, Any]]:
        self._ensure_loaded()
        return [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "enabled": a.enabled,
                "trigger_type": a.trigger.type,
                "action_count": len(a.actions),
                "last_run_at": a.last_run_at,
                "last_status": a.last_status,
                "run_count": a.run_count,
            }
            for a in self._automations.values()
        ]

    def get(self, automation_id: str) -> dict[str, Any] | None:
        self._ensure_loaded()
        auto = self._automations.get(automation_id)
        if auto is None:
            return None
        return auto.model_dump()

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        self._ensure_loaded()
        if "id" not in data or not data["id"]:
            data["id"] = data.get("name", "automation").lower().replace(" ", "-")
        if data["id"] in self._automations:
            return {"error": f"Automation '{data['id']}' already exists"}
        try:
            auto = Automation(**data)
            self._automations[auto.id] = auto
            self._save()
            logger.info("Created automation: {} ({})", auto.name, auto.id)
            return auto.model_dump()
        except Exception as exc:
            return {"error": str(exc)}

    def update(self, automation_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self._ensure_loaded()
        if automation_id not in self._automations:
            return {"error": f"Automation '{automation_id}' not found"}
        try:
            existing = self._automations[automation_id]
            updated_data = existing.model_dump()
            updated_data.update(data)
            updated_data["id"] = automation_id
            updated_data["updated_at"] = datetime.utcnow().isoformat()
            auto = Automation(**updated_data)
            self._automations[automation_id] = auto
            self._save()
            return auto.model_dump()
        except Exception as exc:
            return {"error": str(exc)}

    def delete(self, automation_id: str) -> dict[str, Any]:
        self._ensure_loaded()
        if automation_id not in self._automations:
            return {"error": f"Automation '{automation_id}' not found"}
        auto = self._automations.pop(automation_id)
        self._save()
        logger.info("Deleted automation: {} ({})", auto.name, automation_id)
        return {"status": "deleted", "id": automation_id, "name": auto.name}

    def enable(self, automation_id: str) -> dict[str, Any]:
        self._ensure_loaded()
        if automation_id not in self._automations:
            return {"error": f"Automation '{automation_id}' not found"}
        self._automations[automation_id].enabled = True
        self._save()
        return {"status": "enabled", "id": automation_id}

    def disable(self, automation_id: str) -> dict[str, Any]:
        self._ensure_loaded()
        if automation_id not in self._automations:
            return {"error": f"Automation '{automation_id}' not found"}
        self._automations[automation_id].enabled = False
        self._save()
        return {"status": "disabled", "id": automation_id}

    # ── Execution ──

    def run(
        self,
        automation_id: str,
        triggered_by: str = "manual",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a single automation — evaluates trigger, conditions, runs actions."""
        self._ensure_loaded()
        auto = self._automations.get(automation_id)
        if auto is None:
            return {
                "automation_id": automation_id,
                "status": "failed",
                "triggered_by": triggered_by,
                "error": f"Automation '{automation_id}' not found",
            }

        t0 = time.monotonic()
        cond_results: list[ConditionResult] = []
        action_results: list[AutoActionResult] = []

        logger.info("Running automation: {} ({}) triggered_by={}", auto.name, auto.id, triggered_by)

        # Ensure skills and workflows are loaded
        if not skill_registry.loaded:
            skill_registry.discover_and_load()

        # Evaluate trigger
        # Skip trigger evaluation if the caller explicitly triggered by the same type
        if triggered_by not in (auto.trigger.type, "manual"):
            trigger_ok = TriggerEvaluator.evaluate(auto.trigger, context)
            if not trigger_ok:
                return {
                    "automation_id": automation_id,
                    "automation_name": auto.name,
                    "status": "skipped",
                    "triggered_by": triggered_by,
                    "conditions": [],
                    "actions": [],
                    "error": "Trigger conditions not met",
                }

        # Evaluate conditions
        all_conditions_passed = True
        for cond in auto.conditions:
            passed, msg = ConditionEvaluator.evaluate(cond)
            cr = ConditionResult(
                type=cond.type,
                status="passed" if passed else "failed",
                message=msg,
            )
            cond_results.append(cr)
            if not passed:
                all_conditions_passed = False

        if auto.conditions and not all_conditions_passed:
            elapsed = (time.monotonic() - t0) * 1000
            result = AutomationRunResult(
                automation_id=automation_id,
                automation_name=auto.name,
                status="skipped",
                triggered_by=triggered_by,
                conditions=cond_results,
                actions=[],
                error="Conditions not met",
                total_duration_ms=round(elapsed, 1),
            )

            # Update stats
            auto.run_count += 1
            auto.last_run_at = datetime.utcnow().isoformat()
            auto.last_status = "skipped"
            self._save()

            return result.model_dump()

        # Check permissions for each action
        requires_confirmation = False
        for action in auto.actions:
            if action.risk in ("confirmation", "dangerous"):
                risk = action.risk
                if risk == "dangerous" or (risk == "confirmation" and settings.security.confirm_dangerous_actions):
                    requires_confirmation = True
                    break

        if requires_confirmation and triggered_by != "manual":
            # Auto-triggered dangerous actions are skipped
            elapsed = (time.monotonic() - t0) * 1000
            result = AutomationRunResult(
                automation_id=automation_id,
                automation_name=auto.name,
                status="skipped_requires_confirmation",
                triggered_by=triggered_by,
                conditions=cond_results,
                actions=[],
                error="Contains actions requiring user confirmation — cannot run automatically",
                total_duration_ms=round(elapsed, 1),
            )

            auto.run_count += 1
            auto.last_run_at = datetime.utcnow().isoformat()
            auto.last_status = "skipped_requires_confirmation"
            self._save()

            logger.warning(
                "Automation '{}' skipped — contains confirmation/dangerous actions", auto.name,
            )
            return result.model_dump()

        # Execute actions
        successful = 0
        failed = 0
        for i, action in enumerate(auto.actions):
            ar = ActionExecutor.execute(action)
            ar.index = i + 1
            action_results.append(ar)
            if ar.status == "success":
                successful += 1
            else:
                failed += 1

        # Determine overall status
        total_actions = len(auto.actions)
        if failed == 0:
            status = "success"
        elif successful > 0:
            status = "partial"
        else:
            status = "failed"

        elapsed = (time.monotonic() - t0) * 1000

        # Update stats
        auto.run_count += 1
        auto.last_run_at = datetime.utcnow().isoformat()
        auto.last_status = status
        self._save()

        result = AutomationRunResult(
            automation_id=automation_id,
            automation_name=auto.name,
            status=status,
            triggered_by=triggered_by,
            conditions=cond_results,
            actions=action_results,
            total_duration_ms=round(elapsed, 1),
        )

        logger.info(
            "Automation '{}' completed: {} ({}/{}) in {:.0f}ms",
            auto.name, status, successful, total_actions, elapsed,
        )

        return result.model_dump()

    # ── Scheduler ──

    def start_scheduler(self) -> None:
        """Start the background scheduler thread."""
        if self._running:
            logger.info("Scheduler already running")
            return
        self._ensure_loaded()
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="automation-scheduler")
        self._thread.start()
        logger.info("Automation scheduler started")

    def stop_scheduler(self) -> None:
        """Stop the background scheduler thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Automation scheduler stopped")

    def get_scheduler_status(self) -> dict[str, Any]:
        """Get scheduler engine status."""
        self._ensure_loaded()
        enabled_count = sum(1 for a in self._automations.values() if a.enabled)
        return {
            "running": self._running,
            "loaded_automations": len(self._automations),
            "enabled_automations": enabled_count,
            "last_tick": self._last_tick,
            "errors": self._errors[-10:],  # last 10
        }

    def _scheduler_loop(self) -> None:
        """Background loop checking time/interval triggers every 15 seconds."""
        logger.info("Scheduler loop started — tick interval: 15s")

        # Run startup automations once
        if not self._startup_run:
            self._startup_run = True
            self._run_startup_automations()

        while self._running:
            try:
                tick_start = datetime.utcnow()
                self._last_tick = tick_start.isoformat()

                with self._lock:
                    for auto in list(self._automations.values()):
                        if not auto.enabled:
                            continue
                        if auto.trigger.type in ("manual", "app_opened", "mode_is"):
                            continue  # Not triggered by scheduler

                        try:
                            context = {
                                "_last_interval_run": self._last_interval_run,
                                "startup": False,
                            }
                            should_run = TriggerEvaluator.evaluate(auto.trigger, context)

                            if should_run:
                                # Update interval tracking before running
                                if auto.trigger.type == "interval" and auto.trigger.config.interval_minutes:
                                    self._last_interval_run[auto.trigger.config.interval_minutes] = time.time()

                                logger.info("Scheduler triggered: {} ({})", auto.name, auto.id)
                                self.run(auto.id, triggered_by="scheduler", context=context)

                        except Exception as exc:
                            msg = f"Error evaluating automation {auto.id}: {exc}"
                            logger.error(msg)
                            self._errors.append(msg)

            except Exception as exc:
                msg = f"Scheduler tick error: {exc}"
                logger.error(msg)
                self._errors.append(msg)

            # Sleep 15 seconds between ticks
            for _ in range(15):
                if not self._running:
                    break
                time.sleep(1)

        logger.info("Scheduler loop stopped")

    def _run_startup_automations(self) -> None:
        """Run automations with startup trigger."""
        logger.info("Running startup automations...")
        for auto in list(self._automations.values()):
            if auto.enabled and auto.trigger.type == "startup":
                try:
                    self.run(auto.id, triggered_by="startup", context={"startup": True})
                except Exception as exc:
                    logger.error("Startup automation '{}' failed: {}", auto.name, exc)

    def reload(self) -> dict[str, Any]:
        """Reload automations from storage."""
        self._automations.clear()
        self._loaded = False
        self._ensure_loaded()
        return {"status": "reloaded", "count": len(self._automations)}


# Singleton
automation_engine = AutomationEngine()
