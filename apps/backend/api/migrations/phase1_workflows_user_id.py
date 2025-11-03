"""
Phase 1 Migration: Add user_id columns to workflow tables for user isolation

This migration:
1. Adds user_id columns to workflows, work_items, stage_transitions, and attachments tables
2. Backfills user_id from created_by/transitioned_by/uploaded_by fields
3. Creates indexes on user_id columns for performance
4. Records completion in migrations table

Non-interactive and idempotent - safe to run multiple times.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def get_user_id_mapping(app_db_path: Path) -> Dict[str, str]:
    """
    Get mapping of usernames to user_ids from app_db

    Returns dict: {username: user_id}
    """
    try:
        conn = sqlite3.connect(str(app_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT username, user_id FROM users")
        mapping = {row['username']: row['user_id'] for row in cursor.fetchall()}

        conn.close()

        logger.info(f"  Found {len(mapping)} users in auth database")
        for username, user_id in mapping.items():
            logger.info(f"    {username} → {user_id}")

        return mapping
    except Exception as e:
        logger.warning(f"  Could not load user mapping from app_db: {e}")
        logger.info("  Will use created_by as user_id (fallback)")
        return {}


def add_user_id_columns(conn: sqlite3.Connection) -> None:
    """Add user_id columns to all workflow tables if not already present"""
    cursor = conn.cursor()

    logger.info("  Adding user_id columns to tables...")

    tables = [
        ('workflows', 'workflows'),
        ('work_items', 'work_items'),
        ('stage_transitions', 'stage_transitions'),
        ('attachments', 'attachments'),
    ]

    for table_name, display_name in tables:
        try:
            # Check if column already exists
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]

            if 'user_id' in columns:
                logger.info(f"    ✓ {display_name} already has user_id column")
            else:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN user_id TEXT")
                logger.info(f"    ✓ Added user_id to {display_name}")
        except sqlite3.OperationalError as e:
            logger.warning(f"    Could not add user_id to {table_name}: {e}")

    conn.commit()


def backfill_user_ids(conn: sqlite3.Connection, user_mapping: Dict[str, str]) -> None:
    """Populate user_id columns from existing created_by/transitioned_by/uploaded_by fields"""
    cursor = conn.cursor()

    logger.info("  Backfilling user_id from existing data...")

    # 1. Workflows (use created_by)
    cursor.execute("SELECT id, created_by FROM workflows WHERE user_id IS NULL OR user_id = ''")
    workflows = cursor.fetchall()
    migrated = 0
    for workflow_id, created_by in workflows:
        user_id = user_mapping.get(created_by, created_by)
        cursor.execute("UPDATE workflows SET user_id = ? WHERE id = ?", (user_id, workflow_id))
        migrated += 1
    logger.info(f"    ✓ Migrated {migrated} workflows")

    # 2. Work Items (use created_by)
    cursor.execute("SELECT id, created_by FROM work_items WHERE user_id IS NULL OR user_id = ''")
    work_items = cursor.fetchall()
    migrated = 0
    for item_id, created_by in work_items:
        user_id = user_mapping.get(created_by, created_by)
        cursor.execute("UPDATE work_items SET user_id = ? WHERE id = ?", (user_id, item_id))
        migrated += 1
    logger.info(f"    ✓ Migrated {migrated} work_items")

    # 3. Stage Transitions (use transitioned_by)
    cursor.execute("SELECT id, transitioned_by FROM stage_transitions WHERE user_id IS NULL OR user_id = ''")
    transitions = cursor.fetchall()
    migrated = 0
    for trans_id, transitioned_by in transitions:
        # Handle NULL transitioned_by (system transitions)
        user_id = user_mapping.get(transitioned_by, transitioned_by) if transitioned_by else None
        cursor.execute("UPDATE stage_transitions SET user_id = ? WHERE id = ?", (user_id, trans_id))
        migrated += 1
    logger.info(f"    ✓ Migrated {migrated} stage_transitions")

    # 4. Attachments (use uploaded_by)
    cursor.execute("SELECT id, uploaded_by FROM attachments WHERE user_id IS NULL OR user_id = ''")
    attachments = cursor.fetchall()
    migrated = 0
    for attach_id, uploaded_by in attachments:
        user_id = user_mapping.get(uploaded_by, uploaded_by)
        cursor.execute("UPDATE attachments SET user_id = ? WHERE id = ?", (user_id, attach_id))
        migrated += 1
    logger.info(f"    ✓ Migrated {migrated} attachments")

    conn.commit()


def create_indexes(conn: sqlite3.Connection) -> None:
    """Create indexes on user_id columns for query performance"""
    cursor = conn.cursor()

    logger.info("  Creating indexes on user_id columns...")

    indexes = [
        ('idx_workflows_user', 'workflows', 'user_id'),
        ('idx_work_items_user', 'work_items', 'user_id'),
        ('idx_transitions_user', 'stage_transitions', 'user_id'),
        ('idx_attachments_user', 'attachments', 'user_id'),
    ]

    for index_name, table_name, column_name in indexes:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})")
        logger.info(f"    ✓ Created {index_name}")

    conn.commit()


def record_migration_completion(app_db_conn: sqlite3.Connection) -> None:
    """Record this migration as complete in app_db migrations table"""
    cursor = app_db_conn.cursor()

    migration_name = '2025_11_03_phase1_workflows_user_id'
    applied_at = datetime.now().isoformat()

    cursor.execute("""
        INSERT OR IGNORE INTO migrations (migration_name, applied_at)
        VALUES (?, ?)
    """, (migration_name, applied_at))

    app_db_conn.commit()
    logger.info(f"  ✓ Recorded migration completion: {migration_name}")


def check_migration_applied(app_db_path: Path) -> bool:
    """Check if this migration has already been applied"""
    try:
        conn = sqlite3.connect(str(app_db_path))
        cursor = conn.cursor()

        # Ensure migrations table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                migration_name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            SELECT 1 FROM migrations
            WHERE migration_name = '2025_11_03_phase1_workflows_user_id'
        """)

        result = cursor.fetchone()
        conn.close()

        return result is not None
    except Exception as e:
        logger.warning(f"Could not check migration status: {e}")
        return False


