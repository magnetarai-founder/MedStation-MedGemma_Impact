"""
Workflow Storage Layer
SQLite persistence for workflows and work items
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import logging

try:
    from .workflow_models import (
        Workflow,
        WorkItem,
        Stage,
        WorkflowTrigger,
        StageTransition,
        WorkItemAttachment,
        WorkItemStatus,
        WorkItemPriority,
    )
except ImportError:
    from workflow_models import (
        Workflow,
        WorkItem,
        Stage,
        WorkflowTrigger,
        StageTransition,
        WorkItemAttachment,
        WorkItemStatus,
        WorkItemPriority,
    )

logger = logging.getLogger(__name__)


class WorkflowStorage:
    """
    SQLite storage for workflows and work items

    Schema:
    - workflows: Workflow definitions
    - work_items: Work item instances
    - stage_transitions: Audit trail of stage changes
    - attachments: File attachments
    """

    def __init__(self, db_path: str = "data/workflows.db"):
        """
        Initialize storage

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()
        logger.info(f"📦 Workflow storage initialized: {self.db_path}")

    def _init_database(self) -> None:
        """Create database schema if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Workflows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                category TEXT,
                stages TEXT NOT NULL,  -- JSON
                triggers TEXT NOT NULL,  -- JSON
                enabled INTEGER DEFAULT 1,
                allow_manual_creation INTEGER DEFAULT 1,
                require_approval_to_start INTEGER DEFAULT 0,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                tags TEXT,  -- JSON array
                user_id TEXT,  -- Phase 1: User isolation
                team_id TEXT   -- Phase 3: Team isolation (NULL for personal workflows)
            )
        """)

        # Work items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_items (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                workflow_name TEXT NOT NULL,
                current_stage_id TEXT NOT NULL,
                current_stage_name TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                assigned_to TEXT,
                claimed_at TEXT,
                data TEXT NOT NULL,  -- JSON
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                sla_due_at TEXT,
                is_overdue INTEGER DEFAULT 0,
                tags TEXT,  -- JSON array
                reference_number TEXT,
                user_id TEXT,  -- Phase 1: User isolation
                team_id TEXT,  -- Phase 3: Team isolation (NULL for personal work items)
                FOREIGN KEY (workflow_id) REFERENCES workflows(id)
            )
        """)

        # Stage transitions table (audit trail)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stage_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_item_id TEXT NOT NULL,
                from_stage_id TEXT,
                to_stage_id TEXT,
                transitioned_at TEXT NOT NULL,
                transitioned_by TEXT,
                notes TEXT,
                duration_seconds INTEGER,
                user_id TEXT,  -- Phase 1: User isolation
                team_id TEXT,  -- Phase 3: Team isolation
                FOREIGN KEY (work_item_id) REFERENCES work_items(id)
            )
        """)

        # Attachments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id TEXT PRIMARY KEY,
                work_item_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                uploaded_by TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                user_id TEXT,  -- Phase 1: User isolation
                team_id TEXT,  -- Phase 3: Team isolation
                FOREIGN KEY (work_item_id) REFERENCES work_items(id)
            )
        """)

        # Indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_items_workflow ON work_items(workflow_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_items_status ON work_items(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_items_assigned ON work_items(assigned_to)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_items_overdue ON work_items(is_overdue)")

        # Phase 1: User isolation indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_user ON workflows(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_items_user ON work_items(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transitions_user ON stage_transitions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attachments_user ON attachments(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transitions_work_item ON stage_transitions(work_item_id)")

        # Phase 3: Team isolation indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_team ON workflows(team_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_items_team ON work_items(team_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transitions_team ON stage_transitions(team_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attachments_team ON attachments(team_id)")

        conn.commit()
        conn.close()

    # ============================================
    # WORKFLOW CRUD
    # ============================================

    def save_workflow(self, workflow: Workflow, user_id: str, team_id: Optional[str] = None) -> None:
        """
        Save workflow to database (Phase 3: team-aware)

        Args:
            workflow: Workflow to save
            user_id: User ID for isolation
            team_id: Optional team ID for team workflows (None for personal)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO workflows
            (id, name, description, icon, category, stages, triggers, enabled,
             allow_manual_creation, require_approval_to_start, created_by,
             created_at, updated_at, version, tags, user_id, team_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workflow.id,
            workflow.name,
            workflow.description,
            workflow.icon,
            workflow.category,
            json.dumps([s.model_dump() for s in workflow.stages]),
            json.dumps([t.model_dump() for t in workflow.triggers]),
            1 if workflow.enabled else 0,
            1 if workflow.allow_manual_creation else 0,
            1 if workflow.require_approval_to_start else 0,
            workflow.created_by,
            workflow.created_at.isoformat(),
            workflow.updated_at.isoformat(),
            workflow.version,
            json.dumps(workflow.tags),
            user_id,
            team_id,  # Phase 3: team_id
        ))

        conn.commit()
        conn.close()

        team_context = f"team={team_id}" if team_id else "personal"
        logger.info(f"💾 Saved workflow: {workflow.name} (ID: {workflow.id}) [{team_context}]")

    def get_workflow(self, workflow_id: str, user_id: str, team_id: Optional[str] = None) -> Optional[Workflow]:
        """
        Get workflow by ID (Phase 3: team-aware)

        Args:
            workflow_id: Workflow ID
            user_id: User ID for isolation
            team_id: Optional team ID (None for personal workflows)

        Returns:
            Workflow or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Phase 3: Filter by team_id
        if team_id:
            # Team workflow: filter by team_id
            cursor.execute("""
                SELECT * FROM workflows
                WHERE id = ? AND team_id = ?
            """, (workflow_id, team_id))
        else:
            # Personal workflow: filter by user_id and team_id IS NULL
            cursor.execute("""
                SELECT * FROM workflows
                WHERE id = ? AND user_id = ? AND team_id IS NULL
            """, (workflow_id, user_id))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_workflow(row)

    def list_workflows(
        self,
        user_id: str,
        category: Optional[str] = None,
        enabled_only: bool = True,
        team_id: Optional[str] = None
    ) -> List[Workflow]:
        """
        List all workflows (Phase 3: team-aware)

        Args:
            user_id: User ID for isolation
            category: Filter by category
            enabled_only: Only return enabled workflows
            team_id: Optional team ID (None for personal workflows)

        Returns:
            List of workflows
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Phase 3: Filter by team_id
        if team_id:
            # Team workflows: filter by team_id
            query = "SELECT * FROM workflows WHERE team_id = ?"
            params = [team_id]
        else:
            # Personal workflows: filter by user_id and team_id IS NULL
            query = "SELECT * FROM workflows WHERE user_id = ? AND team_id IS NULL"
            params = [user_id]

        if category:
            query += " AND category = ?"
            params.append(category)

        if enabled_only:
            query += " AND enabled = 1"

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_workflow(row) for row in rows]

    def delete_workflow(self, workflow_id: str, user_id: str) -> None:
        """
        Delete workflow (soft delete)

        Args:
            workflow_id: Workflow ID
            user_id: User ID for isolation
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE workflows
            SET enabled = 0, updated_at = ?
            WHERE id = ? AND user_id = ?
        """, (datetime.utcnow().isoformat(), workflow_id, user_id))

        conn.commit()
        conn.close()

        logger.info(f"🗑️  Deleted workflow: {workflow_id}")

    # ============================================
    # WORK ITEM CRUD
    # ============================================

    def save_work_item(self, work_item: WorkItem, user_id: str) -> None:
        """
        Save work item to database

        Args:
            work_item: Work item to save
            user_id: User ID for isolation
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO work_items
            (id, workflow_id, workflow_name, current_stage_id, current_stage_name,
             status, priority, assigned_to, claimed_at, data, created_by,
             created_at, updated_at, completed_at, sla_due_at, is_overdue,
             tags, reference_number, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
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
        ))

        # Save stage transitions
        for transition in work_item.history:
            cursor.execute("""
                INSERT INTO stage_transitions
                (work_item_id, from_stage_id, to_stage_id, transitioned_at,
                 transitioned_by, notes, duration_seconds, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                work_item.id,
                transition.from_stage_id,
                transition.to_stage_id,
                transition.transitioned_at.isoformat(),
                transition.transitioned_by,
                transition.notes,
                transition.duration_seconds,
                user_id,
            ))

        # Save attachments
        for attachment in work_item.attachments:
            cursor.execute("""
                INSERT OR REPLACE INTO attachments
                (id, work_item_id, filename, file_path, file_size, mime_type,
                 uploaded_by, uploaded_at, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attachment.id,
                work_item.id,
                attachment.filename,
                attachment.file_path,
                attachment.file_size,
                attachment.mime_type,
                attachment.uploaded_by,
                attachment.uploaded_at.isoformat(),
                user_id,
            ))

        conn.commit()
        conn.close()

        logger.debug(f"💾 Saved work item: {work_item.id}")

    def get_work_item(self, work_item_id: str, user_id: str) -> Optional[WorkItem]:
        """
        Get work item by ID

        Args:
            work_item_id: Work item ID
            user_id: User ID for isolation

        Returns:
            Work item or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM work_items
            WHERE id = ? AND user_id = ?
        """, (work_item_id, user_id))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        work_item = self._row_to_work_item(row)

        # Load transitions
        cursor.execute("""
            SELECT * FROM stage_transitions
            WHERE work_item_id = ? AND user_id = ?
            ORDER BY transitioned_at ASC
        """, (work_item_id, user_id))
        transitions = cursor.fetchall()
        work_item.history = [self._row_to_transition(t) for t in transitions]

        # Load attachments
        cursor.execute("""
            SELECT * FROM attachments
            WHERE work_item_id = ? AND user_id = ?
            ORDER BY uploaded_at ASC
        """, (work_item_id, user_id))
        attachments = cursor.fetchall()
        work_item.attachments = [self._row_to_attachment(a) for a in attachments]

        conn.close()
        return work_item

    def list_work_items(
        self,
        user_id: str,
        workflow_id: Optional[str] = None,
        status: Optional[WorkItemStatus] = None,
        assigned_to: Optional[str] = None,
        limit: int = 50
    ) -> List[WorkItem]:
        """
        List work items with filters

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
        params = [user_id]

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

        return [self._row_to_work_item(row) for row in rows]

    # ============================================
    # HELPER METHODS
    # ============================================

    def _row_to_workflow(self, row: sqlite3.Row) -> Workflow:
        """Convert database row to Workflow object"""
        stages_data = json.loads(row['stages'])
        triggers_data = json.loads(row['triggers'])

        return Workflow(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            icon=row['icon'],
            category=row['category'],
            stages=[Stage(**s) for s in stages_data],
            triggers=[WorkflowTrigger(**t) for t in triggers_data],
            enabled=bool(row['enabled']),
            allow_manual_creation=bool(row['allow_manual_creation']),
            require_approval_to_start=bool(row['require_approval_to_start']),
            created_by=row['created_by'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            version=row['version'],
            tags=json.loads(row['tags']) if row['tags'] else [],
        )

    def _row_to_work_item(self, row: sqlite3.Row) -> WorkItem:
        """Convert database row to WorkItem object"""
        return WorkItem(
            id=row['id'],
            workflow_id=row['workflow_id'],
            workflow_name=row['workflow_name'],
            current_stage_id=row['current_stage_id'],
            current_stage_name=row['current_stage_name'],
            status=WorkItemStatus(row['status']),
            priority=WorkItemPriority(row['priority']),
            assigned_to=row['assigned_to'],
            claimed_at=datetime.fromisoformat(row['claimed_at']) if row['claimed_at'] else None,
            data=json.loads(row['data']),
            created_by=row['created_by'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            sla_due_at=datetime.fromisoformat(row['sla_due_at']) if row['sla_due_at'] else None,
            is_overdue=bool(row['is_overdue']),
            tags=json.loads(row['tags']) if row['tags'] else [],
            reference_number=row['reference_number'],
            history=[],  # Will be loaded separately
            attachments=[],  # Will be loaded separately
        )

    def _row_to_transition(self, row: sqlite3.Row) -> StageTransition:
        """Convert database row to StageTransition object"""
        return StageTransition(
            from_stage_id=row['from_stage_id'],
            to_stage_id=row['to_stage_id'],
            transitioned_at=datetime.fromisoformat(row['transitioned_at']),
            transitioned_by=row['transitioned_by'],
            notes=row['notes'],
            duration_seconds=row['duration_seconds'],
        )

    def _row_to_attachment(self, row: sqlite3.Row) -> WorkItemAttachment:
        """Convert database row to WorkItemAttachment object"""
        return WorkItemAttachment(
            id=row['id'],
            filename=row['filename'],
            file_path=row['file_path'],
            file_size=row['file_size'],
            mime_type=row['mime_type'],
            uploaded_by=row['uploaded_by'],
            uploaded_at=datetime.fromisoformat(row['uploaded_at']),
        )
