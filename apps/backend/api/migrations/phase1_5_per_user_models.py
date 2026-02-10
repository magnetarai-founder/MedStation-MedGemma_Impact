#!/usr/bin/env python3
"""
Phase 1.5 Migration: Per-User Model Preferences and Hot Slots
Created: 2025-11-12

This migration implements per-user model preferences and hot slots,
moving from global system-wide settings to individual user control.

Changes:
1. Creates user_model_preferences table for per-user model visibility
2. Creates user_hot_slots table for per-user favorite model slots
3. Creates model_installations table for global model catalog
4. Adds setup_completed column to users table for per-user wizard tracking
5. Migrates existing hot slots JSON to database (for founder/first admin)

See: docs/SETUP_WIZARD_ARCHITECTURE_REDESIGN.md Phase 1.5
"""

import os
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


def migrate_phase1_5_per_user_models(app_db_path: Path, config_dir: Path) -> bool:
    """
    Run Phase 1.5 per-user model preferences migration

    Args:
        app_db_path: Path to medstation.db (authoritative database)
        config_dir: Path to config directory (for hot_slots.json)

    Returns:
        True if migration succeeded, False otherwise
    """
    try:
        logger.info("=" * 60)
        logger.info("Phase 1.5 Migration: Per-User Model Preferences")
        logger.info("=" * 60)

        # ===== Step 1: Ensure app_db exists =====
        logger.info(f"Step 1: Connecting to app_db at {app_db_path}")

        if not app_db_path.exists():
            logger.error(f"  ✗ app_db not found at {app_db_path}")
            return False

        conn = sqlite3.connect(str(app_db_path))
        cursor = conn.cursor()

        # ===== Step 2: Add setup_completed to users table =====
        logger.info("Step 2: Adding setup_completed column to users table")

        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'setup_completed' not in columns:
            logger.info("  Adding 'setup_completed' column")
            cursor.execute("ALTER TABLE users ADD COLUMN setup_completed INTEGER DEFAULT 0")
            conn.commit()
            logger.info("  ✓ setup_completed column added")
        else:
            logger.info("  setup_completed column already exists")

        if 'setup_completed_at' not in columns:
            logger.info("  Adding 'setup_completed_at' column")
            cursor.execute("ALTER TABLE users ADD COLUMN setup_completed_at TEXT")
            conn.commit()
            logger.info("  ✓ setup_completed_at column added")
        else:
            logger.info("  setup_completed_at column already exists")

        # ===== Step 3: Create model_installations table (global catalog) =====
        logger.info("Step 3: Creating model_installations table")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_installations (
                model_name TEXT PRIMARY KEY,
                size TEXT,
                status TEXT CHECK (status IN ('installed', 'downloading', 'failed', 'unknown')) DEFAULT 'installed',
                installed_at TEXT,
                last_seen TEXT,
                metadata TEXT
            )
        """)

        conn.commit()
        logger.info("  ✓ model_installations table created")

        # ===== Step 4: Create user_model_preferences table =====
        logger.info("Step 4: Creating user_model_preferences table")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_model_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                visible INTEGER DEFAULT 1,
                preferred INTEGER DEFAULT 0,
                display_order INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, model_name)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_model_prefs_user
            ON user_model_preferences(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_model_prefs_visible
            ON user_model_preferences(user_id, visible)
        """)

        conn.commit()
        logger.info("  ✓ user_model_preferences table created with indexes")

        # ===== Step 5: Create user_hot_slots table =====
        logger.info("Step 5: Creating user_hot_slots table")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_hot_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                slot_number INTEGER NOT NULL CHECK (slot_number BETWEEN 1 AND 4),
                model_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, slot_number)
            )
        """)

        # Create index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_hot_slots_user
            ON user_hot_slots(user_id)
        """)

        conn.commit()
        logger.info("  ✓ user_hot_slots table created with index")

        # ===== Step 6: Migrate hot slots from JSON (if exists) =====
        logger.info("Step 6: Migrating hot slots from JSON (if exists)")

        hot_slots_json_path = config_dir / "model_hot_slots.json"

        if hot_slots_json_path.exists():
            try:
                with open(hot_slots_json_path, 'r') as f:
                    hot_slots_data = json.load(f)

                logger.info(f"  Found hot slots JSON: {hot_slots_data}")

                # Get first super_admin or founder user to assign legacy slots to
                cursor.execute("""
                    SELECT user_id FROM users
                    WHERE role IN ('super_admin', 'founder')
                    ORDER BY created_at ASC
                    LIMIT 1
                """)
                founder_user = cursor.fetchone()

                if founder_user:
                    user_id = founder_user[0]
                    logger.info(f"  Migrating hot slots to user: {user_id}")

                    migrated_count = 0
                    for slot_num_str, model_name in hot_slots_data.items():
                        try:
                            slot_num = int(slot_num_str)
                            if 1 <= slot_num <= 4 and model_name:
                                cursor.execute("""
                                    INSERT OR IGNORE INTO user_hot_slots
                                    (user_id, slot_number, model_name, created_at, updated_at)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (
                                    user_id,
                                    slot_num,
                                    model_name,
                                    datetime.now(UTC).isoformat(),
                                    datetime.now(UTC).isoformat()
                                ))
                                migrated_count += 1
                        except (ValueError, TypeError) as e:
                            logger.warning(f"  Skipping invalid slot entry {slot_num_str}: {e}")

                    conn.commit()
                    logger.info(f"  ✓ Migrated {migrated_count} hot slot(s) from JSON")

                    # Rename JSON file to mark as migrated (don't delete - audit trail)
                    backup_path = config_dir / "model_hot_slots.json.migrated"
                    hot_slots_json_path.rename(backup_path)
                    logger.info(f"  ✓ Renamed JSON to {backup_path.name}")
                else:
                    logger.info("  No founder/super_admin user found - skipping JSON migration")

            except Exception as e:
                logger.warning(f"  Failed to migrate hot slots JSON: {e}")
                logger.info("  Continuing without JSON migration")
        else:
            logger.info("  No hot slots JSON found - skipping migration")

        # ===== Step 7: Create migration tracking =====
        logger.info("Step 7: Recording migration completion")

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
            '2025_11_12_phase1_5_per_user_models',
            datetime.now(UTC).isoformat(),
            'Phase 1.5: Per-User Model Preferences and Hot Slots'
        ))

        conn.commit()
        conn.close()

        logger.info("=" * 60)
        logger.info("✓ Phase 1.5 Migration completed successfully")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"✗ Phase 1.5 Migration failed: {e}", exc_info=True)
        return False


def check_migration_applied(app_db_path: Path) -> bool:
    """
    Check if Phase 1.5 migration has already been applied

    Args:
        app_db_path: Path to medstation.db

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
            ('2025_11_12_phase1_5_per_user_models',)
        )
        result = cursor.fetchone()
        conn.close()

        return result is not None

    except Exception as e:
        logger.error(f"Failed to check migration status: {e}")
        return False
