"""Pending Actions API — approve/reject/list security-gated actions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.core.pending_actions import pending_queue
from backend.core.logger import logger

router = APIRouter(prefix="/api/pending-actions", tags=["pending-actions"])


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
    """Get a specific action by ID."""
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
        pending_queue.execute_approved(action_id)
        pa = pending_queue.get(action_id)
        logger.info("Pending action approved and executed: {}", action_id)
        return {"status": "approved_executed", "result": pa.result if pa else None}

    logger.info("Pending action approved: {}", action_id)
    return {"status": "approved"}


@router.post("/{action_id}/reject")
def reject_action(action_id: str):
    """Reject a pending action."""
    if not pending_queue.reject(action_id):
        raise HTTPException(status_code=404, detail="Action not found or already resolved")

    logger.info("Pending action rejected: {}", action_id)
    return {"status": "rejected"}


@router.post("/clear-resolved")
def clear_resolved():
    """Remove resolved actions older than 1 hour."""
    pending_queue.clear_resolved()
    return {"status": "cleared"}
