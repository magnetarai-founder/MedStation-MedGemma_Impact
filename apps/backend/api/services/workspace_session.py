#!/usr/bin/env python3
"""
Workspace Session Manager for MagnetarCode

Provides unified session IDs across Chat, Terminal, and Code context.
Uses the BaseRepository pattern for consistent database operations.
"""
# ruff: noqa: S608

import json
import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from api.services.db import BaseRepository, DatabaseConnection

logger = logging.getLogger(__name__)

# Data directory for MagnetarCode
DATA_DIR = Path(os.path.expanduser("~/.magnetarcode/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class WorkspaceSession:
    """A unified workspace session entity."""

    session_id: str
    user_id: str
    workspace_root: str | None = None
    chat_id: str | None = None
    terminal_id: str | None = None
    active_files: list[str] = field(default_factory=list)
    created_at: str = ""
    last_activity: str = ""
    is_active: bool = True


class WorkspaceSessionRepository(BaseRepository[WorkspaceSession]):
    """
    Repository for workspace sessions.

    Extends BaseRepository to provide consistent database access patterns
    with thread-local connection pooling and WAL mode.
    """

    @property
    def table_name(self) -> str:
        return "workspace_sessions"

    def _create_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS workspace_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                workspace_root TEXT,
                chat_id TEXT,
                terminal_id TEXT,
                active_files TEXT,
                created_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """

    def _row_to_entity(self, row: sqlite3.Row) -> WorkspaceSession:
        return WorkspaceSession(
            session_id=row["session_id"],
            user_id=row["user_id"],
            workspace_root=row["workspace_root"],
            chat_id=row["chat_id"],
            terminal_id=row["terminal_id"],
            active_files=json.loads(row["active_files"]) if row["active_files"] else [],
            created_at=row["created_at"],
            last_activity=row["last_activity"],
            is_active=bool(row["is_active"]),
        )

    def _run_migrations(self):
        """Create indexes for efficient queries."""
        self._create_index(["user_id", "last_activity"], name="idx_workspace_user")
        self._create_index(["workspace_root"], name="idx_workspace_root")


class WorkspaceSessionManager:
    """
    Manages unified workspace sessions across all MagnetarCode tabs.

    A workspace session represents a single coding/work session that:
    - Spans across Chat, Terminal, Code, and Agent tabs
    - Has a consistent session_id for unified context
    - Tracks active workspace root and files
    - Persists across tab switches
    """

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = DATA_DIR / "workspace_sessions.db"

        self._db = DatabaseConnection(db_path)
        self._repo = WorkspaceSessionRepository(self._db)

    def create_session(
        self, user_id: str, workspace_root: str | None = None, chat_id: str | None = None
    ) -> str:
        """
        Create a new workspace session.

        Args:
            user_id: User ID
            workspace_root: Path to workspace root (optional)
            chat_id: Associated chat session ID (optional)

        Returns:
            session_id
        """
        session_id = f"ws_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        self._repo.insert(
            {
                "session_id": session_id,
                "user_id": user_id,
                "workspace_root": workspace_root,
                "chat_id": chat_id,
                "active_files": None,
                "terminal_id": None,
                "created_at": now,
                "last_activity": now,
                "is_active": 1,
            }
        )

        logger.info(f"Created workspace session {session_id} for user {user_id}")
        return session_id

    def get_or_create_for_workspace(self, user_id: str, workspace_root: str) -> str:
        """
        Get existing session for workspace root or create new one.

        Args:
            user_id: User ID
            workspace_root: Path to workspace root

        Returns:
            session_id
        """
        sessions = self._repo.find_where(
            "user_id = ? AND workspace_root = ? AND is_active = 1",
            (user_id, workspace_root),
            order_by="last_activity DESC",
            limit=1,
        )

        if sessions:
            self.update_activity(sessions[0].session_id)
            return sessions[0].session_id

        return self.create_session(user_id, workspace_root)

    def get_or_create_for_chat(
        self, user_id: str, chat_id: str, workspace_root: str | None = None
    ) -> str:
        """
        Get existing session for chat or create new one.

        Args:
            user_id: User ID
            chat_id: Chat session ID
            workspace_root: Path to workspace root (optional)

        Returns:
            session_id
        """
        sessions = self._repo.find_where(
            "user_id = ? AND chat_id = ? AND is_active = 1",
            (user_id, chat_id),
            limit=1,
        )

        if sessions:
            self.update_activity(sessions[0].session_id)
            return sessions[0].session_id

        return self.create_session(user_id, workspace_root, chat_id)

    def link_chat(self, session_id: str, chat_id: str):
        """Link a chat session to workspace session."""
        self._repo.update_where(
            {"chat_id": chat_id, "last_activity": datetime.utcnow().isoformat()},
            "session_id = ?",
            (session_id,),
        )

    def link_terminal(self, session_id: str, terminal_id: str):
        """Link a terminal session to workspace session."""
        self._repo.update_where(
            {"terminal_id": terminal_id, "last_activity": datetime.utcnow().isoformat()},
            "session_id = ?",
            (session_id,),
        )

    def update_workspace_root(self, session_id: str, workspace_root: str):
        """Update workspace root for session."""
        self._repo.update_where(
            {"workspace_root": workspace_root, "last_activity": datetime.utcnow().isoformat()},
            "session_id = ?",
            (session_id,),
        )

    def update_active_files(self, session_id: str, file_paths: list[str]):
        """Update active files for session."""
        self._repo.update_where(
            {"active_files": json.dumps(file_paths), "last_activity": datetime.utcnow().isoformat()},
            "session_id = ?",
            (session_id,),
        )

    def update_activity(self, session_id: str):
        """Update last activity timestamp."""
        self._repo.update_where(
            {"last_activity": datetime.utcnow().isoformat()},
            "session_id = ?",
            (session_id,),
        )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session info."""
        session = self._repo.find_by_id(session_id, id_column="session_id")
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "workspace_root": session.workspace_root,
            "chat_id": session.chat_id,
            "terminal_id": session.terminal_id,
            "active_files": session.active_files,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "is_active": session.is_active,
        }

    def list_user_sessions(self, user_id: str, active_only: bool = True) -> list[dict[str, Any]]:
        """List all sessions for a user."""
        where = "user_id = ?"
        params = [user_id]

        if active_only:
            where += " AND is_active = 1"

        sessions = self._repo.find_where(where, tuple(params), order_by="last_activity DESC")

        return [
            {
                "session_id": s.session_id,
                "user_id": s.user_id,
                "workspace_root": s.workspace_root,
                "chat_id": s.chat_id,
                "terminal_id": s.terminal_id,
                "active_files": s.active_files,
                "created_at": s.created_at,
                "last_activity": s.last_activity,
                "is_active": s.is_active,
            }
            for s in sessions
        ]

    def close_session(self, session_id: str):
        """Mark session as inactive."""
        self._repo.update_where(
            {"is_active": 0, "last_activity": datetime.utcnow().isoformat()},
            "session_id = ?",
            (session_id,),
        )
        logger.info(f"Closed workspace session {session_id}")


# Global instance
_workspace_session_manager: WorkspaceSessionManager | None = None


def get_workspace_session_manager() -> WorkspaceSessionManager:
    """Get global workspace session manager instance."""
    global _workspace_session_manager
    if _workspace_session_manager is None:
        _workspace_session_manager = WorkspaceSessionManager()
    return _workspace_session_manager
