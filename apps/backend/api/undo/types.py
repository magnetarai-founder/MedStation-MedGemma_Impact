"""
Undo Types - Enums and models for undo/redo functionality

Extracted from undo_service.py during P2 decomposition.
Contains:
- ActionType enum (types of undoable actions)
- UndoAction model (undoable action data)
- UndoResult model (result of undo operation)
"""

from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel


class ActionType(str, Enum):
    """Types of undoable actions"""
    MESSAGE_SENT = "message_sent"
    MESSAGE_DELETED = "message_deleted"
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_UPDATED = "workflow_updated"
    WORKFLOW_DELETED = "workflow_deleted"
    FILE_UPLOADED = "file_uploaded"
    FILE_DELETED = "file_deleted"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_ROLE_CHANGED = "user_role_changed"
    SETTINGS_CHANGED = "settings_changed"
    VAULT_ITEM_CREATED = "vault_item_created"
    VAULT_ITEM_UPDATED = "vault_item_updated"
    VAULT_ITEM_DELETED = "vault_item_deleted"


class UndoAction(BaseModel):
    """Undoable action model

    Attributes:
        id: Action ID (auto-generated)
        action_type: Type of action
        user_id: User who performed the action
        resource_type: Type of resource affected
        resource_id: ID of resource affected
        state_before: State before the action (for rollback)
        state_after: State after the action (optional)
        created_at: When action was created
        expires_at: When action expires (cannot be undone after)
        is_undone: Whether action has been undone
        undone_at: When action was undone
        timeout_seconds: Timeout for undo window
    """
    id: Optional[int] = None
    action_type: ActionType
    user_id: str
    resource_type: str
    resource_id: str
    state_before: Dict[str, Any]
    state_after: Optional[Dict[str, Any]] = None
    created_at: str
    expires_at: str
    is_undone: bool = False
    undone_at: Optional[str] = None
    timeout_seconds: int = 5


class UndoResult(BaseModel):
    """Result of an undo operation

    Attributes:
        success: Whether undo was successful
        action_id: ID of the action
        action_type: Type of action
        resource_type: Type of resource
        resource_id: ID of resource
        message: Human-readable result message
    """
    success: bool
    action_id: int
    action_type: ActionType
    resource_type: str
    resource_id: str
    message: str


__all__ = [
    # Enum
    "ActionType",
    # Models
    "UndoAction",
    "UndoResult",
]
