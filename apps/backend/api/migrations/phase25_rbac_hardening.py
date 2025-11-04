#!/usr/bin/env python3
"""
Phase 2.5 RBAC Hardening Migration

Builds on Phase 2 to add:
- permission_set_permissions table (permission set grants)
- user_permissions_cache table (optional caching)
- Index hardening on permissions(permission_key)

"Build on the rock, not on sand" - Matthew 7:24-27
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

MIGRATION_NAME = "2025_11_05_phase25_rbac_hardening"


def check_migration_applied(db_path: Path) -> bool:
    """Check if Phase 2.5 migration has already been applied"""
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        # Check migrations table
        cur.execute(
            "SELECT 1 FROM migrations WHERE migration_name = ?",
            (MIGRATION_NAME,)
        )
        result = cur.fetchone()
        conn.close()

        return result is not None
    except sqlite3.OperationalError:
        return False


def create_hardening_schema(conn: sqlite3.Connection) -> None:
    """Create Phase 2.5 hardening tables and indexes"""
    cursor = conn.cursor()

    logger.info("Creating permission_set_permissions table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permission_set_permissions (
            permission_set_id TEXT NOT NULL,
            permission_id TEXT NOT NULL,
            is_granted INTEGER DEFAULT 1,
            permission_level TEXT CHECK(permission_level IN ('none','read','write','admin')),
            permission_scope TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (permission_set_id, permission_id),
            FOREIGN KEY (permission_set_id) REFERENCES permission_sets(permission_set_id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions(permission_id) ON DELETE CASCADE
        )
    """)

    logger.info("Creating user_permissions_cache table (optional)...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_permissions_cache (
            user_id TEXT PRIMARY KEY,
            permissions_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)

    logger.info("Creating index on permissions(permission_key)...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_permissions_key
        ON permissions(permission_key)
    """)

    # Additional useful indexes for performance
    logger.info("Creating additional performance indexes...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_permission_set_permissions_set_id
        ON permission_set_permissions(permission_set_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_permission_sets_user_id
        ON user_permission_sets(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_permission_profiles_user_id
        ON user_permission_profiles(user_id)
    """)

    conn.commit()
    logger.info("✅ Phase 2.5 schema created successfully")


def record_migration(conn: sqlite3.Connection) -> None:
    """Record migration in migrations table"""
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT INTO migrations (migration_name, applied_at)
        VALUES (?, ?)
    """, (MIGRATION_NAME, now))

    conn.commit()
    logger.info(f"✅ Migration recorded: {MIGRATION_NAME} at {now}")


def migrate_phase25_rbac_hardening(db_path: Path) -> bool:
    """
    Run Phase 2.5 RBAC hardening migration

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("=" * 60)
    logger.info("PHASE 2.5: RBAC HARDENING MIGRATION")
    logger.info("=" * 60)
    logger.info(f"Database: {db_path}")

    if not db_path.exists():
        logger.error(f"❌ Database not found: {db_path}")
        return False

    if check_migration_applied(db_path):
        logger.info("⚠️  Phase 2.5 migration already applied")
        return True

    try:
        conn = sqlite3.connect(str(db_path))

        # Create schema
        create_hardening_schema(conn)

        # Record migration
        record_migration(conn)

        conn.close()

        logger.info("=" * 60)
        logger.info("✅ PHASE 2.5 MIGRATION COMPLETE")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ Phase 2.5 migration failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # For standalone testing
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from config_paths import get_config_paths

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s - %(message)s"
    )

    paths = get_config_paths()
    success = migrate_phase25_rbac_hardening(paths.app_db)

    sys.exit(0 if success else 1)
