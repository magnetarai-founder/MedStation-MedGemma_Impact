"""
Workflow Storage - Starring

Star/unstar workflow functionality for quick access.
"""

import sqlite3
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class StarringMixin:
    """Starring functionality mixin."""

    db_path: Path  # Provided by WorkflowStorage

    def star_workflow(self, workflow_id: str, user_id: str) -> bool:
        """
        Star a workflow for a user (max 5 per workflow type).

        Args:
            workflow_id: Workflow ID to star
            user_id: User ID

        Returns:
            bool: True if starred successfully, False if limit reached
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get workflow type
            cursor.execute(
                "SELECT workflow_type FROM workflows WHERE id = ?", (workflow_id,)
            )
            workflow_row = cursor.fetchone()
            if not workflow_row:
                conn.close()
                return False

            workflow_type = workflow_row['workflow_type']

            # Count existing starred workflows of same type for this user
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM starred_workflows sw
                JOIN workflows w ON sw.workflow_id = w.id
                WHERE sw.user_id = ? AND w.workflow_type = ?
            """,
                (user_id, workflow_type),
            )

            count = cursor.fetchone()['count']

            # Check limit (5 per type)
            if count >= 5:
                conn.close()
                return False

            # Star the workflow
            now = datetime.now(UTC).isoformat()
            cursor.execute(
                """
                INSERT OR IGNORE INTO starred_workflows (user_id, workflow_id, starred_at)
                VALUES (?, ?, ?)
            """,
                (user_id, workflow_id, now),
            )

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error starring workflow: {e}")
            conn.close()
            return False

    def unstar_workflow(self, workflow_id: str, user_id: str) -> None:
        """
        Unstar a workflow for a user.

        Args:
            workflow_id: Workflow ID to unstar
            user_id: User ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM starred_workflows
            WHERE user_id = ? AND workflow_id = ?
        """,
            (user_id, workflow_id),
        )

        conn.commit()
        conn.close()

    def get_starred_workflows(
        self, user_id: str, workflow_type: Optional[str] = None
    ) -> List[str]:
        """
        Get list of starred workflow IDs for a user.

        Args:
            user_id: User ID
            workflow_type: Optional filter by workflow type

        Returns:
            List of workflow IDs
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if workflow_type:
            cursor.execute(
                """
                SELECT sw.workflow_id
                FROM starred_workflows sw
                JOIN workflows w ON sw.workflow_id = w.id
                WHERE sw.user_id = ? AND w.workflow_type = ?
                ORDER BY sw.starred_at DESC
            """,
                (user_id, workflow_type),
            )
        else:
            cursor.execute(
                """
                SELECT workflow_id
                FROM starred_workflows
                WHERE user_id = ?
                ORDER BY starred_at DESC
            """,
                (user_id,),
            )

        workflow_ids = [row['workflow_id'] for row in cursor.fetchall()]
        conn.close()
        return workflow_ids

    def is_workflow_starred(self, workflow_id: str, user_id: str) -> bool:
        """
        Check if a workflow is starred by a user.

        Args:
            workflow_id: Workflow ID
            user_id: User ID

        Returns:
            bool: True if starred, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 1 FROM starred_workflows
            WHERE user_id = ? AND workflow_id = ?
        """,
            (user_id, workflow_id),
        )

        result = cursor.fetchone()
        conn.close()
        return result is not None
