"""Timer API — expose active timers to the frontend."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/timers")
async def list_timers():
    """Return all active timers (for frontend countdown display)."""
    try:
        from backend.core.registry import skill_registry
        timer_skill = skill_registry.get_skill("timers")
        if timer_skill and hasattr(timer_skill, "_timers"):
            timers = []
            now = __import__("time").time()
            for t_id, t_data in list(timer_skill._timers.items()):
                elapsed = now - t_data["created_at"]
                remaining = max(0, t_data["duration_seconds"] - elapsed)
                timers.append({
                    "id": t_id,
                    "type": t_data["type"],
                    "message": t_data["message"],
                    "total_seconds": t_data["duration_seconds"],
                    "remaining_seconds": round(remaining),
                    "remaining_display": f"{int(remaining // 60)}m{int(remaining % 60)}s",
                })
            # Remove finished timers
            timer_skill._timers = {
                k: v for k, v in timer_skill._timers.items()
                if now - v["created_at"] < v["duration_seconds"]
            }
            return {"timers": timers, "count": len(timers)}
    except Exception:
        pass
    return {"timers": [], "count": 0}
