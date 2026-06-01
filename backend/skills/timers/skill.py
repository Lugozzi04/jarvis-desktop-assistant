"""TimerSkill — timers, reminders, and Pomodoro.

Creates countdown timers with desktop notifications.
Uses threading for non-blocking timer execution.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from typing import Any

from backend.core.logger import logger
from backend.core.schemas import ActionResult
from backend.skills.base import BaseSkill


class TimerSkill(BaseSkill):
    """Create and manage timers and reminders."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._timers: dict[str, dict[str, Any]] = {}

    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        if action == "create_timer":
            return self._create_timer(
                parameters.get("duration", ""),
                parameters.get("message", "Timer finished"),
            )
        elif action == "create_reminder":
            return self._create_reminder(
                parameters.get("when", ""),
                parameters.get("message", "Reminder"),
            )
        elif action == "list_active":
            return self._list_timers()
        elif action == "cancel":
            return self._cancel_timer(parameters.get("timer_id", ""))
        else:
            return self._result(action, success=False, error=f"Unknown action: {action}")

    def _parse_duration(self, duration_str: str) -> int:
        """Parse a duration string like '25m', '30s', '1h', '90' into seconds."""
        duration_str = duration_str.strip().lower()
        if not duration_str:
            return 0

        match = re.match(r"^(\d+)\s*(h|m|s|hour|min|sec|minute|second)?s?$", duration_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2) or "m"
            multipliers = {"h": 3600, "hour": 3600, "m": 60, "min": 60, "minute": 60, "s": 1, "sec": 1, "second": 1}
            return value * multipliers.get(unit, 60)

        # Plain number → assume minutes
        try:
            return int(duration_str) * 60
        except ValueError:
            return 0

    def _create_timer(self, duration_str: str, message: str) -> ActionResult:
        seconds = self._parse_duration(duration_str)
        if seconds <= 0:
            return self._result("create_timer", success=False, error=f"Invalid duration: '{duration_str}'. Use format like '25m', '30s', '1h'.")

        timer_id = str(uuid.uuid4())[:8]
        self._timers[timer_id] = {
            "id": timer_id,
            "type": "timer",
            "duration_seconds": seconds,
            "message": message,
            "remaining": seconds,
            "created_at": time.time(),
        }

        # Start countdown in background thread
        thread = threading.Thread(
            target=self._run_timer,
            args=(timer_id, seconds, message),
            daemon=True,
        )
        thread.start()

        mins = seconds // 60
        secs = seconds % 60
        duration_display = f"{mins}m{secs}s" if secs > 0 else f"{mins}m"

        logger.info("Timer created: {} — {} ({})", timer_id, duration_display, message)
        return self._result(
            "create_timer",
            success=True,
            result=f"⏱️ Timer set for {duration_display}: \"{message}\" (ID: {timer_id})",
        )

    def _create_reminder(self, when: str, message: str) -> ActionResult:
        # For MVP, treat "when" as a simple duration string
        seconds = self._parse_duration(when.replace("in ", ""))
        if seconds <= 0:
            # Try to parse as time like "18:30"
            return self._result(
                "create_reminder",
                success=False,
                error=f"Cannot parse time: '{when}'. For now, use format like '10m', '1h', '30s'.",
            )

        reminder_id = str(uuid.uuid4())[:8]
        self._timers[reminder_id] = {
            "id": reminder_id,
            "type": "reminder",
            "duration_seconds": seconds,
            "message": message,
            "remaining": seconds,
            "created_at": time.time(),
        }

        thread = threading.Thread(
            target=self._run_timer,
            args=(reminder_id, seconds, f"🔔 Reminder: {message}"),
            daemon=True,
        )
        thread.start()

        mins = seconds // 60
        return self._result(
            "create_reminder",
            success=True,
            result=f"🔔 Reminder set for {mins} minutes: \"{message}\" (ID: {reminder_id})",
        )

    def _list_timers(self) -> ActionResult:
        if not self._timers:
            return self._result("list_active", success=True, result="No active timers.")
        lines = []
        for t in self._timers.values():
            remaining = max(0, t["remaining"])
            mins, secs = divmod(int(remaining), 60)
            lines.append(f"• [{t['id']}] {t['type']}: {mins}m{secs}s — \"{t['message']}\"")
        return self._result("list_active", success=True, result="Active timers:\n" + "\n".join(lines))

    def _cancel_timer(self, timer_id: str) -> ActionResult:
        if timer_id in self._timers:
            del self._timers[timer_id]
            return self._result("cancel", success=True, result=f"Cancelled timer {timer_id}")
        return self._result("cancel", success=False, error=f"Timer {timer_id} not found")

    def _run_timer(self, timer_id: str, seconds: int, message: str) -> None:
        """Background countdown."""
        for i in range(seconds):
            time.sleep(1)
            if timer_id not in self._timers:
                return  # Cancelled
            self._timers[timer_id]["remaining"] = seconds - i - 1

        # Timer finished
        if timer_id in self._timers:
            del self._timers[timer_id]

        logger.info("Timer finished: {} — {}", timer_id, message)

        # Try desktop notification
        try:
            import subprocess
            subprocess.run(
                ["notify-send", "Jarvis Timer", message],
                timeout=5,
                capture_output=True,
            )
        except Exception:
            pass
