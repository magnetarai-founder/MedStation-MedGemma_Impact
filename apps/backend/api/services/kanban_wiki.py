"""
Kanban Wiki - Comments and Wiki Page management

Provides CRUD operations for task Comments and project Wiki Pages
in the Kanban workspace.

Extracted from kanban_service.py during P2 decomposition.
"""

from __future__ import annotations

import secrets
from typing import Any, Dict, List, Optional

from .kanban_core import _utcnow, _conn


# ===== Comments =====

def list_comments(task_id: str) -> List[Dict[str, Any]]:
    """List all comments for a task ordered by creation date."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT comment_id, task_id, user_id, content, created_at FROM comments WHERE task_id=? ORDER BY created_at ASC",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_comment(task_id: str, user_id: str, content: str) -> Dict[str, Any]:
    """Create a comment on a task.

    Args:
        task_id: ID of the parent task
        user_id: ID of the commenting user
        content: Comment content (required, max 10000 chars)

    Returns:
        Created comment dict

    Raises:
        ValueError: If task doesn't exist or content is invalid
    """
    if not content or not content.strip():
        raise ValueError("Comment content cannot be empty")
    if len(content) > 10000:
        raise ValueError("Comment content cannot exceed 10000 characters")

    cid = secrets.token_urlsafe(12)
    now = _utcnow()
    with _conn() as conn:
        # Validate task exists
        task_row = conn.execute(
            "SELECT task_id FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        if not task_row:
            raise ValueError(f"Task not found: {task_id}")

        conn.execute(
            "INSERT INTO comments(comment_id, task_id, user_id, content, created_at) VALUES (?,?,?,?,?)",
            (cid, task_id, user_id, content.strip(), now),
        )
        conn.commit()
        return {"comment_id": cid, "task_id": task_id, "user_id": user_id, "content": content.strip(), "created_at": now}


# ===== Wiki Pages =====

def list_wiki_pages(project_id: str) -> List[Dict[str, Any]]:
    """List all wiki pages for a project ordered by creation date (newest first)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT page_id, project_id, title, content, created_at, updated_at FROM wiki_pages WHERE project_id=? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_wiki_page(project_id: str, title: str, content: Optional[str] = None) -> Dict[str, Any]:
    """Create a wiki page within a project.

    Args:
        project_id: ID of the parent project
        title: Page title (required, max 500 chars)
        content: Optional page content (markdown)

    Returns:
        Created wiki page dict

    Raises:
        ValueError: If project doesn't exist or title is invalid
    """
    if not title or not title.strip():
        raise ValueError("Wiki page title cannot be empty")
    if len(title) > 500:
        raise ValueError("Wiki page title cannot exceed 500 characters")

    pid = secrets.token_urlsafe(12)
    now = _utcnow()
    with _conn() as conn:
        # Validate project exists
        project_row = conn.execute(
            "SELECT project_id FROM projects WHERE project_id = ?", (project_id,)
        ).fetchone()
        if not project_row:
            raise ValueError(f"Project not found: {project_id}")

        conn.execute(
            "INSERT INTO wiki_pages(page_id, project_id, title, content, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (pid, project_id, title.strip(), content or "", now, now),
        )
        conn.commit()
        return {"page_id": pid, "project_id": project_id, "title": title.strip(), "content": content or "", "created_at": now, "updated_at": now}


def update_wiki_page(page_id: str, *, title: Optional[str] = None, content: Optional[str] = None) -> Dict[str, Any]:
    """Update a wiki page's title and/or content.

    Args:
        page_id: ID of the wiki page to update
        title: Optional new title
        content: Optional new content

    Returns:
        Updated wiki page dict

    Raises:
        ValueError: If wiki page not found
    """
    with _conn() as conn:
        row = conn.execute("SELECT * FROM wiki_pages WHERE page_id=?", (page_id,)).fetchone()
        if not row:
            raise ValueError("Wiki page not found")
        new_title = title if title is not None else row["title"]
        new_content = content if content is not None else row["content"]
        now = _utcnow()
        conn.execute(
            "UPDATE wiki_pages SET title=?, content=?, updated_at=? WHERE page_id=?",
            (new_title, new_content, now, page_id),
        )
        conn.commit()
        return {
            "page_id": page_id,
            "project_id": row["project_id"],
            "title": new_title,
            "content": new_content,
            "created_at": row["created_at"],
            "updated_at": now,
        }


def delete_wiki_page(page_id: str) -> None:
    """Delete a wiki page.

    Args:
        page_id: Wiki page ID

    Raises:
        ValueError: If wiki page not found
    """
    with _conn() as conn:
        row = conn.execute("SELECT * FROM wiki_pages WHERE page_id=?", (page_id,)).fetchone()
        if not row:
            raise ValueError("Wiki page not found")
        conn.execute("DELETE FROM wiki_pages WHERE page_id=?", (page_id,))
        conn.commit()


__all__ = [
    # Comments
    "list_comments",
    "create_comment",
    # Wiki Pages
    "list_wiki_pages",
    "create_wiki_page",
    "update_wiki_page",
    "delete_wiki_page",
]
