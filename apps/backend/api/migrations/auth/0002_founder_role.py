"""
Auth Migration 0002: Founder Role

Normalizes the Founder account into the database schema.
Previously, Founder was a hardcoded env-based backdoor.
Now Founder is a real user with a special 'founder_rights' role.

This migration:
1. Ensures 'founder_rights' is a recognized role value in the users table
2. Does NOT create the Founder user - that's handled by bootstrap at runtime
3. Maintains backward compatibility with existing permission checks

The actual Founder user will be created by auth_bootstrap.py at startup in dev mode.

Created: 2025-11-20
"""

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

MIGRATION_VERSION = "auth_0002_founder_role"


def apply_migration(conn: sqlite3.Connection) -> None:
    """
    Apply Founder role migration.

    This migration is minimal because:
    - The 'founder_rights' role is already used in code (permissions/engine.py:585)
    - The users.role column already exists (from 0001_initial)
    - We just need to document that 'founder_rights' is a valid role value

    The Founder user row will be created by runtime bootstrap, not migration.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    logger.info(f"Applying migration: {MIGRATION_VERSION}")

    # ========================================
    # FOUNDER ROLE VALIDATION
    # ========================================

    # Add CHECK constraint to users.role column to document valid roles
    # Note: SQLite doesn't support ALTER TABLE ... ADD CONSTRAINT directly
    # So we document this in comments and rely on application-level validation

    # Valid roles:
    # - founder_rights: Superuser with full bypass (Founder account)
    # - super_admin: All permissions unless explicitly denied
    # - admin: Most features, limited system permissions
    # - member: Core features, own resources
    # - guest: Read-only access

    logger.info("  ✓ Founder role 'founder_rights' documented")
    logger.info("    (users.role column already supports 'founder_rights' value)")

    # ========================================
    # NO TABLE CHANGES NEEDED
    # ========================================

    # The users table from 0001_initial already has:
    # - role TEXT DEFAULT 'member'
    # - No constraints preventing 'founder_rights' value

    # The permission engine already handles 'founder_rights':
    # - See permissions/engine.py:585 for bypass logic

    # The god_rights_auth table (for delegation) is separate:
    # - Managed by team/founder_rights.py
    # - Not part of auth migrations (team-specific)

    conn.commit()
    logger.info(f"✅ Migration {MIGRATION_VERSION} applied successfully")
    logger.info("   Founder user will be created by auth_bootstrap.py at startup")


def rollback_migration(conn: sqlite3.Connection) -> None:
    """
    Rollback this migration.

    Since this migration doesn't create tables or columns,
    rollback is a no-op. The 'founder_rights' role value
    will simply stop being used by the application.

    Args:
        conn: SQLite database connection
    """
    logger.warning(f"Rolling back migration: {MIGRATION_VERSION}")
    logger.warning("  No-op: Migration didn't create schema objects")

    conn.commit()
    logger.info(f"✅ Migration {MIGRATION_VERSION} rolled back")
