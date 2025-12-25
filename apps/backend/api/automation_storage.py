"""
Automation Workflow Storage

SQLite persistence for n8n-style visual automation workflows.
These are distinct from team workflows - they store visual node/edge definitions.
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AutomationStorage:
    """
    SQLite storage for automation workflow definitions

    Schema:
    - automation_workflows: Visual workflow definitions (nodes, edges)
    - automation_executions: Execution history
    """

    def __init__(self, db_path: str | None = None):
        """
        Initialize storage

        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            try:
                from .config_paths import get_config_paths
            except Exception:
                from config_paths import get_config_paths
            paths = get_config_paths()
            self.db_path = Path(paths.data_dir) / "automations.db"
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logger.info(f"⚙️ Automation storage initialized: {self.db_path}")

    def _init_database(self) -> None:
        """Create database schema if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Automation workflows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                nodes TEXT NOT NULL,  -- JSON array
                edges TEXT NOT NULL,  -- JSON array
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                last_run_at TEXT,
                run_count INTEGER DEFAULT 0
            )
        """)

        # Automation executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,  -- running, completed, failed
                steps_executed INTEGER DEFAULT 0,
                execution_time_ms INTEGER,
                results TEXT,  -- JSON
                error TEXT,
                FOREIGN KEY (workflow_id) REFERENCES automation_workflows(id)
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_automation_user ON automation_workflows(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_workflow ON automation_executions(workflow_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_user ON automation_executions(user_id)")

        conn.commit()
        conn.close()

    def save_workflow(
        self,
        workflow_id: str,
        name: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        user_id: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save or update an automation workflow

        Args:
            workflow_id: Workflow ID
            name: Workflow name
            nodes: List of node definitions
            edges: List of edge definitions
            user_id: Owner user ID
            description: Optional description

        Returns:
            Saved workflow data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()

        # Check if exists
        cursor.execute("SELECT id FROM automation_workflows WHERE id = ?", (workflow_id,))
        exists = cursor.fetchone() is not None

        if exists:
            # Update
            cursor.execute("""
                UPDATE automation_workflows
                SET name = ?, nodes = ?, edges = ?, description = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (
                name,
                json.dumps(nodes),
                json.dumps(edges),
                description,
                now,
                workflow_id,
                user_id
            ))
            logger.info(f"📝 Updated automation workflow: {workflow_id}")
        else:
            # Insert
            cursor.execute("""
                INSERT INTO automation_workflows
                (id, name, nodes, edges, user_id, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow_id,
                name,
                json.dumps(nodes),
                json.dumps(edges),
                user_id,
                description,
                now,
                now
            ))
            logger.info(f"💾 Saved new automation workflow: {workflow_id}")

        conn.commit()
        conn.close()

        return {
            "id": workflow_id,
            "name": name,
            "nodes": nodes,
            "edges": edges,
            "user_id": user_id,
            "description": description,
            "created_at": now,
            "updated_at": now
        }

    def get_workflow(self, workflow_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow by ID

        Args:
            workflow_id: Workflow ID
            user_id: User ID for isolation

        Returns:
            Workflow data or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM automation_workflows
            WHERE id = ? AND user_id = ?
        """, (workflow_id, user_id))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "nodes": json.loads(row["nodes"]),
            "edges": json.loads(row["edges"]),
            "user_id": row["user_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "is_active": bool(row["is_active"]),
            "last_run_at": row["last_run_at"],
            "run_count": row["run_count"]
        }

    def list_workflows(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List workflows for a user

        Args:
            user_id: User ID for isolation
            limit: Max results
            offset: Pagination offset
            active_only: Only return active workflows

        Returns:
            List of workflows
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM automation_workflows WHERE user_id = ?"
        params = [user_id]

        if active_only:
            query += " AND is_active = 1"

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "nodes": json.loads(row["nodes"]),
                "edges": json.loads(row["edges"]),
                "user_id": row["user_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "is_active": bool(row["is_active"]),
                "last_run_at": row["last_run_at"],
                "run_count": row["run_count"]
            }
            for row in rows
        ]

    def delete_workflow(self, workflow_id: str, user_id: str) -> bool:
        """
        Delete a workflow

        Args:
            workflow_id: Workflow ID
            user_id: User ID for isolation

        Returns:
            True if deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM automation_workflows
            WHERE id = ? AND user_id = ?
        """, (workflow_id, user_id))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if deleted:
            logger.info(f"🗑️ Deleted automation workflow: {workflow_id}")

        return deleted

    def record_execution(
        self,
        workflow_id: str,
        user_id: str,
        status: str,
        steps_executed: int = 0,
        execution_time_ms: int = 0,
        results: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> int:
        """
        Record a workflow execution

        Args:
            workflow_id: Workflow ID
            user_id: User ID
            status: Execution status
            steps_executed: Number of steps executed
            execution_time_ms: Execution time in ms
            results: Execution results
            error: Error message if failed

        Returns:
            Execution ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            INSERT INTO automation_executions
            (workflow_id, user_id, started_at, completed_at, status,
             steps_executed, execution_time_ms, results, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workflow_id,
            user_id,
            now,
            now if status in ["completed", "failed"] else None,
            status,
            steps_executed,
            execution_time_ms,
            json.dumps(results) if results else None,
            error
        ))

        execution_id = cursor.lastrowid

        # Update workflow run count
        cursor.execute("""
            UPDATE automation_workflows
            SET run_count = run_count + 1, last_run_at = ?
            WHERE id = ?
        """, (now, workflow_id))

        conn.commit()
        conn.close()

        return execution_id

    def get_execution_history(
        self,
        workflow_id: str,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get execution history for a workflow

        Args:
            workflow_id: Workflow ID
            user_id: User ID for isolation
            limit: Max results

        Returns:
            List of executions
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM automation_executions
            WHERE workflow_id = ? AND user_id = ?
            ORDER BY started_at DESC
            LIMIT ?
        """, (workflow_id, user_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row["id"],
                "workflow_id": row["workflow_id"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "status": row["status"],
                "steps_executed": row["steps_executed"],
                "execution_time_ms": row["execution_time_ms"],
                "results": json.loads(row["results"]) if row["results"] else None,
                "error": row["error"]
            }
            for row in rows
        ]


# Singleton
_automation_storage: Optional[AutomationStorage] = None


def get_automation_storage() -> AutomationStorage:
    """Get singleton automation storage instance"""
    global _automation_storage

    if _automation_storage is None:
        _automation_storage = AutomationStorage()

    return _automation_storage
