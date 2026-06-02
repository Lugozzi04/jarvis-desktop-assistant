"""Habit API — event tracking, analysis, suggestion management."""

from __future__ import annotations

from fastapi import APIRouter

from backend.core.logger import logger

router = APIRouter(tags=["habits"])


@router.get("/habits/events")
def get_events(limit: int = 50):
    """Get recent habit events."""
    try:
        from backend.habit_learning.engine import habit_tracker
        return {"events": habit_tracker.get_events(limit)}
    except Exception as exc:
        return {"events": [], "error": str(exc)}


@router.get("/habits/suggestions")
def get_suggestions():
    """Get all suggestions."""
    try:
        from backend.habit_learning.engine import habit_tracker
        return {"suggestions": habit_tracker.get_suggestions()}
    except Exception as exc:
        return {"suggestions": [], "error": str(exc)}


@router.post("/habits/analyze")
def analyze_habits():
    """Run pattern analysis."""
    try:
        from backend.habit_learning.engine import habit_tracker
        suggestions = habit_tracker.analyze()
        return {"status": "analyzed", "suggestion_count": len(suggestions)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.post("/habits/suggestions/{suggestion_id}/accept")
def accept_suggestion(suggestion_id: str):
    """Accept a suggestion — creates the proposed automation/workflow."""
    try:
        from backend.habit_learning.engine import habit_tracker
        return habit_tracker.accept_suggestion(suggestion_id)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.post("/habits/suggestions/{suggestion_id}/dismiss")
def dismiss_suggestion(suggestion_id: str):
    """Dismiss a suggestion."""
    try:
        from backend.habit_learning.engine import habit_tracker
        return habit_tracker.dismiss_suggestion(suggestion_id)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.post("/habits/clear-events")
def clear_events():
    """Clear all events (privacy)."""
    try:
        from backend.habit_learning.engine import habit_tracker
        return habit_tracker.clear_events()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.post("/habits/clear-suggestions")
def clear_suggestions():
    """Clear all suggestions."""
    try:
        from backend.habit_learning.engine import habit_tracker
        return habit_tracker.clear_suggestions()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.post("/habits/track")
def track_event(event_type: str, metadata: dict | None = None):
    """Track a habit event."""
    try:
        from backend.habit_learning.engine import habit_tracker
        event = habit_tracker.track(event_type, metadata or {})
        return {"status": "tracked", "event_id": event.id}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
