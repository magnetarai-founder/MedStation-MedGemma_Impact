#!/usr/bin/env python3
"""
Phase 0 Migration: Database Architecture Consolidation
Created: 2025-11-02

This migration consolidates the multi-database user architecture into a single
authoritative database (elohimos_app.db) following Option B: Multi-user system.

Changes:
1. Ensures auth.users table has role and job_role columns
2. Creates user_profiles table in elohimos_app.db for profile data
3. Migrates any existing data from legacy users.db into user_profiles
4. Leaves docs.db and workflows.db unchanged (future phases)

See: docs/dev/SECURITY_AND_PERMISSIONS_ARCHITECTURE.md Phase 0
"""

import os
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def migrate_phase0_user_db(app_db_path: Path, legacy_users_db_path: Path) -> bool:
    """
    Run Phase 0 database consolidation migration

    Args:
        app_db_path: Path to elohimos_app.db (authoritative database)
        legacy_users_db_path: Path to legacy .neutron_data/users.db

    Returns:
        True if migration succeeded, False otherwise
    """
    try:
        logger.info("=" * 60)
        logger.info("Phase 0 Migration: Database Architecture Consolidation")
        logger.info("=" * 60)

        # ===== Step 1: Ensure app_db exists and has proper auth tables =====
        logger.info(f"Step 1: Ensuring app_db exists at {app_db_path}")

        app_db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(app_db_path))
        cursor = conn.cursor()

        # Create users table if not exists (should already exist from AuthService)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                device_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER DEFAULT 1,
                role TEXT DEFAULT 'member'
            )
        """)

        # Check if role column exists, add if missing
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'role' not in columns:
            logger.info("  Adding 'role' column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'member'")

        if 'job_role' not in columns:
            logger.info("  Adding 'job_role' column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN job_role TEXT DEFAULT 'unassigned'")

        # Create sessions table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                device_fingerprint TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()
        logger.info("  ✓ Auth tables verified in app_db")

        # ===== Step 2: Create user_profiles table =====
        logger.info("Step 2: Creating user_profiles table")

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

        conn.commit()
        logger.info("  ✓ user_profiles table created")

        # ===== Step 3: Migrate users from legacy auth.db if exists =====
        logger.info("Step 3: Migrating users from legacy auth.db")

        legacy_auth_db_path = app_db_path.parent / "auth.db"
        if legacy_auth_db_path.exists() and legacy_auth_db_path != app_db_path:
            try:
                legacy_auth_conn = sqlite3.connect(str(legacy_auth_db_path))
                legacy_auth_conn.row_factory = sqlite3.Row
                legacy_auth_cursor = legacy_auth_conn.cursor()

                # Check if users table exists
                legacy_auth_cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                )
                if legacy_auth_cursor.fetchone():
                    # Get all users from legacy auth.db
                    legacy_auth_cursor.execute("SELECT * FROM users")
                    legacy_auth_users = legacy_auth_cursor.fetchall()

                    if legacy_auth_users:
                        logger.info(f"  Found {len(legacy_auth_users)} user(s) in legacy auth.db")

                        migrated_count = 0
                        for legacy_user in legacy_auth_users:
                            # Migrate auth credentials to new users table
                            # sqlite3.Row doesn't have .get(), use try/except
                            try:
                                last_login = legacy_user['last_login']
                            except (KeyError, IndexError):
                                last_login = None

                            try:
                                is_active = legacy_user['is_active']
                            except (KeyError, IndexError):
                                is_active = 1

                            cursor.execute("""
                                INSERT OR IGNORE INTO users
                                (user_id, username, password_hash, device_id, created_at, last_login, is_active, role)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                legacy_user['user_id'],
                                legacy_user['username'],
                                legacy_user['password_hash'],
                                legacy_user['device_id'],
                                legacy_user['created_at'],
                                last_login,
                                is_active,
                                'member'  # Default role for migrated users
                            ))
                            migrated_count += 1

                        conn.commit()
                        logger.info(f"  ✓ Migrated {migrated_count} user(s) from legacy auth.db")
                    else:
                        logger.info("  Legacy auth.db is empty, skipping migration")
                else:
                    logger.info("  No 'users' table found in legacy auth.db")

                # Also migrate sessions if they exist
                legacy_auth_cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
                )
                if legacy_auth_cursor.fetchone():
                    legacy_auth_cursor.execute("SELECT * FROM sessions")
                    legacy_sessions = legacy_auth_cursor.fetchall()

                    if legacy_sessions:
                        logger.info(f"  Found {len(legacy_sessions)} session(s) in legacy auth.db")
                        session_count = 0
                        for session in legacy_sessions:
                            # sqlite3.Row doesn't have .get(), use try/except
                            try:
                                device_fingerprint = session['device_fingerprint']
                            except (KeyError, IndexError):
                                device_fingerprint = None

                            cursor.execute("""
                                INSERT OR IGNORE INTO sessions
                                (session_id, user_id, token_hash, created_at, expires_at, device_fingerprint)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                session['session_id'],
                                session['user_id'],
                                session['token_hash'],
                                session['created_at'],
                                session['expires_at'],
                                device_fingerprint
                            ))
                            session_count += 1

                        conn.commit()
                        logger.info(f"  ✓ Migrated {session_count} session(s) from legacy auth.db")

                legacy_auth_conn.close()

            except Exception as e:
                logger.warning(f"  Failed to migrate from legacy auth.db: {e}")
                logger.info("  Continuing without legacy auth migration")
        else:
            if legacy_auth_db_path == app_db_path:
                logger.info("  Legacy auth.db is now app_db (already consolidated)")
            else:
                logger.info("  No legacy auth.db found at expected location")

        # ===== Step 4: Migrate data from legacy users.db if exists =====
        logger.info("Step 4: Checking for legacy users.db data")

        if legacy_users_db_path.exists():
            try:
                legacy_conn = sqlite3.connect(str(legacy_users_db_path))
                legacy_conn.row_factory = sqlite3.Row
                legacy_cursor = legacy_conn.cursor()

                # Check if users table exists in legacy DB
                legacy_cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                )
                if legacy_cursor.fetchone():
                    # Get all users from legacy DB
                    legacy_cursor.execute("SELECT * FROM users")
                    legacy_users = legacy_cursor.fetchall()

                    if legacy_users:
                        logger.info(f"  Found {len(legacy_users)} user(s) in legacy users.db")

                        migrated_count = 0
                        for legacy_user in legacy_users:
                            # Map legacy user to user_profiles
                            # Note: We don't migrate auth credentials, only profile data
                            # sqlite3.Row doesn't have .get(), use try/except for missing columns
                            try:
                                avatar_color = legacy_user['avatar_color']
                            except (KeyError, IndexError):
                                avatar_color = None

                            try:
                                bio = legacy_user['bio']
                            except (KeyError, IndexError):
                                bio = None

                            cursor.execute("""
                                INSERT OR IGNORE INTO user_profiles
                                (user_id, display_name, device_name, created_at, avatar_color, bio)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                legacy_user['user_id'],
                                legacy_user['display_name'],
                                legacy_user['device_name'],
                                legacy_user['created_at'],
                                avatar_color,
                                bio
                            ))

                            # If the user has a role in legacy DB, try to update auth.users
                            try:
                                if legacy_user['role']:
                                    cursor.execute("""
                                        UPDATE users SET role = ? WHERE user_id = ?
                                    """, (legacy_user['role'], legacy_user['user_id']))
                            except (KeyError, IndexError):
                                pass

                            try:
                                if legacy_user['job_role']:
                                    cursor.execute("""
                                        UPDATE users SET job_role = ? WHERE user_id = ?
                                    """, (legacy_user['job_role'], legacy_user['user_id']))
                            except (KeyError, IndexError):
                                pass

                            migrated_count += 1

                        conn.commit()
                        logger.info(f"  ✓ Migrated {migrated_count} profile(s) from legacy users.db")
                    else:
                        logger.info("  Legacy users.db is empty, skipping migration")
                else:
                    logger.info("  No 'users' table found in legacy users.db")

                legacy_conn.close()

            except Exception as e:
                logger.warning(f"  Failed to migrate from legacy users.db: {e}")
                logger.info("  Continuing without legacy data migration")
        else:
            logger.info("  No legacy users.db found at expected location")

        # ===== Step 5: Create migration tracking =====
        logger.info("Step 5: Recording migration completion")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                migration_name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT
            )
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO migrations (migration_name, applied_at, description)
            VALUES (?, ?, ?)
        """, (
            '2025_11_02_phase0_user_db',
            datetime.utcnow().isoformat(),
            'Phase 0: Database Architecture Consolidation - Multi-user with single app_db'
        ))

        conn.commit()
        conn.close()

        logger.info("=" * 60)
        logger.info("✓ Phase 0 Migration completed successfully")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"✗ Phase 0 Migration failed: {e}", exc_info=True)
        return False


def check_migration_applied(app_db_path: Path) -> bool:
    """
    Check if Phase 0 migration has already been applied

    Args:
        app_db_path: Path to elohimos_app.db

    Returns:
        True if migration has been applied, False otherwise
    """
    try:
        if not app_db_path.exists():
            return False

        conn = sqlite3.connect(str(app_db_path))
        cursor = conn.cursor()

        # Check if migrations table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'"
        )
        if not cursor.fetchone():
            conn.close()
            return False

        # Check if this specific migration has been applied
        cursor.execute(
            "SELECT applied_at FROM migrations WHERE migration_name = ?",
            ('2025_11_02_phase0_user_db',)
        )
        result = cursor.fetchone()
        conn.close()

        return result is not None

    except Exception as e:
        logger.error(f"Failed to check migration status: {e}")
        return False
