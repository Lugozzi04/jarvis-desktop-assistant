"""Habit Learning Engine — event tracking, pattern analysis, suggestions.

Lightweight MVP: tracks events, detects patterns, generates suggestions.
No ML — uses simple rule-based pattern detection.
Privacy-safe: does NOT store full chat content or personal data.
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.logger import logger


# ── Models ──

class HabitEvent(BaseModel):
    """A single tracked event."""

    id: str = Field(default_factory=lambda: f"evt_{int(time.time() * 1000)}")
    event_type: str  # skill_action, workflow_run, automation_run, app_opened, chat_command, timer_created
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)
    session_id: str = "default"


class HabitSuggestion(BaseModel):
    """A suggestion generated from pattern analysis."""

    id: str = Field(default_factory=lambda: f"sug_{int(time.time() * 1000)}")
    type: str  # automation, workflow, shortcut, reminder
    title: str
    description: str
    confidence: float = 0.5
    evidence: str = ""
    proposed_automation: dict[str, Any] | None = None
    proposed_workflow: dict[str, Any] | None = None
    status: str = "pending"  # pending, accepted, dismissed
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Storage ──

def _events_file() -> Path:
    return Path(settings.data_dir) / "habit_events.json"


def _suggestions_file() -> Path:
    return Path(settings.data_dir) / "habit_suggestions.json"


# ── Pattern Analyzer ──

class PatternAnalyzer:
    """Detects patterns from habit events and generates suggestions."""

    MIN_OCCURRENCES = 3  # Minimum events to detect a pattern
    TIME_WINDOW_MINUTES = 30  # Co-occurrence window

    @staticmethod
    def analyze(events: list[HabitEvent]) -> list[HabitSuggestion]:
        """Analyze events and generate suggestions."""
        suggestions: list[HabitSuggestion] = []
        if len(events) < PatternAnalyzer.MIN_OCCURRENCES:
            return suggestions

        # 1. Repeated skill actions
        suggestions.extend(PatternAnalyzer._detect_repeated_actions(events))

        # 2. Co-occurring actions
        suggestions.extend(PatternAnalyzer._detect_co_occurring(events))

        # 3. Repeated workflows
        suggestions.extend(PatternAnalyzer._detect_repeated_workflows(events))

        # 4. App + workflow patterns
        suggestions.extend(PatternAnalyzer._detect_app_workflow_patterns(events))

        return suggestions

    @staticmethod
    def _detect_repeated_actions(events: list[HabitEvent]) -> list[HabitSuggestion]:
        """Detect skill actions repeated frequently."""
        skill_actions = [
            e for e in events
            if e.event_type == "skill_action"
        ]

        # Group by (skill, action, hour_bucket)
        action_buckets: dict[str, list[HabitEvent]] = defaultdict(list)
        for e in skill_actions:
            skill = e.metadata.get("skill", "")
            action = e.metadata.get("action", "")
            if not skill or not action:
                continue
            ts = datetime.fromisoformat(e.timestamp)
            hour_bucket = ts.strftime("%H:00")
            key = f"{skill}.{action}@{hour_bucket}"
            action_buckets[key].append(e)

        suggestions = []
        for key, events_list in action_buckets.items():
            if len(events_list) >= PatternAnalyzer.MIN_OCCURRENCES:
                parts = key.split("@")
                skill_action = parts[0].split(".")
                hour = parts[1] if len(parts) > 1 else ""

                suggestion = HabitSuggestion(
                    type="automation",
                    title=f"Automate {skill_action[0]}.{skill_action[1]}",
                    description=f"You've used {skill_action[0]}.{skill_action[1]} {len(events_list)} times{' around ' + hour if hour else ''}. Would you like to automate it?",
                    confidence=min(0.5 + len(events_list) * 0.1, 0.95),
                    evidence=f"{len(events_list)} occurrences detected",
                    proposed_automation={
                        "name": f"Auto {skill_action[0]}.{skill_action[1]}",
                        "description": f"Automated from habit — {len(events_list)} uses detected",
                        "enabled": False,
                        "trigger": {
                            "type": "time",
                            "config": {"time": hour.replace(":00", ":00"), "days": ["mon", "tue", "wed", "thu", "fri"]},
                        } if hour else {"type": "manual", "config": {}},
                        "conditions": [],
                        "actions": [
                            {"type": "skill_action", "skill": skill_action[0], "action": skill_action[1], "parameters": {}, "risk": "safe"},
                        ],
                    },
                )
                suggestions.append(suggestion)

        return suggestions

    @staticmethod
    def _detect_co_occurring(events: list[HabitEvent]) -> list[HabitSuggestion]:
        """Detect actions that happen together within a time window."""
        suggestions = []

        # Group by session/timestamp proximity
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        clusters: list[list[HabitEvent]] = []
        current_cluster: list[HabitEvent] = []

        for event in sorted_events:
            ts = datetime.fromisoformat(event.timestamp)
            if not current_cluster:
                current_cluster.append(event)
            else:
                last_ts = datetime.fromisoformat(current_cluster[-1].timestamp)
                if (ts - last_ts).total_seconds() <= PatternAnalyzer.TIME_WINDOW_MINUTES * 60:
                    current_cluster.append(event)
                else:
                    if len(current_cluster) >= 2:
                        clusters.append(current_cluster)
                    current_cluster = [event]

        if len(current_cluster) >= 2:
            clusters.append(current_cluster)

        # Find repeated clusters
        cluster_signatures = defaultdict(int)
        for cluster in clusters:
            sig = tuple(sorted(
                f"{e.event_type}:{e.metadata.get('skill', '')}.{e.metadata.get('action', '')}"
                for e in cluster if e.event_type in ("skill_action", "workflow_run", "app_opened")
            ))
            if len(sig) >= 2:
                cluster_signatures[sig] += 1

        for sig, count in cluster_signatures.items():
            if count >= PatternAnalyzer.MIN_OCCURRENCES:
                workflow_steps = []
                for i, s in enumerate(sig):
                    parts = s.split(":", 1)
                    etype = parts[0]
                    detail = parts[1] if len(parts) > 1 else ""
                    d_parts = detail.split(".")
                    if etype == "skill_action" and len(d_parts) >= 2:
                        workflow_steps.append({
                            "order": i + 1,
                            "skill": d_parts[0],
                            "action": d_parts[1],
                            "parameters": {},
                            "description": f"Auto-{d_parts[1]}",
                        })
                    elif etype == "app_opened":
                        workflow_steps.append({
                            "order": i + 1,
                            "skill": "apps",
                            "action": "open",
                            "parameters": {"app_name": detail},
                            "description": f"Open {detail}",
                        })

                if workflow_steps:
                    suggestions.append(HabitSuggestion(
                        type="workflow",
                        title=f"Create workflow from {count} co-occurring actions",
                        description=f"These {len(workflow_steps)} actions happen together {count} times. Create a workflow?",
                        confidence=min(0.4 + count * 0.15, 0.9),
                        evidence=f"{count} co-occurrence clusters detected",
                        proposed_workflow={
                            "name": "Auto-generated Workflow",
                            "description": f"Detected from {count} co-occurrences",
                            "steps": workflow_steps,
                        },
                    ))

        return suggestions

    @staticmethod
    def _detect_repeated_workflows(events: list[HabitEvent]) -> list[HabitSuggestion]:
        """Detect repeatedly run workflows."""
        workflow_runs = [e for e in events if e.event_type == "workflow_run"]
        workflow_counts = Counter(
            e.metadata.get("workflow_id", "") for e in workflow_runs
        )

        suggestions = []
        for wf_id, count in workflow_counts.items():
            if count >= PatternAnalyzer.MIN_OCCURRENCES and wf_id:
                suggestions.append(HabitSuggestion(
                    type="automation",
                    title=f"Automate workflow '{wf_id}'",
                    description=f"You've run '{wf_id}' {count} times. Create a shortcut?",
                    confidence=min(0.5 + count * 0.1, 0.9),
                    evidence=f"{count} workflow runs detected",
                    proposed_automation={
                        "name": f"Run {wf_id}",
                        "description": f"Auto-run workflow {wf_id}",
                        "enabled": False,
                        "trigger": {"type": "manual", "config": {}},
                        "conditions": [],
                        "actions": [{"type": "workflow", "workflow_id": wf_id, "parameters": {}, "risk": "safe"}],
                    },
                ))
        return suggestions

    @staticmethod
    def _detect_app_workflow_patterns(events: list[HabitEvent]) -> list[HabitSuggestion]:
        """Detect app_opened followed by workflow within time window."""
        suggestions = []
        app_events = {e.id: e for e in events if e.event_type == "app_opened"}
        wf_events = {e.id: e for e in events if e.event_type == "workflow_run"}

        patterns = defaultdict(int)
        for a_id, a_event in app_events.items():
            a_ts = datetime.fromisoformat(a_event.timestamp)
            app_name = a_event.metadata.get("app_name", "")

            for w_id, w_event in wf_events.items():
                w_ts = datetime.fromisoformat(w_event.timestamp)
                diff = (w_ts - a_ts).total_seconds()
                if 0 < diff <= PatternAnalyzer.TIME_WINDOW_MINUTES * 60:
                    wf_name = w_event.metadata.get("workflow_id", "")
                    key = f"{app_name}→{wf_name}"
                    patterns[key] += 1

        for key, count in patterns.items():
            if count >= PatternAnalyzer.MIN_OCCURRENCES:
                parts = key.split("→")
                app_name = parts[0]
                wf_id = parts[1] if len(parts) > 1 else ""
                suggestions.append(HabitSuggestion(
                    type="automation",
                    title=f"Automate: open {app_name} → run {wf_id}",
                    description=f"When you open {app_name}, you often run {wf_id} ({count} times).",
                    confidence=min(0.5 + count * 0.1, 0.9),
                    evidence=f"{count} app→workflow patterns detected",
                    proposed_automation={
                        "name": f"{app_name} → {wf_id}",
                        "description": f"Auto-run {wf_id} when {app_name} opens",
                        "enabled": False,
                        "trigger": {"type": "app_opened", "config": {"app_name": app_name}},
                        "conditions": [],
                        "actions": [{"type": "workflow", "workflow_id": wf_id, "parameters": {}, "risk": "safe"}],
                    },
                ))
        return suggestions


# ── Tracker ──

class HabitTracker:
    """Tracks user actions and generates suggestions."""

    _instance = None
    _enabled_default = True  # Can be disabled via settings

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._events: list[HabitEvent] = []
            cls._instance._suggestions: list[HabitSuggestion] = []
            cls._instance._loaded = False
        return cls._instance

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._load_events()
        self._load_suggestions()
        self._loaded = True

    def _load_events(self):
        try:
            if _events_file().exists():
                data = json.loads(_events_file().read_text())
                self._events = [HabitEvent(**e) for e in data[-1000:]]  # Keep last 1000
        except Exception:
            self._events = []

    def _load_suggestions(self):
        try:
            if _suggestions_file().exists():
                data = json.loads(_suggestions_file().read_text())
                self._suggestions = [HabitSuggestion(**s) for s in data]
        except Exception:
            self._suggestions = []

    def _save_events(self):
        try:
            _events_file().parent.mkdir(parents=True, exist_ok=True)
            data = [e.model_dump() for e in self._events[-1000:]]
            _events_file().write_text(json.dumps(data, indent=2))
        except Exception as exc:
            logger.error("Failed to save habit events: {}", exc)

    def _save_suggestions(self):
        try:
            _suggestions_file().parent.mkdir(parents=True, exist_ok=True)
            data = [s.model_dump() for s in self._suggestions]
            _suggestions_file().write_text(json.dumps(data, indent=2))
        except Exception as exc:
            logger.error("Failed to save habit suggestions: {}", exc)

    # ── Public API ──

    def track(
        self,
        event_type: str,
        metadata: dict[str, Any] | None = None,
        session_id: str = "default",
    ) -> HabitEvent:
        """Record a new habit event. Called from skills/automations."""
        self._ensure_loaded()
        event = HabitEvent(
            event_type=event_type,
            metadata=metadata or {},
            session_id=session_id,
        )
        self._events.append(event)
        # Keep only last 1000
        if len(self._events) > 1000:
            self._events = self._events[-1000:]
        self._save_events()
        return event

    def analyze(self) -> list[HabitSuggestion]:
        """Run pattern analysis and generate suggestions."""
        self._ensure_loaded()
        new_suggestions = PatternAnalyzer.analyze(self._events)

        # Deduplicate against existing suggestions
        existing_titles = {s.title for s in self._suggestions}
        for sugg in new_suggestions:
            if sugg.title not in existing_titles:
                self._suggestions.append(sugg)
                existing_titles.add(sugg.title)

        self._save_suggestions()
        logger.info("Habit analysis complete — {} suggestions", len(self._suggestions))
        return self._suggestions

    def get_events(self, limit: int = 50) -> list[dict[str, Any]]:
        self._ensure_loaded()
        return [e.model_dump() for e in self._events[-limit:]]

    def get_suggestions(self) -> list[dict[str, Any]]:
        self._ensure_loaded()
        return [s.model_dump() for s in self._suggestions]

    def accept_suggestion(self, suggestion_id: str) -> dict[str, Any]:
        """Accept a suggestion — create the proposed automation/workflow."""
        self._ensure_loaded()
        for s in self._suggestions:
            if s.id == suggestion_id:
                if s.status != "pending":
                    return {"error": f"Suggestion already {s.status}"}

                # Update status
                s.status = "accepted"
                s.updated_at = datetime.utcnow().isoformat()

                # Create the proposed item
                created = None
                try:
                    if s.proposed_automation:
                        from backend.automation.engine import automation_engine
                        auto_data = s.proposed_automation.copy()
                        if "id" not in auto_data or not auto_data["id"]:
                            auto_data["id"] = auto_data.get("name", "habit-auto").lower().replace(" ", "-")
                        created = automation_engine.create(auto_data)

                    elif s.proposed_workflow:
                        from backend.workflows.engine import workflow_engine
                        wf_data = s.proposed_workflow.copy()
                        if "id" not in wf_data or not wf_data["id"]:
                            wf_data["id"] = wf_data.get("name", "habit-wf").lower().replace(" ", "-")
                        created = workflow_engine.create(wf_data)

                except Exception as exc:
                    logger.error("Failed to create from suggestion: {}", exc)
                    s.status = "pending"  # Rollback

                self._save_suggestions()

                return {
                    "status": "accepted",
                    "suggestion_id": suggestion_id,
                    "created": created,
                }

        return {"error": "Suggestion not found"}

    def dismiss_suggestion(self, suggestion_id: str) -> dict[str, Any]:
        """Dismiss a suggestion."""
        self._ensure_loaded()
        for s in self._suggestions:
            if s.id == suggestion_id:
                if s.status != "pending":
                    return {"error": f"Suggestion already {s.status}"}
                s.status = "dismissed"
                s.updated_at = datetime.utcnow().isoformat()
                self._save_suggestions()
                return {"status": "dismissed", "suggestion_id": suggestion_id}
        return {"error": "Suggestion not found"}

    def clear_events(self) -> dict[str, Any]:
        """Clear all tracked events (privacy)."""
        self._events.clear()
        self._save_events()
        return {"status": "cleared"}

    def clear_suggestions(self) -> dict[str, Any]:
        """Clear all suggestions."""
        self._suggestions.clear()
        self._save_suggestions()
        return {"status": "cleared"}


# Singleton
habit_tracker = HabitTracker()
