"""
Kanban Core - Database utilities and schema management

This module provides the shared database connection and schema initialization
for all Kanban service modules.

Extracted from kanban_service.py during P2 decomposition.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, UTC

from api.config_paths import PATHS

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    """Return current UTC time as ISO format string."""
    return datetime.now(UTC).isoformat()


def _conn() -> sqlite3.Connection:
    """
    Create a database connection with proper settings.

    Returns:
        sqlite3.Connection configured with Row factory and foreign keys enabled
    """
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


__all__ = [
    "_utcnow",
    "_conn",
    "ensure_schema",
]
