"""Conversations API — list, create, get, delete conversations."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.chat_store import conversation_store
from backend.core.logger import logger

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    llm_model: str


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    llm_model: str
    messages: list[dict]


@router.get("")
def list_conversations():
    """List all conversations (newest first)."""
    convs = conversation_store.list()
    return {"conversations": convs}


@router.post("")
def create_conversation():
    """Create a new empty conversation."""
    conv = conversation_store.create()
    return conv


@router.get("/{conv_id}")
def get_conversation(conv_id: str):
    """Get a full conversation with messages."""
    conv = conversation_store.get(conv_id)
    if not conv:
        return {"error": "Conversation not found"}
    return {
        "id": conv["id"],
        "title": conv["title"],
        "created_at": conv["created_at"],
        "updated_at": conv["updated_at"],
        "llm_model": conv.get("llm_model", ""),
        "messages": conv.get("messages", []),
    }


@router.delete("/{conv_id}")
def delete_conversation(conv_id: str):
    """Delete a conversation."""
    if conversation_store.delete(conv_id):
        return {"success": True}
    return {"error": "Conversation not found"}


@router.put("/{conv_id}/title")
def update_title(conv_id: str, title: str):
    """Update conversation title."""
    if conversation_store.update_title(conv_id, title):
        return {"success": True}
    return {"error": "Conversation not found"}
