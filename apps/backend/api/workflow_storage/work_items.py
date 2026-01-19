"""
Workflow Storage - Work Item CRUD

Save, get, and list work item operations.
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional

from api.workflow_models import WorkItem, WorkItemStatus

from api.workflow_storage.converters import (
    row_to_work_item,
    row_to_transition,
    row_to_attachment,
)

logger = logging.getLogger(__name__)


class WorkItemCRUD:
    """Work item CRUD operations mixin."""

    db_path: Path  # Provided by WorkflowStorage

    def save_work_item(self, work_item: WorkItem, user_id: str) -> None:
        """
        Save work item to database.

        Args:
            work_item: Work item to save
            user_id: User ID for isolation
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO work_items
            (id, workflow_id, workflow_name, current_stage_id, current_stage_name,
             status, priority, assigned_to, claimed_at, data, created_by,
             created_at, updated_at, completed_at, sla_due_at, is_overdue,
             tags, reference_number, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                work_item.id,
                work_item.workflow_id,
                work_item.workflow_name,
                work_item.current_stage_id,
                work_item.current_stage_name,
                work_item.status.value,
                work_item.priority.value,
                work_item.assigned_to,
                work_item.claimed_at.isoformat() if work_item.claimed_at else None,
                json.dumps(work_item.data),
                work_item.created_by,
                work_item.created_at.isoformat(),
                work_item.updated_at.isoformat(),
                work_item.completed_at.isoformat() if work_item.completed_at else None,
                work_item.sla_due_at.isoformat() if work_item.sla_due_at else None,
                1 if work_item.is_overdue else 0,
                json.dumps(work_item.tags),
                work_item.reference_number,
                user_id,
            ),
        )

        # Save stage transitions
        for transition in work_item.history:
            cursor.execute(
                """
                INSERT INTO stage_transitions
                (work_item_id, from_stage_id, to_stage_id, transitioned_at,
                 transitioned_by, notes, duration_seconds, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    work_item.id,
                    transition.from_stage_id,
                    transition.to_stage_id,
                    transition.transitioned_at.isoformat(),
                    transition.transitioned_by,
                    transition.notes,
                    transition.duration_seconds,
                    user_id,
                ),
            )

        # Save attachments
        for attachment in work_item.attachments:
            cursor.execute(
                """
                INSERT OR REPLACE INTO attachments
                (id, work_item_id, filename, file_path, file_size, mime_type,
                 uploaded_by, uploaded_at, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    attachment.id,
                    work_item.id,
                    attachment.filename,
                    attachment.file_path,
                    attachment.file_size,
                    attachment.mime_type,
                    attachment.uploaded_by,
                    attachment.uploaded_at.isoformat(),
                    user_id,
                ),
            )

        conn.commit()
        conn.close()

        logger.debug(f"💾 Saved work item: {work_item.id}")

    def get_work_item(self, work_item_id: str, user_id: str) -> Optional[WorkItem]:
        """
        Get work item by ID.

        Args:
            work_item_id: Work item ID
            user_id: User ID for isolation

        Returns:
            Work item or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM work_items
            WHERE id = ? AND user_id = ?
        """,
            (work_item_id, user_id),
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        work_item = row_to_work_item(row)

        # Load transitions
        cursor.execute(
            """
            SELECT * FROM stage_transitions
            WHERE work_item_id = ? AND user_id = ?
            ORDER BY transitioned_at ASC
        """,
            (work_item_id, user_id),
        )
        transitions = cursor.fetchall()
        work_item.history = [row_to_transition(t) for t in transitions]

        # Load attachments
        cursor.execute(
            """
            SELECT * FROM attachments
            WHERE work_item_id = ? AND user_id = ?
            ORDER BY uploaded_at ASC
        """,
            (work_item_id, user_id),
        )
        attachments = cursor.fetchall()
        work_item.attachments = [row_to_attachment(a) for a in attachments]

        conn.close()
        return work_item

    def get_work_item_by_id(self, work_item_id: str) -> Optional[WorkItem]:
        """
        Get work item by ID without user isolation (admin/webhook use).

        This method bypasses user isolation and should only be used by
        system processes like webhooks that don't have user context.

        Args:
            work_item_id: Work item ID

        Returns:
            Work item or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM work_items
            WHERE id = ?
        """,
            (work_item_id,),
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        work_item = row_to_work_item(row)

        # Load transitions (using owner's user_id)
        cursor.execute(
            """
            SELECT * FROM stage_transitions
            WHERE work_item_id = ?
            ORDER BY transitioned_at ASC
        """,
            (work_item_id,),
        )
        transitions = cursor.fetchall()
        work_item.history = [row_to_transition(t) for t in transitions]

        # Load attachments
        cursor.execute(
            """
            SELECT * FROM attachments
            WHERE work_item_id = ?
            ORDER BY uploaded_at ASC
        """,
            (work_item_id,),
        )
        attachments = cursor.fetchall()
        work_item.attachments = [row_to_attachment(a) for a in attachments]

        conn.close()
        return work_item

    def list_work_items(
        self,
        user_id: str,
        workflow_id: Optional[str] = None,
        status: Optional[WorkItemStatus] = None,
        assigned_to: Optional[str] = None,
        limit: int = 50,
    ) -> List[WorkItem]:
        """
        List work items with filters.

        Args:
            user_id: User ID for isolation
            workflow_id: Filter by workflow
            status: Filter by status
            assigned_to: Filter by assigned user
            limit: Max results

        Returns:
            List of work items
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM work_items WHERE user_id = ?"
        params: list = [user_id]

        if workflow_id:
            query += " AND workflow_id = ?"
            params.append(workflow_id)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if assigned_to:
            query += " AND assigned_to = ?"
            params.append(assigned_to)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [row_to_work_item(row) for row in rows]
