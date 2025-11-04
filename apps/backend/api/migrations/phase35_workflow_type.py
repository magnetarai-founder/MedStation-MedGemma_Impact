#!/usr/bin/env python3
"""
Phase 3.5: Add workflow_type Column to Workflows Table

Adds workflow_type column to support Local Automation vs Team Workflow distinction.

Migration Changes:
- workflows table: Add workflow_type column (default='team')
- Backward compatible: existing workflows default to 'team' type
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def check_migration_applied(app_db_path: Path) -> bool:
    """
    Check if Phase 3.5 migration has already been applied

    Returns:
        bool: True if migration already applied, False otherwise
    """
    try:
        conn = sqlite3.connect(str(app_db_path))
        cursor = conn.cursor()

        # Check if migration tracking entry exists
        cursor.execute("""
            SELECT applied
            FROM schema_migrations
            WHERE phase = 'phase_3.5'
        """)

        result = cursor.fetchone()
        conn.close()

        if result:
            return bool(result[0])
        return False

    except sqlite3.OperationalError:
        # Table doesn't exist or other DB error
        return False


def migrate_phase35_workflow_type(app_db_path: Path, workflows_db_path: Path) -> bool:
    """
    Apply Phase 3.5 migration: Add workflow_type column

    Args:
        app_db_path: Path to main app database (for tracking)
        workflows_db_path: Path to workflows database

    Returns:
        bool: True if migration succeeded, False otherwise
    """
    try:
        logger.info("📦 Starting Phase 3.5 migration: Workflow Type Column")

        # Connect to workflows database
        workflows_conn = sqlite3.connect(str(workflows_db_path))
        workflows_cursor = workflows_conn.cursor()

        # Check if workflow_type column already exists
        workflows_cursor.execute("PRAGMA table_info(workflows)")
        columns = [row[1] for row in workflows_cursor.fetchall()]

        if 'workflow_type' in columns:
            logger.info("  ✓ workflow_type column already exists, skipping schema change")
        else:
            logger.info("  → Adding workflow_type column to workflows table")
            workflows_cursor.execute("""
                ALTER TABLE workflows
                ADD COLUMN workflow_type TEXT DEFAULT 'team'
            """)
            logger.info("  ✓ Added workflow_type column (default='team')")

        workflows_conn.commit()
        workflows_conn.close()

        # Track migration in app database
        app_conn = sqlite3.connect(str(app_db_path))
        app_cursor = app_conn.cursor()

        # Record migration as applied
        app_cursor.execute("""
            INSERT OR REPLACE INTO schema_migrations (phase, applied_at, applied)
            VALUES ('phase_3.5', datetime('now'), 1)
        """)

        app_conn.commit()
        app_conn.close()

        logger.info("✓ Phase 3.5 migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"✗ Phase 3.5 migration failed: {e}", exc_info=True)
        return False
