"""
Kanban Service - Facade Module

SQLite-backed service providing Projects, Boards, Columns, Tasks, Comments,
and Wiki pages for the Kanban workspace.

This module serves as a backward-compatible facade that re-exports functions
from extracted modules. Direct imports from extracted modules are preferred
for new code.

Extracted modules (P2 decomposition):
- kanban_core.py: Database utilities and schema management
- kanban_projects.py: Project and Board CRUD
- kanban_tasks.py: Column and Task CRUD, movement, rebalancing
- kanban_wiki.py: Comment and Wiki Page CRUD
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Re-export from extracted modules for backward compatibility
from .kanban_core import (
    _utcnow,
    _conn,
    ensure_schema,
)

from .kanban_projects import (
    list_projects,
    create_project,
    list_boards,
    create_board,
)

from .kanban_tasks import (
    list_columns,
    next_position_for_column,
    create_column,
    update_column,
    list_tasks,
    _next_task_position,
    create_task,
    update_task,
    move_task,
    rebalance_column,
)

from .kanban_wiki import (
    list_comments,
    create_comment,
    list_wiki_pages,
    create_wiki_page,
    update_wiki_page,
    delete_wiki_page,
)

# Ensure schema at import time (safe, idempotent)
ensure_schema()


__all__ = [
    # Core
    "_utcnow",
    "_conn",
    "ensure_schema",
    # Projects
    "list_projects",
    "create_project",
    # Boards
    "list_boards",
    "create_board",
    # Columns
    "list_columns",
    "next_position_for_column",
    "create_column",
    "update_column",
    # Tasks
    "list_tasks",
    "_next_task_position",
    "create_task",
    "update_task",
    "move_task",
    "rebalance_column",
    # Comments
    "list_comments",
    "create_comment",
    # Wiki
    "list_wiki_pages",
    "create_wiki_page",
    "update_wiki_page",
    "delete_wiki_page",
]
