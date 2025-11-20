"""
Auth Migration Runner

Manages auth-specific schema migrations.
Integrates with existing migration tracking system in the main migrations table.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


def _ensure_migration_table(conn: sqlite3.Connection) -> None:
    """
    Ensure the main migrations table exists.

    This table is shared across all migrations (not just auth).
    Created by phase0 migration, but we ensure it exists here for safety.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            migration_name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT
        )
    """)

    conn.commit()


def _is_migration_applied(conn: sqlite3.Connection, migration_name: str) -> bool:
    """
    Check if a migration has been applied.

    Args:
        conn: SQLite database connection
        migration_name: Name of migration to check (e.g., "auth_0001_initial")

    Returns:
        True if migration has been applied, False otherwise
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1 FROM migrations WHERE migration_name = ?
    """, (migration_name,))

    return cursor.fetchone() is not None


def _record_migration(conn: sqlite3.Connection, migration_name: str, description: str) -> None:
    """
    Record that a migration has been applied.

    Args:
        conn: SQLite database connection
        migration_name: Name of migration
        description: Human-readable description
    """
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT OR REPLACE INTO migrations (migration_name, applied_at, description)
        VALUES (?, ?, ?)
    """, (migration_name, now, description))

    conn.commit()


def run_auth_migrations(conn: sqlite3.Connection) -> None:
    """
    Run all pending auth migrations.

    This function:
    1. Ensures migration tracking table exists
    2. Checks which auth migrations have been applied
    3. Runs pending migrations in order
    4. Records completion in migrations table

    Safe to call on every startup - migrations are idempotent.

    Args:
        conn: SQLite database connection

    Raises:
        Exception: If a migration fails
    """
    try:
        logger.info("Running auth migrations...")

        # Ensure migration tracking table exists
        _ensure_migration_table(conn)

        # List of auth migrations in order
        # Format: (module_name, migration_name, description)
        migrations = [
            ("0001_initial", "auth_0001_initial", "Initial auth/permissions schema consolidation"),
            ("0002_founder_role", "auth_0002_founder_role", "Normalize Founder account role"),
        ]

        applied_count = 0

        for module_name, migration_name, description in migrations:
            # Check if already applied
            if _is_migration_applied(conn, migration_name):
                logger.debug(f"  ✓ {migration_name} already applied")
                continue

            # Import and run migration
            logger.info(f"  Applying {migration_name}...")

            try:
                # Import the migration module dynamically using importlib
                # (Can't use 'from . import 0001_initial' due to leading digit)
                import importlib
                migration_module = importlib.import_module(f".{module_name}", package="api.migrations.auth")

                # Run the migration
                migration_module.apply_migration(conn)

                # Record completion
                _record_migration(conn, migration_name, description)

                applied_count += 1
                logger.info(f"  ✅ {migration_name} completed")

            except Exception as e:
                logger.error(f"  ❌ {migration_name} failed: {e}", exc_info=True)
                raise

        if applied_count > 0:
            logger.info(f"✅ Applied {applied_count} auth migration(s)")
        else:
            logger.info("✅ Auth migrations up to date")

    except Exception as e:
        logger.error(f"Auth migrations failed: {e}", exc_info=True)
        raise
