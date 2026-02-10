"""
n8n Offline Cache

SQLite-backed cache for n8n workflows and execution queue.
Enables graceful degradation when n8n is unreachable.

Tier 10.5 Features:
- Caches workflow list for offline access
- Queues executions for later retry when n8n is down
- Tracks retry counts and errors

Extracted from n8n_integration.py during P2 decomposition.
"""

import sqlite3
import uuid
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, UTC
from pathlib import Path

logger = logging.getLogger(__name__)


class N8NOfflineCache:
    """
    Cache for n8n workflows and execution queue.

    Tier 10.5: Enables graceful degradation when n8n is unreachable:
    - Caches workflow list for offline access
    - Queues executions for later retry
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / ".medstationos" / "n8n_cache.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite cache database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Workflow cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_cache (
                workflow_id TEXT PRIMARY KEY,
                workflow_data TEXT NOT NULL,
                cached_at TEXT NOT NULL
            )
        """)

        # Execution queue for offline retry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_queue (
                queue_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                execution_data TEXT NOT NULL,
                queued_at TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_queue_workflow
            ON execution_queue(workflow_id)
        """)

        conn.commit()
        conn.close()

    def cache_workflows(self, workflows: List[Dict[str, Any]]) -> None:
        """Cache workflow list"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Clear old cache and insert new
        cursor.execute("DELETE FROM workflow_cache")

        for wf in workflows:
            cursor.execute("""
                INSERT INTO workflow_cache (workflow_id, workflow_data, cached_at)
                VALUES (?, ?, ?)
            """, (
                wf.get('id', str(uuid.uuid4())),
                json.dumps(wf),
                datetime.now(UTC).isoformat()
            ))

        conn.commit()
        conn.close()
        logger.debug(f"📦 Cached {len(workflows)} n8n workflows")

    def get_cached_workflows(self) -> Tuple[List[Dict[str, Any]], Optional[datetime]]:
        """
        Get cached workflows.

        Returns:
            Tuple of (workflows, cached_at) or ([], None) if no cache
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT workflow_data, cached_at FROM workflow_cache
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return [], None

        workflows = [json.loads(row['workflow_data']) for row in rows]
        cached_at = datetime.fromisoformat(rows[0]['cached_at'])

        return workflows, cached_at

    def queue_execution(self, workflow_id: str, data: Dict[str, Any]) -> str:
        """
        Queue workflow execution for later retry.

        Returns:
            Queue ID for tracking
        """
        queue_id = str(uuid.uuid4())
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO execution_queue (queue_id, workflow_id, execution_data, queued_at)
            VALUES (?, ?, ?, ?)
        """, (
            queue_id,
            workflow_id,
            json.dumps(data),
            datetime.now(UTC).isoformat()
        ))

        conn.commit()
        conn.close()
        logger.info(f"📥 Queued n8n execution {queue_id} for workflow {workflow_id}")

        return queue_id

    def get_pending_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending executions from queue"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT queue_id, workflow_id, execution_data, queued_at, retry_count
            FROM execution_queue
            ORDER BY queued_at ASC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'queue_id': row['queue_id'],
                'workflow_id': row['workflow_id'],
                'data': json.loads(row['execution_data']),
                'queued_at': row['queued_at'],
                'retry_count': row['retry_count']
            }
            for row in rows
        ]

    def remove_from_queue(self, queue_id: str) -> None:
        """Remove execution from queue after success"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM execution_queue WHERE queue_id = ?", (queue_id,))
        conn.commit()
        conn.close()

    def mark_retry_failed(self, queue_id: str, error: str) -> None:
        """Increment retry count and record error"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE execution_queue
            SET retry_count = retry_count + 1, last_error = ?
            WHERE queue_id = ?
        """, (error, queue_id))
        conn.commit()
        conn.close()


# Global cache instance
_n8n_cache: Optional[N8NOfflineCache] = None


def get_n8n_cache() -> N8NOfflineCache:
    """Get or create global n8n cache"""
    global _n8n_cache
    if _n8n_cache is None:
        _n8n_cache = N8NOfflineCache()
    return _n8n_cache


__all__ = [
    "N8NOfflineCache",
    "get_n8n_cache",
]
