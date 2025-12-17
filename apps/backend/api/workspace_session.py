#!/usr/bin/env python3
"""
Workspace Session Manager for ElohimOS
Provides unified session IDs across Chat, Terminal, Code, and Agent tabs
"""

import logging
import sqlite3
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Optional, Any
import json

try:
    from .config_paths import get_config_paths
except ImportError:
    from config_paths import get_config_paths

logger = logging.getLogger(__name__)

# Get PATHS for consistent data directory
PATHS = get_config_paths()


class WorkspaceSessionManager:
    """
    Manages unified workspace sessions across all ElohimOS tabs

    A workspace session represents a single coding/work session that:
    - Spans across Chat, Terminal, Code, and Agent tabs
    - Has a consistent session_id for unified context
    - Tracks active workspace root and files
    - Persists across tab switches
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = PATHS.data_dir / "workspace_sessions.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize workspace sessions database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
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
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workspace_user
            ON workspace_sessions(user_id, last_activity DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workspace_root
            ON workspace_sessions(workspace_root)
        """)

        conn.commit()
        conn.close()

    def create_session(
        self,
        user_id: str,
        workspace_root: Optional[str] = None,
        chat_id: Optional[str] = None
    ) -> str:
        """
        Create a new workspace session

        Args:
            user_id: User ID
            workspace_root: Path to workspace root (optional)
            chat_id: Associated chat session ID (optional)

        Returns:
            session_id
        """
        session_id = f"ws_{uuid.uuid4().hex[:12]}"

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            INSERT INTO workspace_sessions
            (session_id, user_id, workspace_root, chat_id, created_at, last_activity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, workspace_root, chat_id, now, now))

        conn.commit()
        conn.close()

        logger.info(f"Created workspace session {session_id} for user {user_id}")
        return session_id

    def get_or_create_for_workspace(
        self,
        user_id: str,
        workspace_root: str
    ) -> str:
        """
        Get existing session for workspace root or create new one

        Args:
            user_id: User ID
            workspace_root: Path to workspace root

        Returns:
            session_id
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check for existing active session for this workspace
        cursor.execute("""
            SELECT session_id FROM workspace_sessions
            WHERE user_id = ? AND workspace_root = ? AND is_active = 1
            ORDER BY last_activity DESC
            LIMIT 1
        """, (user_id, workspace_root))

        row = cursor.fetchone()
        conn.close()

        if row:
            # Update last activity
            self.update_activity(row[0])
            return row[0]
        else:
            # Create new session
            return self.create_session(user_id, workspace_root)

    def get_or_create_for_chat(
        self,
        user_id: str,
        chat_id: str,
        workspace_root: Optional[str] = None
    ) -> str:
        """
        Get existing session for chat or create new one

        Args:
            user_id: User ID
            chat_id: Chat session ID
            workspace_root: Path to workspace root (optional)

        Returns:
            session_id
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check for existing active session for this chat
        cursor.execute("""
            SELECT session_id FROM workspace_sessions
            WHERE user_id = ? AND chat_id = ? AND is_active = 1
            LIMIT 1
        """, (user_id, chat_id))

        row = cursor.fetchone()
        conn.close()

        if row:
            # Update last activity
            self.update_activity(row[0])
            return row[0]
        else:
            # Create new session
            return self.create_session(user_id, workspace_root, chat_id)

    def link_chat(self, session_id: str, chat_id: str):
        """Link a chat session to workspace session"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE workspace_sessions
            SET chat_id = ?, last_activity = ?
            WHERE session_id = ?
        """, (chat_id, datetime.now(UTC).isoformat(), session_id))

        conn.commit()
        conn.close()

    def link_terminal(self, session_id: str, terminal_id: str):
        """Link a terminal session to workspace session"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE workspace_sessions
            SET terminal_id = ?, last_activity = ?
            WHERE session_id = ?
        """, (terminal_id, datetime.now(UTC).isoformat(), session_id))

        conn.commit()
        conn.close()

    def update_workspace_root(self, session_id: str, workspace_root: str):
        """Update workspace root for session"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE workspace_sessions
            SET workspace_root = ?, last_activity = ?
            WHERE session_id = ?
        """, (workspace_root, datetime.now(UTC).isoformat(), session_id))

        conn.commit()
        conn.close()

    def update_active_files(self, session_id: str, file_paths: list[str]):
        """Update active files for session"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE workspace_sessions
            SET active_files = ?, last_activity = ?
            WHERE session_id = ?
        """, (json.dumps(file_paths), datetime.now(UTC).isoformat(), session_id))

        conn.commit()
        conn.close()

    def update_activity(self, session_id: str):
        """Update last activity timestamp"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE workspace_sessions
            SET last_activity = ?
            WHERE session_id = ?
        """, (datetime.now(UTC).isoformat(), session_id))

        conn.commit()
        conn.close()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session info"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT session_id, user_id, workspace_root, chat_id, terminal_id,
                   active_files, created_at, last_activity, is_active
            FROM workspace_sessions
            WHERE session_id = ?
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'session_id': row[0],
            'user_id': row[1],
            'workspace_root': row[2],
            'chat_id': row[3],
            'terminal_id': row[4],
            'active_files': json.loads(row[5]) if row[5] else [],
            'created_at': row[6],
            'last_activity': row[7],
            'is_active': bool(row[8])
        }

    def list_user_sessions(self, user_id: str, active_only: bool = True) -> list[Dict[str, Any]]:
        """List all sessions for a user"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        query = """
            SELECT session_id, user_id, workspace_root, chat_id, terminal_id,
                   active_files, created_at, last_activity, is_active
            FROM workspace_sessions
            WHERE user_id = ?
        """
        params = [user_id]

        if active_only:
            query += " AND is_active = 1"

        query += " ORDER BY last_activity DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        sessions = []
        for row in rows:
            sessions.append({
                'session_id': row[0],
                'user_id': row[1],
                'workspace_root': row[2],
                'chat_id': row[3],
                'terminal_id': row[4],
                'active_files': json.loads(row[5]) if row[5] else [],
                'created_at': row[6],
                'last_activity': row[7],
                'is_active': bool(row[8])
            })

        return sessions

    def close_session(self, session_id: str):
        """Mark session as inactive"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE workspace_sessions
            SET is_active = 0, last_activity = ?
            WHERE session_id = ?
        """, (datetime.now(UTC).isoformat(), session_id))

        conn.commit()
        conn.close()

        logger.info(f"Closed workspace session {session_id}")


# Global instance
_workspace_session_manager = None

def get_workspace_session_manager() -> WorkspaceSessionManager:
    """Get global workspace session manager instance"""
    global _workspace_session_manager
    if _workspace_session_manager is None:
        _workspace_session_manager = WorkspaceSessionManager()
    return _workspace_session_manager
