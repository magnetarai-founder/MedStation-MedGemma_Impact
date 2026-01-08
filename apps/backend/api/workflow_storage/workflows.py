"""
Workflow Storage - Workflow CRUD

Save, get, list, and delete workflow operations.
"""

import json
import sqlite3
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Optional

try:
    from api.workflow_models import Workflow
except ImportError:
    from workflow_models import Workflow

from api.workflow_storage.converters import row_to_workflow

logger = logging.getLogger(__name__)


class WorkflowCRUD:
    """Workflow CRUD operations mixin."""

    db_path: Path  # Provided by WorkflowStorage

    def save_workflow(
        self, workflow: Workflow, user_id: str, team_id: Optional[str] = None
    ) -> None:
        """
        Save workflow to database (Phase 3: team-aware).

        Args:
            workflow: Workflow to save
            user_id: User ID for isolation
            team_id: Optional team ID for team workflows (None for personal)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO workflows
            (id, name, description, icon, category, workflow_type, stages, triggers, enabled,
             allow_manual_creation, require_approval_to_start, is_template, created_by,
             created_at, updated_at, version, tags, user_id, team_id, owner_team_id, visibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                workflow.id,
                workflow.name,
                workflow.description,
                workflow.icon,
                workflow.category,
                workflow.workflow_type.value,
                json.dumps([s.model_dump() for s in workflow.stages]),
                json.dumps([t.model_dump() for t in workflow.triggers]),
                1 if workflow.enabled else 0,
                1 if workflow.allow_manual_creation else 0,
                1 if workflow.require_approval_to_start else 0,
                1 if workflow.is_template else 0,
                workflow.created_by,
                workflow.created_at.isoformat(),
                workflow.updated_at.isoformat(),
                workflow.version,
                json.dumps(workflow.tags),
                user_id,
                team_id,
                workflow.owner_team_id,
                workflow.visibility,
            ),
        )

        conn.commit()
        conn.close()

        team_context = f"team={team_id}" if team_id else "personal"
        logger.info(
            f"💾 Saved workflow: {workflow.name} (ID: {workflow.id}) [{team_context}]"
        )

    def get_workflow(
        self, workflow_id: str, user_id: str, team_id: Optional[str] = None
    ) -> Optional[Workflow]:
        """
        Get workflow by ID with visibility check (T3-1: visibility-aware).

        Visibility rules:
        - Personal: only owner can see
        - Team: all team members can see
        - Global: everyone can see

        Args:
            workflow_id: Workflow ID
            user_id: User ID for isolation
            team_id: Optional team ID for the user's team

        Returns:
            Workflow or None if not found/not visible
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Check visibility
        visibility = row['visibility'] if row['visibility'] else 'personal'

        if visibility == 'personal':
            if row['created_by'] != user_id:
                return None
        elif visibility == 'team':
            owner_team = row['owner_team_id']
            if not owner_team or owner_team != team_id:
                return None
        elif visibility == 'global':
            pass  # Everyone can see
        else:
            # Unknown visibility, treat as personal
            if row['created_by'] != user_id:
                return None

        return row_to_workflow(row)

    def list_workflows(
        self,
        user_id: str,
        category: Optional[str] = None,
        enabled_only: bool = True,
        team_id: Optional[str] = None,
        workflow_type: Optional[str] = None,
    ) -> List[Workflow]:
        """
        List all workflows visible to user (T3-1: visibility-aware).

        Visibility rules:
        - Personal: only owner can see
        - Team: all team members can see
        - Global: everyone can see (system templates)

        Args:
            user_id: User ID for isolation
            category: Filter by category
            enabled_only: Only return enabled workflows
            team_id: Optional team ID for the user's team
            workflow_type: Filter by workflow type ('local' or 'team')

        Returns:
            List of workflows visible to this user
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # T3-1: Build visibility query
        if team_id:
            query = """
                SELECT * FROM workflows
                WHERE (
                    (created_by = ? AND (visibility = 'personal' OR visibility IS NULL))
                    OR (owner_team_id = ? AND visibility = 'team')
                    OR visibility = 'global'
                )
            """
            params: list = [user_id, team_id]
        else:
            query = """
                SELECT * FROM workflows
                WHERE (
                    (created_by = ? AND (visibility = 'personal' OR visibility IS NULL))
                    OR visibility = 'global'
                )
            """
            params = [user_id]

        if category:
            query += " AND category = ?"
            params.append(category)

        if enabled_only:
            query += " AND enabled = 1"

        if workflow_type:
            query += " AND workflow_type = ?"
            params.append(workflow_type)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [row_to_workflow(row) for row in rows]

    def delete_workflow(self, workflow_id: str, user_id: str) -> None:
        """
        Delete workflow (soft delete).

        Args:
            workflow_id: Workflow ID
            user_id: User ID for isolation
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE workflows
            SET enabled = 0, updated_at = ?
            WHERE id = ? AND user_id = ?
        """,
            (datetime.now(UTC).isoformat(), workflow_id, user_id),
        )

        conn.commit()
        conn.close()

        logger.info(f"🗑️  Deleted workflow: {workflow_id}")
