"""
Auth Migration 0003: Device Identity

Creates a stable device identity separate from user accounts.
This identity persists across:
- User account changes (creation, deletion, all users deleted)
- Auth data resets
- App reinstalls (if machine_id can be recovered)

The device_identity table:
- Provides a stable identifier for "this machine"
- Enables future update server integration (device checks for updates)
- Maintains machine history (first boot, last boot)

Device ID generation happens at runtime via ensure_device_identity().
This migration only creates the table schema.

Created: 2025-11-20 (AUTH-P6)
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)

MIGRATION_VERSION = "auth_0003_device_identity"


def apply_migration(conn: sqlite3.Connection) -> None:
    """
    Apply device identity migration.

    Creates the device_identity table for stable machine identification.
    Uses CREATE TABLE IF NOT EXISTS for idempotency.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    logger.info(f"Applying migration: {MIGRATION_VERSION}")

    # ========================================
    # DEVICE IDENTITY TABLE
    # ========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_identity (
            device_id TEXT PRIMARY KEY,
            machine_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            last_boot_at TEXT NOT NULL,
            hostname TEXT,
            platform TEXT,
            architecture TEXT,
            metadata_json TEXT
        )
    """)
    logger.info("  ✓ device_identity table")

    # Index for looking up by machine_id (alternative key)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_identity_machine_id
        ON device_identity(machine_id)
    """)
    logger.info("  ✓ device_identity indexes")

    conn.commit()
    logger.info(f"✅ Migration {MIGRATION_VERSION} applied successfully")


def rollback_migration(conn: sqlite3.Connection) -> None:
    """
    Rollback this migration.

    WARNING: This will DROP the device_identity table.
    Only use for testing. Device identity should persist in production.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    logger.warning(f"Rolling back migration: {MIGRATION_VERSION}")
    logger.warning("⚠️  This will DROP device_identity table")

    cursor.execute("DROP TABLE IF EXISTS device_identity")
    logger.info("  ✓ Dropped device_identity table")

    cursor.execute("DROP INDEX IF EXISTS idx_device_identity_machine_id")
    logger.info("  ✓ Dropped device_identity indexes")

    conn.commit()
    logger.warning(f"⚠️  Migration {MIGRATION_VERSION} rolled back")
