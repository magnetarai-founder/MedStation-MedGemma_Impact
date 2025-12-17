"""
Undo/Redo Action Service

Manages reversible actions with automatic timeout cleanup.
Supports undo functionality for user actions like:
- Message sent
- Workflow created/updated
- File uploaded
- Settings changed
- User action modifications

Features:
- Action history tracking with state snapshots
- Automatic timeout cleanup (default 5 seconds)
- Action type registry
- State preservation for rollback
- Audit logging of undo actions
"""

from enum import Enum
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta, UTC
import sqlite3
import json
from pathlib import Path
import logging
import asyncio

from pydantic import BaseModel

logger = logging.getLogger(__name__)


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
    """Undoable action model"""
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
    """Result of an undo operation"""
    success: bool
    action_id: int
    action_type: ActionType
    resource_type: str
    resource_id: str
    message: str


class UndoService:
    """
    Service for managing undo/redo actions
    """

    def __init__(self, db_path: Optional[Path] = None, default_timeout: int = 5):
        """
        Initialize undo service

        Args:
            db_path: Path to database (defaults to data dir)
            default_timeout: Default timeout in seconds for undo actions
        """
        if db_path is None:
            from config_paths import get_data_dir
            data_dir = get_data_dir()
            db_path = data_dir / "elohimos_app.db"

        self.db_path = db_path
        self.default_timeout = default_timeout
        self._undo_handlers: Dict[ActionType, Callable] = {}
        self._init_db()

    def _init_db(self):
        """Initialize undo actions table"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS undo_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                user_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                state_before TEXT NOT NULL,
                state_after TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_undone INTEGER DEFAULT 0,
                undone_at TEXT,
                timeout_seconds INTEGER DEFAULT 5
            )
        """)

        # Create index for expiration cleanup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_undo_expires
            ON undo_actions(expires_at, is_undone)
        """)

        # Create index for user lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_undo_user
            ON undo_actions(user_id, is_undone)
        """)

        conn.commit()
        conn.close()

        logger.info("Undo service initialized")

    def register_undo_handler(self, action_type: ActionType, handler: Callable):
        """
        Register a handler function for undoing an action type

        Args:
            action_type: Type of action
            handler: Async function that performs the undo
                    Signature: async def handler(action: UndoAction) -> bool
        """
        self._undo_handlers[action_type] = handler
        logger.info(f"Registered undo handler for {action_type.value}")

    def create_action(
        self,
        action_type: ActionType,
        user_id: str,
        resource_type: str,
        resource_id: str,
        state_before: Dict[str, Any],
        state_after: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None
    ) -> UndoAction:
        """
        Create a new undoable action

        Args:
            action_type: Type of action
            user_id: User who performed the action
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            state_before: State before the action (for rollback)
            state_after: State after the action (optional)
            timeout_seconds: Custom timeout (default: service default)

        Returns:
            Created undo action
        """
        timeout = timeout_seconds or self.default_timeout
        created_at = datetime.now(UTC)
        expires_at = created_at + timedelta(seconds=timeout)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO undo_actions
            (action_type, user_id, resource_type, resource_id, state_before, state_after,
             created_at, expires_at, timeout_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            action_type.value,
            user_id,
            resource_type,
            resource_id,
            json.dumps(state_before),
            json.dumps(state_after) if state_after else None,
            created_at.isoformat(),
            expires_at.isoformat(),
            timeout
        ))

        action_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Created undo action {action_id}: {action_type.value} for {resource_type}/{resource_id}")

        return UndoAction(
            id=action_id,
            action_type=action_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            state_before=state_before,
            state_after=state_after,
            created_at=created_at.isoformat(),
            expires_at=expires_at.isoformat(),
            timeout_seconds=timeout
        )

    def get_action(self, action_id: int) -> Optional[UndoAction]:
        """
        Get an undo action by ID

        Args:
            action_id: Action ID

        Returns:
            Undo action or None
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, action_type, user_id, resource_type, resource_id,
                   state_before, state_after, created_at, expires_at,
                   is_undone, undone_at, timeout_seconds
            FROM undo_actions
            WHERE id = ?
        """, (action_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return UndoAction(
            id=row[0],
            action_type=ActionType(row[1]),
            user_id=row[2],
            resource_type=row[3],
            resource_id=row[4],
            state_before=json.loads(row[5]),
            state_after=json.loads(row[6]) if row[6] else None,
            created_at=row[7],
            expires_at=row[8],
            is_undone=bool(row[9]),
            undone_at=row[10],
            timeout_seconds=row[11]
        )

    def get_pending_actions(self, user_id: str, limit: int = 10) -> list[UndoAction]:
        """
        Get pending (not undone, not expired) actions for a user

        Args:
            user_id: User ID
            limit: Maximum number of actions

        Returns:
            List of pending undo actions
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            SELECT id, action_type, user_id, resource_type, resource_id,
                   state_before, state_after, created_at, expires_at,
                   is_undone, undone_at, timeout_seconds
            FROM undo_actions
            WHERE user_id = ? AND is_undone = 0 AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, now, limit))

        rows = cursor.fetchall()
        conn.close()

        actions = []
        for row in rows:
            actions.append(UndoAction(
                id=row[0],
                action_type=ActionType(row[1]),
                user_id=row[2],
                resource_type=row[3],
                resource_id=row[4],
                state_before=json.loads(row[5]),
                state_after=json.loads(row[6]) if row[6] else None,
                created_at=row[7],
                expires_at=row[8],
                is_undone=bool(row[9]),
                undone_at=row[10],
                timeout_seconds=row[11]
            ))

        return actions

    async def undo_action(self, action_id: int, user_id: str) -> UndoResult:
        """
        Undo an action

        Args:
            action_id: Action ID to undo
            user_id: User requesting the undo (must match action user)

        Returns:
            Result of undo operation
        """
        action = self.get_action(action_id)

        if not action:
            return UndoResult(
                success=False,
                action_id=action_id,
                action_type=ActionType.MESSAGE_SENT,
                resource_type="unknown",
                resource_id="unknown",
                message="Action not found"
            )

        # Check if user owns the action
        if action.user_id != user_id:
            return UndoResult(
                success=False,
                action_id=action_id,
                action_type=action.action_type,
                resource_type=action.resource_type,
                resource_id=action.resource_id,
                message="Unauthorized: action belongs to different user"
            )

        # Check if already undone
        if action.is_undone:
            return UndoResult(
                success=False,
                action_id=action_id,
                action_type=action.action_type,
                resource_type=action.resource_type,
                resource_id=action.resource_id,
                message="Action already undone"
            )

        # Check if expired
        expires_at = datetime.fromisoformat(action.expires_at)
        if datetime.now(UTC) > expires_at:
            return UndoResult(
                success=False,
                action_id=action_id,
                action_type=action.action_type,
                resource_type=action.resource_type,
                resource_id=action.resource_id,
                message="Action expired (timeout exceeded)"
            )

        # Execute undo handler if registered
        handler = self._undo_handlers.get(action.action_type)
        if handler:
            try:
                success = await handler(action)
                if not success:
                    return UndoResult(
                        success=False,
                        action_id=action_id,
                        action_type=action.action_type,
                        resource_type=action.resource_type,
                        resource_id=action.resource_id,
                        message="Undo handler failed"
                    )
            except Exception as e:
                logger.error(f"Undo handler error for {action_id}: {e}")
                return UndoResult(
                    success=False,
                    action_id=action_id,
                    action_type=action.action_type,
                    resource_type=action.resource_type,
                    resource_id=action.resource_id,
                    message=f"Undo handler error: {str(e)}"
                )

        # Mark as undone
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE undo_actions
            SET is_undone = 1, undone_at = ?
            WHERE id = ?
        """, (datetime.now(UTC).isoformat(), action_id))

        conn.commit()
        conn.close()

        logger.info(f"Undone action {action_id}: {action.action_type.value}")

        # Log to audit system
        try:
            from audit_logger import audit_log_sync, AuditAction
            audit_log_sync(
                user_id=user_id,
                action="action.undone",
                resource=action.resource_type,
                resource_id=action.resource_id,
                details={
                    "action_type": action.action_type.value,
                    "original_action_id": action_id
                }
            )
        except Exception as e:
            logger.debug(f"Could not log undo to audit: {e}")

        return UndoResult(
            success=True,
            action_id=action_id,
            action_type=action.action_type,
            resource_type=action.resource_type,
            resource_id=action.resource_id,
            message="Action undone successfully"
        )

    def cleanup_expired_actions(self, days_to_keep: int = 7) -> int:
        """
        Delete expired and old undo actions

        Args:
            days_to_keep: Keep actions for this many days

        Returns:
            Number of actions deleted
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cutoff_date = datetime.now(UTC) - timedelta(days=days_to_keep)

        cursor.execute("""
            DELETE FROM undo_actions
            WHERE created_at < ?
        """, (cutoff_date.isoformat(),))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old undo actions")

        return deleted

    def get_action_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about undo actions

        Args:
            user_id: Optional user filter

        Returns:
            Statistics dictionary
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Count by action type
        query = """
            SELECT action_type, COUNT(*), SUM(is_undone)
            FROM undo_actions
        """
        params = []

        if user_id:
            query += " WHERE user_id = ?"
            params.append(user_id)

        query += " GROUP BY action_type"

        cursor.execute(query, params)
        action_stats = {}
        for row in cursor.fetchall():
            action_stats[row[0]] = {
                "total_count": row[1],
                "undone_count": row[2],
                "undo_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0
            }

        conn.close()

        return {
            "action_types": action_stats
        }


# Global undo service instance
_undo_service: Optional[UndoService] = None


def get_undo_service() -> UndoService:
    """
    Get or create global undo service instance

    Returns:
        UndoService instance
    """
    global _undo_service

    if _undo_service is None:
        _undo_service = UndoService()

    return _undo_service
