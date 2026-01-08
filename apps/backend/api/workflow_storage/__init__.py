"""
Workflow Storage Package

SQLite persistence for workflows and work items.

Components:
- base.py: Database path and connection utilities
- schema.py: Table definitions and migrations
- converters.py: Row-to-model conversion helpers
- workflows.py: Workflow CRUD operations
- work_items.py: Work item CRUD operations
- starring.py: Star/unstar functionality
- storage.py: Main WorkflowStorage class (composes all mixins)
"""

# Main class and singleton
from api.workflow_storage.storage import (
    WorkflowStorage,
    get_workflow_storage,
    _reset_workflow_storage,
)

# Converters for external use (e.g., tests)
from api.workflow_storage.converters import (
    row_to_workflow,
    row_to_work_item,
    row_to_transition,
    row_to_attachment,
)

# Schema initialization (for testing/setup)
from api.workflow_storage.schema import init_database

# Base utilities
from api.workflow_storage.base import get_db_path, get_connection

__all__ = [
    # Main class
    "WorkflowStorage",
    "get_workflow_storage",
    "_reset_workflow_storage",
    # Converters
    "row_to_workflow",
    "row_to_work_item",
    "row_to_transition",
    "row_to_attachment",
    # Schema
    "init_database",
    # Base
    "get_db_path",
    "get_connection",
]
