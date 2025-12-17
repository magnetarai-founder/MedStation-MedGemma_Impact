"""
Agent Session Storage (Phase C)

SQLite-based persistence for agent workspace sessions.
Stores session metadata, current plans, and activity tracking.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC

try:
    from api.agent.orchestration.models import AgentSession
    from api.config_paths import get_config_paths
except ImportError:
    from .models import AgentSession
    try:
        from config_paths import get_config_paths
    except ImportError:
        from api.config_paths import get_config_paths

logger = logging.getLogger(__name__)

# Module-level DB initialization flag
_db_initialized = False


def get_db_path() -> Path:
    """Get path to agent sessions database"""
    paths = get_config_paths()
    return Path(paths.data_dir) / "agent_sessions.db"


def _get_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Initialize database schema.

    Creates agent_sessions table if it doesn't exist.
    Safe to call multiple times (idempotent).
    """
    global _db_initialized
    if _db_initialized:
        return

    conn = _get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            repo_root TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_activity_at TEXT NOT NULL,
            status TEXT NOT NULL,
            current_plan TEXT,
            attached_work_item_id TEXT
        )
        """
    )

    # Create index on user_id for faster lookups
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id
        ON agent_sessions(user_id)
        """
    )

    # Create index on status for filtering active sessions
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_status
        ON agent_sessions(status)
        """
    )

    conn.commit()
    conn.close()

    _db_initialized = True
    logger.info(f"Agent sessions database initialized: {get_db_path()}")


def create_session(session: AgentSession) -> None:
    """
    Create a new agent session.

    Args:
        session: AgentSession object to persist

    Raises:
        sqlite3.IntegrityError: If session with same ID already exists
    """
    init_db()  # Ensure DB is initialized

    conn = _get_connection()
    cur = conn.cursor()

    # Serialize current_plan to JSON if present
    current_plan_json = json.dumps(session.current_plan) if session.current_plan else None

    cur.execute(
        """
        INSERT INTO agent_sessions
            (id, user_id, repo_root, created_at, last_activity_at,
             status, current_plan, attached_work_item_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session.id,
            session.user_id,
            session.repo_root,
            session.created_at.isoformat(),
            session.last_activity_at.isoformat(),
            session.status,
            current_plan_json,
            session.attached_work_item_id,
        ),
    )

    conn.commit()
    conn.close()

    logger.info(f"Created agent session {session.id} for user {session.user_id}")


def row_to_session(row: sqlite3.Row) -> AgentSession:
    """
    Convert database row to AgentSession object.

    Args:
        row: sqlite3.Row from query

    Returns:
        AgentSession object
    """
    # Parse JSON fields
    current_plan = None
    if row["current_plan"]:
        try:
            current_plan = json.loads(row["current_plan"])
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse current_plan for session {row['id']}")

    return AgentSession(
        id=row["id"],
        user_id=row["user_id"],
        repo_root=row["repo_root"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_activity_at=datetime.fromisoformat(row["last_activity_at"]),
        status=row["status"],
        current_plan=current_plan,
        attached_work_item_id=row["attached_work_item_id"],
    )


def get_session(session_id: str) -> Optional[AgentSession]:
    """
    Get session by ID.

    Args:
        session_id: Session identifier

    Returns:
        AgentSession if found, None otherwise
    """
    init_db()  # Ensure DB is initialized

    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM agent_sessions WHERE id = ?", (session_id,))
    row = cur.fetchone()

    conn.close()

    return row_to_session(row) if row else None


def list_sessions_for_user(user_id: str, status_filter: Optional[str] = None) -> List[AgentSession]:
    """
    List all sessions for a user.

    Args:
        user_id: User identifier
        status_filter: Optional status filter (e.g., "active")

    Returns:
        List of AgentSession objects, ordered by last_activity_at DESC
    """
    init_db()  # Ensure DB is initialized

    conn = _get_connection()
    cur = conn.cursor()

    if status_filter:
        cur.execute(
            """
            SELECT * FROM agent_sessions
            WHERE user_id = ? AND status = ?
            ORDER BY last_activity_at DESC
            """,
            (user_id, status_filter),
        )
    else:
        cur.execute(
            """
            SELECT * FROM agent_sessions
            WHERE user_id = ?
            ORDER BY last_activity_at DESC
            """,
            (user_id,),
        )

    rows = cur.fetchall()
    conn.close()

    return [row_to_session(r) for r in rows]


def update_session(session_id: str, updates: Dict[str, Any]) -> None:
    """
    Update session fields.

    Args:
        session_id: Session identifier
        updates: Dict of field names to values

    Supported update fields:
        - status: str
        - current_plan: Dict[str, Any]
        - last_activity_at: datetime
        - attached_work_item_id: str

    Example:
        update_session("session_123", {
            "current_plan": {...},
            "last_activity_at": datetime.now(UTC)
        })
    """
    init_db()  # Ensure DB is initialized

    conn = _get_connection()
    cur = conn.cursor()

    fields = []
    values = []

    for key, value in updates.items():
        if key == "current_plan":
            fields.append("current_plan = ?")
            values.append(json.dumps(value) if value is not None else None)
        elif key in ("last_activity_at", "created_at") and isinstance(value, datetime):
            fields.append(f"{key} = ?")
            values.append(value.isoformat())
        elif key in ("status", "attached_work_item_id", "repo_root", "user_id"):
            fields.append(f"{key} = ?")
            values.append(value)
        else:
            logger.warning(f"Ignoring unknown update field: {key}")

    if not fields:
        conn.close()
        return

    values.append(session_id)

    cur.execute(
        f"UPDATE agent_sessions SET {', '.join(fields)} WHERE id = ?",
        values,
    )

    conn.commit()
    conn.close()

    logger.debug(f"Updated session {session_id}: {list(updates.keys())}")


def archive_session(session_id: str) -> None:
    """
    Archive a session (sets status to 'archived').

    Args:
        session_id: Session identifier
    """
    update_session(
        session_id,
        {
            "status": "archived",
            "last_activity_at": datetime.now(UTC),
        }
    )

    logger.info(f"Archived session {session_id}")


def delete_session(session_id: str) -> None:
    """
    Permanently delete a session.

    Args:
        session_id: Session identifier

    Note: Prefer archive_session() for soft delete
    """
    init_db()  # Ensure DB is initialized

    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM agent_sessions WHERE id = ?", (session_id,))

    conn.commit()
    conn.close()

    logger.info(f"Deleted session {session_id}")


# Initialize database on module import
init_db()
