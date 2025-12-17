"""
Kanban Service (skeleton)

SQLite-backed service providing Projects, Boards, Columns, Tasks, Comments,
and Wiki pages for the Kanban workspace.

Implementations should:
- Call ensure_schema() once (import time or first use)
- Use PATHS.app_db for storage
- Use ISO timestamps via datetime.now(UTC).isoformat()
- Store tags as JSON strings in tasks.tags
- Use REAL 'position' fields for ordering and provide a rebalance helper
"""

from __future__ import annotations

import json
import logging
import secrets
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.config_paths import PATHS

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(PATHS.app_db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def ensure_schema() -> None:
    """Create Kanban tables and indexes if they don't exist (idempotent)."""
    logger.info("Ensuring Kanban schema exists...")
    with _conn() as conn:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
              project_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              description TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS boards (
              board_id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL,
              name TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS columns (
              column_id TEXT PRIMARY KEY,
              board_id TEXT NOT NULL,
              name TEXT NOT NULL,
              position REAL NOT NULL,
              FOREIGN KEY(board_id) REFERENCES boards(board_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_columns_board_pos ON columns(board_id, position);

            CREATE TABLE IF NOT EXISTS tasks (
              task_id TEXT PRIMARY KEY,
              board_id TEXT NOT NULL,
              column_id TEXT NOT NULL,
              title TEXT NOT NULL,
              description TEXT,
              status TEXT,
              assignee_id TEXT,
              priority TEXT,
              due_date TEXT,
              tags TEXT,
              position REAL NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(board_id) REFERENCES boards(board_id) ON DELETE CASCADE,
              FOREIGN KEY(column_id) REFERENCES columns(column_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_board_col_pos ON tasks(board_id, column_id, position);

            CREATE TABLE IF NOT EXISTS comments (
              comment_id TEXT PRIMARY KEY,
              task_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_comments_task_created ON comments(task_id, created_at);

            CREATE TABLE IF NOT EXISTS wiki_pages (
              page_id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL,
              title TEXT NOT NULL,
              content TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_wiki_project ON wiki_pages(project_id, created_at);
            """
        )
        conn.commit()


# Ensure schema at import time (safe, idempotent)
ensure_schema()


# ===== Projects =====
def list_projects() -> List[Dict[str, Any]]:
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


# ===== Columns =====
def list_columns(board_id: str) -> List[Dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT column_id, board_id, name, position FROM columns WHERE board_id = ? ORDER BY position ASC",
            (board_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def next_position_for_column(board_id: str) -> float:
    with _conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), 0) AS maxpos FROM columns WHERE board_id = ?",
            (board_id,),
        ).fetchone()
        maxpos = float(row["maxpos"]) if row and row["maxpos"] is not None else 0.0
        return maxpos + 1024.0


def create_column(board_id: str, name: str, position: Optional[float] = None) -> Dict[str, Any]:
    """Create a new column within a board.

    Args:
        board_id: ID of the parent board
        name: Column name (required, max 255 chars)
        position: Optional position (auto-calculated if not provided)

    Returns:
        Created column dict

    Raises:
        ValueError: If board doesn't exist or name is invalid
    """
    if not name or not name.strip():
        raise ValueError("Column name cannot be empty")
    if len(name) > 255:
        raise ValueError("Column name cannot exceed 255 characters")

    cid = secrets.token_urlsafe(12)
    with _conn() as conn:
        # Validate board exists
        board_row = conn.execute(
            "SELECT board_id FROM boards WHERE board_id = ?", (board_id,)
        ).fetchone()
        if not board_row:
            raise ValueError(f"Board not found: {board_id}")

        pos = position if position is not None else next_position_for_column(board_id)
        conn.execute(
            "INSERT INTO columns(column_id, board_id, name, position) VALUES (?,?,?,?)",
            (cid, board_id, name.strip(), pos),
        )
        conn.commit()
        return {"column_id": cid, "board_id": board_id, "name": name.strip(), "position": pos}


def update_column(column_id: str, name: Optional[str] = None, position: Optional[float] = None) -> Dict[str, Any]:
    with _conn() as conn:
        # Fetch existing
        row = conn.execute(
            "SELECT column_id, board_id, name, position FROM columns WHERE column_id = ?",
            (column_id,),
        ).fetchone()
        if not row:
            raise ValueError("Column not found")
        new_name = name if name is not None else row["name"]
        new_pos = position if position is not None else row["position"]
        conn.execute(
            "UPDATE columns SET name = ?, position = ? WHERE column_id = ?",
            (new_name, new_pos, column_id),
        )
        conn.commit()
        return {
            "column_id": column_id,
            "board_id": row["board_id"],
            "name": new_name,
            "position": new_pos,
        }


# ===== Tasks =====
def list_tasks(board_id: str, column_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with _conn() as conn:
        if column_id:
            rows = conn.execute(
                """
                SELECT task_id, board_id, column_id, title, description, status, assignee_id,
                       priority, due_date, tags, position, created_at, updated_at
                FROM tasks
                WHERE board_id = ? AND column_id = ?
                ORDER BY position ASC
                """,
                (board_id, column_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT task_id, board_id, column_id, title, description, status, assignee_id,
                       priority, due_date, tags, position, created_at, updated_at
                FROM tasks
                WHERE board_id = ?
                ORDER BY position ASC
                """,
                (board_id,),
            ).fetchall()
        result: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            try:
                d["tags"] = json.loads(d.get("tags") or "[]")
            except Exception:
                d["tags"] = []
            result.append(d)
        return result


def _next_task_position(conn: sqlite3.Connection, column_id: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(MAX(position), 0) AS maxpos FROM tasks WHERE column_id = ?",
        (column_id,),
    ).fetchone()
    maxpos = float(row["maxpos"]) if row and row["maxpos"] is not None else 0.0
    return maxpos + 1024.0


def create_task(
    board_id: str,
    column_id: str,
    title: str,
    description: Optional[str] = None,
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None,
    tags: Optional[List[str]] = None,
    position: Optional[float] = None,
) -> Dict[str, Any]:
    """Create a new task within a column.

    Args:
        board_id: ID of the parent board
        column_id: ID of the column
        title: Task title (required, max 500 chars)
        description: Optional task description
        status: Optional status string
        assignee_id: Optional user ID of assignee
        priority: Optional priority string
        due_date: Optional ISO date string
        tags: Optional list of tag strings
        position: Optional position (auto-calculated if not provided)

    Returns:
        Created task dict

    Raises:
        ValueError: If board/column don't exist or title is invalid
    """
    if not title or not title.strip():
        raise ValueError("Task title cannot be empty")
    if len(title) > 500:
        raise ValueError("Task title cannot exceed 500 characters")

    tid = secrets.token_urlsafe(12)
    now = _utcnow()
    with _conn() as conn:
        # Validate board exists
        board_row = conn.execute(
            "SELECT board_id FROM boards WHERE board_id = ?", (board_id,)
        ).fetchone()
        if not board_row:
            raise ValueError(f"Board not found: {board_id}")

        # Validate column exists and belongs to board
        column_row = conn.execute(
            "SELECT column_id, board_id FROM columns WHERE column_id = ?", (column_id,)
        ).fetchone()
        if not column_row:
            raise ValueError(f"Column not found: {column_id}")
        if column_row["board_id"] != board_id:
            raise ValueError(f"Column {column_id} does not belong to board {board_id}")

        pos = position if position is not None else _next_task_position(conn, column_id)
        conn.execute(
            """
            INSERT INTO tasks(task_id, board_id, column_id, title, description, status, assignee_id,
                              priority, due_date, tags, position, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                tid,
                board_id,
                column_id,
                title.strip(),
                description,
                status,
                assignee_id,
                priority,
                due_date,
                json.dumps(tags or []),
                pos,
                now,
                now,
            ),
        )
        conn.commit()
        return {
            "task_id": tid,
            "board_id": board_id,
            "column_id": column_id,
            "title": title.strip(),
            "description": description,
            "status": status,
            "assignee_id": assignee_id,
            "priority": priority,
            "due_date": due_date,
            "tags": tags or [],
            "position": pos,
            "created_at": now,
            "updated_at": now,
        }


def update_task(task_id: str, **fields: Any) -> Dict[str, Any]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if not row:
            raise ValueError("Task not found")

        # Prepare new values
        def pick(name: str, default: Any) -> Any:
            return fields[name] if name in fields and fields[name] is not None else default

        new = {k: row[k] for k in row.keys()}
        for k in [
            "title",
            "description",
            "status",
            "assignee_id",
            "priority",
            "due_date",
            "column_id",
            "position",
        ]:
            if k in fields and fields[k] is not None:
                new[k] = fields[k]

        # Tags handling
        if "tags" in fields and fields["tags"] is not None:
            new["tags"] = json.dumps(fields["tags"]) if isinstance(fields["tags"], list) else fields["tags"]

        new["updated_at"] = _utcnow()

        conn.execute(
            """
            UPDATE tasks SET title=?, description=?, status=?, assignee_id=?, priority=?, due_date=?,
                           tags=?, column_id=?, position=?, updated_at=?
            WHERE task_id=?
            """,
            (
                new["title"],
                new["description"],
                new["status"],
                new["assignee_id"],
                new["priority"],
                new["due_date"],
                new["tags"] if isinstance(new["tags"], str) else json.dumps(new.get("tags") or []),
                new["column_id"],
                float(new["position"]),
                new["updated_at"],
                task_id,
            ),
        )
        conn.commit()
        # Convert tags to list for return
        try:
            new["tags"] = json.loads(new["tags"]) if isinstance(new.get("tags"), str) else (new.get("tags") or [])
        except Exception:
            new["tags"] = []
        return {"task_id": task_id, **{k: new[k] for k in new.keys()}}


def move_task(
    task_id: str,
    new_column_id: str,
    *,
    before_task_id: Optional[str] = None,
    after_task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Move task to a new column and compute a new position by neighbor averaging.

    Args:
        task_id: ID of task to move
        new_column_id: Target column ID
        before_task_id: Optional task ID that should be before this task
        after_task_id: Optional task ID that should be after this task

    Returns:
        Updated task dict

    Raises:
        ValueError: If task or column not found, or neighbors are invalid
    """
    with _conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            raise ValueError(f"Task not found: {task_id}")

        board_id = row["board_id"]

        # Validate new column exists and belongs to same board
        column_row = conn.execute(
            "SELECT column_id, board_id FROM columns WHERE column_id = ?", (new_column_id,)
        ).fetchone()
        if not column_row:
            raise ValueError(f"Column not found: {new_column_id}")
        if column_row["board_id"] != board_id:
            raise ValueError(f"Column {new_column_id} does not belong to board {board_id}")

        def get_pos(tid: str) -> Optional[float]:
            r = conn.execute("SELECT position FROM tasks WHERE task_id=?", (tid,)).fetchone()
            return float(r["position"]) if r else None

        pos_before = get_pos(before_task_id) if before_task_id else None
        pos_after = get_pos(after_task_id) if after_task_id else None

        # Calculate new position with neighbor averaging
        if pos_before is not None and pos_after is not None:
            delta = abs(pos_after - pos_before)
            # If positions are too close, rebalance column first
            if delta < 1e-6:
                rebalance_column(board_id, new_column_id)
                # Recalculate positions after rebalancing
                pos_before = get_pos(before_task_id) if before_task_id else None
                pos_after = get_pos(after_task_id) if after_task_id else None
                if pos_before is not None and pos_after is not None:
                    new_pos = (pos_before + pos_after) / 2.0
                else:
                    # Fallback if rebalancing somehow failed
                    new_pos = _next_task_position(conn, new_column_id)
            else:
                new_pos = (pos_before + pos_after) / 2.0
        elif pos_before is not None:
            new_pos = pos_before + 1024.0
        elif pos_after is not None:
            new_pos = pos_after - 1024.0
        else:
            new_pos = _next_task_position(conn, new_column_id)

        conn.execute(
            "UPDATE tasks SET column_id=?, position=?, updated_at=? WHERE task_id=?",
            (new_column_id, new_pos, _utcnow(), task_id),
        )
        conn.commit()

        # Fetch and return updated task
        updated_row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        result = dict(updated_row)
        try:
            result["tags"] = json.loads(result.get("tags") or "[]")
        except Exception:
            result["tags"] = []
        return result


def rebalance_column(board_id: str, column_id: str) -> None:
    """Rebalance task positions within a column to prevent precision issues.

    Args:
        board_id: ID of the board
        column_id: ID of the column to rebalance

    This redistributes task positions to 1024.0 intervals, preventing
    floating-point precision issues from repeated drag operations.
    """
    logger.info(f"Rebalancing column {column_id} in board {board_id}")
    with _conn() as conn:
        rows = conn.execute(
            "SELECT task_id FROM tasks WHERE board_id=? AND column_id=? ORDER BY position ASC",
            (board_id, column_id),
        ).fetchall()
        logger.debug(f"Rebalancing {len(rows)} tasks in column {column_id}")
        pos = 1024.0
        for r in rows:
            conn.execute("UPDATE tasks SET position=? WHERE task_id=?", (pos, r["task_id"]))
            pos += 1024.0
        conn.commit()


# ===== Comments =====
def list_comments(task_id: str) -> List[Dict[str, Any]]:
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


# ===== Wiki =====
def list_wiki_pages(project_id: str) -> List[Dict[str, Any]]:
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

