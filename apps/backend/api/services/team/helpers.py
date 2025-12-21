"""
Team Service Helper Functions

Utility functions for team membership checks, permission enforcement,
and database connections.
"""

import sqlite3
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _get_app_conn() -> sqlite3.Connection:
    """Get connection to app_db with row factory"""
    from api.config_paths import get_config_paths  # Lazy import
    PATHS = get_config_paths()
    APP_DB = PATHS.app_db
    conn = sqlite3.connect(str(APP_DB))
    conn.row_factory = sqlite3.Row
    return conn


def is_team_member(team_id: str, user_id: str) -> Optional[str]:
    """
    Check if user is a member of the team.

    Args:
        team_id: Team ID
        user_id: User ID

    Returns:
        User's role if they are a member, None otherwise
    """
    conn = _get_app_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT role FROM team_members
        WHERE team_id = ? AND user_id = ? AND is_active = 1
    """, (team_id, user_id))
    row = cur.fetchone()
    conn.close()
    return row["role"] if row else None


def require_team_admin(team_id: str, user_id: str) -> None:
    """
    Raise HTTPException(403) if user is not a team admin (super_admin or admin).

    Args:
        team_id: Team ID
        user_id: User ID

    Raises:
        HTTPException: If user is not an admin
    """
    from fastapi import HTTPException  # Lazy import
    role = is_team_member(team_id, user_id)
    if role not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="Team admin required")


def get_team_manager() -> Any:
    """
    Get singleton TeamManager instance.

    Returns:
        TeamManager instance
    """
    from api.services.team.core import TeamManager
    global _team_manager
    if '_team_manager' not in globals():
        _team_manager = TeamManager()
    return _team_manager
