"""
Auth Migration 0001: Initial Schema

Consolidates all existing auth/permissions schema into a single migration.
This migration reflects the CURRENT STATE of the auth system after:
- Phase 0 (user_db)
- Phase 2 (permissions_rbac)
- Phase 2.5 (rbac_hardening)

Schema includes:
1. Authentication: users, sessions
2. User profiles: user_profiles
3. Permissions registry: permissions
4. RBAC profiles: permission_profiles, profile_permissions
5. Permission sets: permission_sets, permission_set_permissions
6. User assignments: user_permission_profiles, user_permission_sets
7. Optional caching: user_permissions_cache

Created: 2025-11-20
"""

import sqlite3
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

MIGRATION_VERSION = "auth_0001_initial"


def apply_migration(conn: sqlite3.Connection) -> None:
    """
    Apply initial auth schema migration.

    Creates all auth/permissions tables matching current production state.
    Uses CREATE TABLE IF NOT EXISTS for idempotency - safe to run multiple times.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    logger.info(f"Applying migration: {MIGRATION_VERSION}")

    # ========================================
    # AUTHENTICATION TABLES
    # ========================================

    # Table: users (identity and credentials)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            device_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_login TEXT,
            is_active INTEGER DEFAULT 1,
            role TEXT DEFAULT 'member',
            job_role TEXT
        )
    """)
    logger.info("  ✓ users table")

    # Table: sessions (JWT token sessions)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            refresh_token_hash TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            refresh_expires_at TEXT,
            device_fingerprint TEXT,
            last_activity TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    logger.info("  ✓ sessions table")

    # Indexes for sessions
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user
        ON sessions(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_expires
        ON sessions(expires_at)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_last_activity
        ON sessions(last_activity)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_expires_user
        ON sessions(expires_at, user_id)
    """)
    logger.info("  ✓ sessions indexes")

    # ========================================
    # USER PROFILES
    # ========================================

    # Table: user_profiles (profile data separate from auth)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            device_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            avatar_color TEXT,
            bio TEXT,
            role_changed_at TEXT,
            role_changed_by TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
    logger.info("  ✓ user_profiles table")

    # ========================================
    # PERMISSIONS REGISTRY
    # ========================================

    # Table: permissions (registry of all available permissions)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            permission_id TEXT PRIMARY KEY,
            permission_key TEXT NOT NULL UNIQUE,
            permission_name TEXT NOT NULL,
            permission_description TEXT,
            category TEXT NOT NULL,
            subcategory TEXT,
            permission_type TEXT NOT NULL CHECK(permission_type IN ('boolean', 'level', 'scope')),
            is_system INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    logger.info("  ✓ permissions table")

    # Indexes for permissions
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_permissions_key
        ON permissions(permission_key)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_permissions_category
        ON permissions(category)
    """)
    logger.info("  ✓ permissions indexes")

    # ========================================
    # RBAC PROFILES
    # ========================================

    # Table: permission_profiles (reusable permission bundles)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permission_profiles (
            profile_id TEXT PRIMARY KEY,
            profile_name TEXT NOT NULL,
            profile_description TEXT,
            team_id TEXT,
            applies_to_role TEXT CHECK(applies_to_role IN ('admin', 'member', 'guest', 'any')),
            created_by TEXT,
            created_at TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """)
    logger.info("  ✓ permission_profiles table")

    # Table: profile_permissions (join table: profile -> permissions)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile_permissions (
            profile_id TEXT NOT NULL,
            permission_id TEXT NOT NULL,
            is_granted INTEGER DEFAULT 1,
            permission_level TEXT CHECK(permission_level IN ('none', 'read', 'write', 'admin')),
            permission_scope TEXT,
            PRIMARY KEY (profile_id, permission_id),
            FOREIGN KEY (profile_id) REFERENCES permission_profiles(profile_id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions(permission_id) ON DELETE CASCADE
        )
    """)
    logger.info("  ✓ profile_permissions table")

    # Indexes for profiles
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_profiles_role
        ON permission_profiles(applies_to_role)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_profiles_active
        ON permission_profiles(is_active)
    """)
    logger.info("  ✓ permission_profiles indexes")

    # ========================================
    # PERMISSION SETS
    # ========================================

    # Table: permission_sets (ad-hoc permission grants)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permission_sets (
            permission_set_id TEXT PRIMARY KEY,
            set_name TEXT NOT NULL,
            set_description TEXT,
            team_id TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """)
    logger.info("  ✓ permission_sets table")

    # Table: permission_set_permissions (permissions granted by sets)
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
    logger.info("  ✓ permission_set_permissions table")

    # Indexes for permission sets
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_permission_set_permissions_set_id
        ON permission_set_permissions(permission_set_id)
    """)
    logger.info("  ✓ permission_set_permissions indexes")

    # ========================================
    # USER ASSIGNMENTS
    # ========================================

    # Table: user_permission_profiles (user -> profile assignments)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_permission_profiles (
            user_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            assigned_by TEXT,
            assigned_at TEXT NOT NULL,
            PRIMARY KEY (user_id, profile_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES permission_profiles(profile_id) ON DELETE CASCADE
        )
    """)
    logger.info("  ✓ user_permission_profiles table")

    # Table: user_permission_sets (user -> permission set assignments)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_permission_sets (
            user_id TEXT NOT NULL,
            permission_set_id TEXT NOT NULL,
            assigned_by TEXT,
            assigned_at TEXT NOT NULL,
            expires_at TEXT,
            PRIMARY KEY (user_id, permission_set_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (permission_set_id) REFERENCES permission_sets(permission_set_id) ON DELETE CASCADE
        )
    """)
    logger.info("  ✓ user_permission_sets table")

    # Indexes for user assignments
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_profiles_user
        ON user_permission_profiles(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_profiles_profile
        ON user_permission_profiles(profile_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_sets_user
        ON user_permission_sets(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_sets_set
        ON user_permission_sets(permission_set_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_permission_sets_user_id
        ON user_permission_sets(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_permission_profiles_user_id
        ON user_permission_profiles(user_id)
    """)
    logger.info("  ✓ user assignment indexes")

    # ========================================
    # OPTIONAL CACHING
    # ========================================

    # Table: user_permissions_cache (optional DB-level caching)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_permissions_cache (
            user_id TEXT PRIMARY KEY,
            permissions_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
    logger.info("  ✓ user_permissions_cache table")

    conn.commit()
    logger.info(f"✅ Migration {MIGRATION_VERSION} applied successfully")


def rollback_migration(conn: sqlite3.Connection) -> None:
    """
    Rollback this migration.

    WARNING: This will DROP ALL AUTH TABLES. Only use for testing.
    In production, auth tables should never be dropped.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    logger.warning(f"Rolling back migration: {MIGRATION_VERSION}")
    logger.warning("⚠️  This will DROP ALL AUTH TABLES")

    # Drop in reverse order of dependencies
    tables_to_drop = [
        "user_permissions_cache",
        "user_permission_sets",
        "user_permission_profiles",
        "permission_set_permissions",
        "permission_sets",
        "profile_permissions",
        "permission_profiles",
        "permissions",
        "user_profiles",
        "sessions",
        "users",
    ]

    for table in tables_to_drop:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        logger.info(f"  ✓ Dropped {table}")

    conn.commit()
    logger.warning(f"⚠️  Migration {MIGRATION_VERSION} rolled back")
