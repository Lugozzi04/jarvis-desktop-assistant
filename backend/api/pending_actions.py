"""Pending Actions API — approve/reject/list security-gated actions."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from backend.core.pending_actions import pending_queue
from backend.core.logger import logger

router = APIRouter(prefix="/api/pending-actions", tags=["pending-actions"])


class RejectBody(BaseModel):
    reason: str | None = None


class CleanupBody(BaseModel):
    retention_hours: int = 1


@router.get("")
def list_pending():
    """List all pending (unresolved) actions."""
    actions = pending_queue.get_pending()
    return {
        "actions": [a.model_dump() for a in actions],
        "count": len(actions),
    }


@router.get("/all")
def list_all(limit: int = 50):
    """List all actions including resolved ones."""
    actions = pending_queue.get_all()[:limit]
    return {
        "actions": [a.model_dump() for a in actions],
        "count": len(actions),
    }


@router.get("/count")
def get_count():
    """Get count of pending actions only."""
    return {"count": pending_queue.count()}


@router.get("/{action_id}")
def get_action(action_id: str):
    """Get a specific action by ID with full status and details."""
    pa = pending_queue.get(action_id)
    if not pa:
        raise HTTPException(status_code=404, detail="Action not found")
    return pa.model_dump()


@router.post("/{action_id}/approve")
def approve_action(action_id: str, execute: bool = False):
    """Approve a pending action. Optionally execute it immediately."""
    if not pending_queue.approve(action_id):
        raise HTTPException(status_code=404, detail="Action not found or already resolved")

    if execute:
        pending_queue.execute(action_id)
        pa = pending_queue.get(action_id)
        logger.info("Pending action approved and executed: {}", action_id)
        return {"status": "approved_executed", "result": pa.result if pa else None, "id": action_id}

    logger.info("Pending action approved: {}", action_id)
    return {"status": "approved", "id": action_id}


@router.post("/{action_id}/reject")
def reject_action(action_id: str, body: RejectBody | None = None):
    """Reject a pending action with an optional rejection reason."""
    reason = body.reason if body else None
    if not pending_queue.reject(action_id, reason=reason):
        raise HTTPException(status_code=404, detail="Action not found or already resolved")

    logger.info("Pending action rejected: {} (reason={})", action_id, reason)
    return {"status": "rejected", "id": action_id, "reject_reason": reason}


@router.post("/cleanup")
def cleanup_actions(body: CleanupBody | None = None):
    """Remove resolved actions older than retention_hours (default 1)."""
    hours = body.retention_hours if body else 1
    removed = pending_queue.auto_cleanup(retention_hours=hours)
    logger.info("Manual cleanup removed {} actions (retention: {}h)", removed, hours)
    return {"status": "cleaned", "removed": removed, "retention_hours": hours}


@router.post("/clear-resolved")
def clear_resolved():
    """Remove resolved actions older than 1 hour."""
    removed = pending_queue.clear_resolved()
    return {"status": "cleared", "removed": removed}
