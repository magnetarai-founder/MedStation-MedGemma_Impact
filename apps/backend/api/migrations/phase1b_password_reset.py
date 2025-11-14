"""
Phase 1B Migration: Password Reset Support

Adds must_change_password column to users table for forced password change flow.
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run_migration(app_db_path: Path) -> bool:
    """
    Add must_change_password column to users table.

    Returns:
        bool: True if migration succeeded, False otherwise
    """
    try:
        logger.info("Running Phase 1B migration: Password Reset Support")

        conn = sqlite3.connect(str(app_db_path))
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'must_change_password' not in columns:
            logger.info("  Adding 'must_change_password' column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0")
            conn.commit()
            logger.info("  ✓ must_change_password column added")
        else:
            logger.info("  must_change_password column already exists")

        conn.close()
        logger.info("✓ Phase 1B migration completed")
        return True

    except Exception as e:
        logger.error(f"✗ Phase 1B migration failed: {e}")
        return False