def migrate_phase1_workflows_user_id(
    app_db_path: Path,
    workflows_db_path: Path
) -> bool:
    """
    Main migration function for Phase 1: Workflow User Isolation

    Args:
        app_db_path: Path to elohimos_app.db (for user mapping and migration tracking)
        workflows_db_path: Path to workflows.db

    Returns:
        True if migration successful, False otherwise
    """
    try:
        logger.info("Phase 1 Migration: Workflow User Isolation")

        # Check if workflows DB exists
        if not workflows_db_path.exists():
            logger.info(f"  Workflows database does not exist yet: {workflows_db_path}")
            logger.info("  Migration will be applied when workflows DB is created")

            # Still record as complete so we don't try again
            app_db_conn = sqlite3.connect(str(app_db_path))
            record_migration_completion(app_db_conn)
            app_db_conn.close()
            return True

        # Get user mapping from app_db
        user_mapping = get_user_id_mapping(app_db_path)

        # Connect to workflows DB
        workflows_conn = sqlite3.connect(str(workflows_db_path))

        # Step 1: Add user_id columns
        add_user_id_columns(workflows_conn)

        # Step 2: Backfill data
        backfill_user_ids(workflows_conn, user_mapping)

        # Step 3: Create indexes
        create_indexes(workflows_conn)

        workflows_conn.close()

        # Step 4: Record completion in app_db
        app_db_conn = sqlite3.connect(str(app_db_path))
        record_migration_completion(app_db_conn)
        app_db_conn.close()

        logger.info("✓ Phase 1 migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"✗ Phase 1 migration failed: {e}", exc_info=True)
        return False
