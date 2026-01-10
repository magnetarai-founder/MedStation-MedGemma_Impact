"""
Kanban Projects - Project and Board management

Provides CRUD operations for Projects and Boards in the Kanban workspace.

Extracted from kanban_service.py during P2 decomposition.
"""

from __future__ import annotations

import secrets
from typing import Any, Dict, List, Optional

from .kanban_core import _utcnow, _conn


# ===== Projects =====

def list_projects() -> List[Dict[str, Any]]:
    """List all projects ordered by creation date (newest first)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT project_id, name, description, created_at FROM projects ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def create_project(name: str, description: Optional[str] = None) -> Dict[str, Any]:
    """Create a new project.

    Args:
        name: Project name (required, max 255 chars)
        description: Optional project description

    Returns:
        Created project dict

    Raises:
        ValueError: If name is empty or exceeds length limit
    """
    if not name or not name.strip():
        raise ValueError("Project name cannot be empty")
    if len(name) > 255:
        raise ValueError("Project name cannot exceed 255 characters")

    pid = secrets.token_urlsafe(12)
    now = _utcnow()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO projects(project_id, name, description, created_at) VALUES (?,?,?,?)",
            (pid, name.strip(), description, now),
        )
        conn.commit()
        return {
            "project_id": pid,
            "name": name.strip(),
            "description": description,
            "created_at": now,
        }


# ===== Boards =====

def list_boards(project_id: str) -> List[Dict[str, Any]]:
    """List all boards for a project ordered by creation date (newest first)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT board_id, project_id, name, created_at FROM boards WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_board(project_id: str, name: str) -> Dict[str, Any]:
    """Create a new board within a project.

    Args:
        project_id: ID of the parent project
        name: Board name (required, max 255 chars)

    Returns:
        Created board dict

    Raises:
        ValueError: If project doesn't exist or name is invalid
    """
    if not name or not name.strip():
        raise ValueError("Board name cannot be empty")
    if len(name) > 255:
        raise ValueError("Board name cannot exceed 255 characters")

    bid = secrets.token_urlsafe(12)
    now = _utcnow()
    with _conn() as conn:
        # Validate project exists
        project_row = conn.execute(
            "SELECT project_id FROM projects WHERE project_id = ?", (project_id,)
        ).fetchone()
        if not project_row:
            raise ValueError(f"Project not found: {project_id}")

        conn.execute(
            "INSERT INTO boards(board_id, project_id, name, created_at) VALUES (?,?,?,?)",
            (bid, project_id, name.strip(), now),
        )
        conn.commit()
        return {"board_id": bid, "project_id": project_id, "name": name.strip(), "created_at": now}


__all__ = [
    "list_projects",
    "create_project",
    "list_boards",
    "create_board",
]
