"""
Workflow Storage

Main WorkflowStorage class that composes all CRUD mixins.
SQLite persistence for workflows and work items.
"""

import logging
from typing import Optional

from api.workflow_storage.base import get_db_path
from api.workflow_storage.schema import init_database
from api.workflow_storage.workflows import WorkflowCRUD
from api.workflow_storage.work_items import WorkItemCRUD
from api.workflow_storage.starring import StarringMixin

logger = logging.getLogger(__name__)


class WorkflowStorage(WorkflowCRUD, WorkItemCRUD, StarringMixin):
    """
    SQLite storage for workflows and work items.

    Schema:
    - workflows: Workflow definitions
    - work_items: Work item instances
    - stage_transitions: Audit trail of stage changes
    - attachments: File attachments
    - starred_workflows: User favorites

    This class composes functionality from:
    - WorkflowCRUD: Workflow save/get/list/delete
    - WorkItemCRUD: Work item save/get/list
    - StarringMixin: Star/unstar workflows
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = get_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        init_database(self.db_path)
        logger.info(f"📦 Workflow storage initialized: {self.db_path}")


# Singleton instance
_workflow_storage: Optional[WorkflowStorage] = None


def get_workflow_storage() -> WorkflowStorage:
    """Get singleton workflow storage instance."""
    global _workflow_storage

    if _workflow_storage is None:
        _workflow_storage = WorkflowStorage()
        logger.info("📦 Workflow storage singleton created")

    return _workflow_storage


def _reset_workflow_storage() -> None:
    """Reset the global instance - for testing only."""
    global _workflow_storage
    _workflow_storage = None
