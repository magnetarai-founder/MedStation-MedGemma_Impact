"""
Workflow Storage Schema

Database schema definition and initialization for workflow storage.
"""

import sqlite3
import logging
from pathlib import Path

try:
    from api.security.sql_safety import quote_identifier
except ImportError:
    from security.sql_safety import quote_identifier

logger = logging.getLogger(__name__)


def init_database(db_path: Path) -> None:
    """
    Create database schema if not exists.

    Args:
        db_path: Path to the database file
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Workflows table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            category TEXT,
            workflow_type TEXT DEFAULT 'team',  -- 'local' or 'team'
            stages TEXT NOT NULL,  -- JSON
            triggers TEXT NOT NULL,  -- JSON
            enabled INTEGER DEFAULT 1,
            allow_manual_creation INTEGER DEFAULT 1,
            require_approval_to_start INTEGER DEFAULT 0,
            is_template INTEGER DEFAULT 0,  -- Phase D: Template workflow
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

    # Starred workflows table (max 5 per user per type)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS starred_workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            workflow_id TEXT NOT NULL,
            starred_at TEXT NOT NULL,
            UNIQUE(user_id, workflow_id),
            FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
        )
    """)

    # Create indexes
    _create_indexes(cursor)

    # Run migrations for existing databases
    _run_migrations(cursor)

    conn.commit()
    conn.close()


def _create_indexes(cursor: sqlite3.Cursor) -> None:
    """Create database indexes for performance."""
    # Work items indexes
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_starred_user ON starred_workflows(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_starred_workflow ON starred_workflows(workflow_id)")

    # Phase 3: Team isolation indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_team ON workflows(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_items_team ON work_items(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transitions_team ON stage_transitions(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attachments_team ON attachments(team_id)")

    # Phase D: Template index
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_template ON workflows(is_template)")


def _run_migrations(cursor: sqlite3.Cursor) -> None:
    """Run schema migrations for existing databases."""
    # Phase 3.5: Add team_id columns if they don't exist
    # Whitelist of tables for defense-in-depth
    TEAM_ID_TABLES = frozenset({"workflows", "work_items", "stage_transitions", "attachments"})
    for table in TEAM_ID_TABLES:
        try:
            cursor.execute(f"ALTER TABLE {quote_identifier(table)} ADD COLUMN team_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Phase D: Add is_template column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE workflows ADD COLUMN is_template INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # T3-1: Add owner_team_id and visibility for multi-tenant hardening
    try:
        cursor.execute("ALTER TABLE workflows ADD COLUMN owner_team_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE workflows ADD COLUMN visibility TEXT DEFAULT 'personal'")
    except sqlite3.OperationalError:
        pass  # Column already exists
