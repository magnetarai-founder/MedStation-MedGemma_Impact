#!/usr/bin/env python3
"""
User Isolation Migration Script

Adds user_id columns to all tables for multi-user isolation.
This is a CRITICAL security migration.

Usage:
    python migrate_add_user_isolation.py --dry-run  # Preview changes
    python migrate_add_user_isolation.py --backup   # Backup first, then migrate
    python migrate_add_user_isolation.py --execute  # Execute migration (scary!)
    python migrate_add_user_isolation.py --rollback # Rollback migration

IMPORTANT: Always backup first!
"""

import sqlite3
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get database paths
from api.config_paths import get_config_paths
PATHS = get_config_paths()

# All databases that need migration
DATABASES = {
    "medstationos_app.db": PATHS.data_dir / "medstationos_app.db",
    "chat_memory.db": PATHS.memory_dir / "chat_memory.db",
    "vault.db": PATHS.data_dir / "vault.db",
    "docs.db": PATHS.data_dir / "docs.db",
    "users.db": PATHS.data_dir / "users.db",
    "teams.db": PATHS.data_dir / "teams.db",
}

# Tables that need user_id column
# Format: {database: [(table, has_created_by_column)]}
TABLES_TO_MIGRATE = {
    "medstationos_app.db": [
        ("chat_sessions", False),
        ("chat_messages", False),
        ("conversation_summaries", False),
        ("documents", True),  # Has created_by, we'll add user_id separately
        ("document_chunks", False),
        ("message_embeddings", False),
        ("workflows", False),
        ("work_items", False),
        ("attachments", False),
    ],
    "chat_memory.db": [
        ("chat_sessions", False),
        ("chat_messages", False),
        ("conversation_summaries", False),
        ("document_chunks", False),
    ],
    # vault.db and docs.db might have user_id already, check first
    # users.db doesn't need migration (it IS the users table)
    # teams.db needs team-level filtering, not user_id
}


class MigrationError(Exception):
    """Migration failed"""
    pass


def backup_databases(backup_dir: Path) -> None:
    """Backup all databases before migration"""
    backup_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"📦 Backing up databases to {backup_dir}")

    for db_name, db_path in DATABASES.items():
        if not db_path.exists():
            logger.warning(f"⚠️  Database not found: {db_path}")
            continue

        backup_path = backup_dir / db_name
        shutil.copy2(db_path, backup_path)
        logger.info(f"   ✓ Backed up {db_name}")

    logger.info("✅ Backup complete")


def get_first_user_id() -> str:
    """Get the first user ID to assign to existing data"""
    users_db = DATABASES["users.db"]

    if not users_db.exists():
        logger.warning("⚠️  No users.db found - will use placeholder user_id")
        return "migration_user_default"

    conn = sqlite3.connect(str(users_db))
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT user_id FROM users ORDER BY created_at ASC LIMIT 1")
        row = cursor.fetchone()

        if row:
            user_id = row[0]
            logger.info(f"📝 First user found: {user_id}")
            return user_id
        else:
            logger.warning("⚠️  No users in database - will use placeholder user_id")
            return "migration_user_default"
    finally:
        conn.close()


def table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if table already has a column"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate_database(db_path: Path, tables: list, first_user_id: str, dry_run: bool = False) -> None:
    """Migrate a single database"""
    if not db_path.exists():
        logger.warning(f"⚠️  Database not found: {db_path}")
        return

    logger.info(f"\n{'[DRY RUN] ' if dry_run else ''}🔧 Migrating {db_path.name}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        for table, has_created_by in tables:
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                logger.warning(f"   ⚠️  Table not found: {table}")
                continue

            # Check if user_id already exists
            if table_has_column(conn, table, "user_id"):
                logger.info(f"   ℹ️  {table} already has user_id column, skipping")
                continue

            # Add user_id column
            logger.info(f"   + Adding user_id to {table}")

            if not dry_run:
                # Add column with default value
                cursor.execute(f"""
                    ALTER TABLE {table}
                    ADD COLUMN user_id TEXT DEFAULT 'migration_needed'
                """)

                # Update existing rows with first user's ID
                cursor.execute(f"""
                    UPDATE {table}
                    SET user_id = ?
                    WHERE user_id = 'migration_needed'
                """, (first_user_id,))

                rows_updated = cursor.rowcount
                logger.info(f"     ✓ Updated {rows_updated} rows with user_id: {first_user_id}")

                # Create index for performance
                index_name = f"idx_{table}_user_id"
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name}
                    ON {table}(user_id)
                """)
                logger.info(f"     ✓ Created index: {index_name}")

        if not dry_run:
            conn.commit()
            logger.info(f"✅ {db_path.name} migration complete")
        else:
            logger.info(f"[DRY RUN] Would migrate {db_path.name}")

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Migration failed for {db_path.name}: {e}")
        raise MigrationError(f"Failed to migrate {db_path.name}") from e

    finally:
        conn.close()


def rollback_migration(backup_dir: Path) -> bool:
    """Rollback migration by restoring from backup"""
    if not backup_dir.exists():
        logger.error(f"❌ Backup directory not found: {backup_dir}")
        return False

    logger.info(f"🔄 Rolling back from backup: {backup_dir}")

    for db_name, db_path in DATABASES.items():
        backup_path = backup_dir / db_name

        if not backup_path.exists():
            logger.warning(f"⚠️  Backup not found for: {db_name}")
            continue

        shutil.copy2(backup_path, db_path)
        logger.info(f"   ✓ Restored {db_name}")

    logger.info("✅ Rollback complete")
    return True


def verify_migration() -> bool:
    """Verify that migration was successful"""
    logger.info("\n🔍 Verifying migration...")

    all_good = True

    for db_name, tables in TABLES_TO_MIGRATE.items():
        db_path = DATABASES[db_name]

        if not db_path.exists():
            continue

        conn = sqlite3.connect(str(db_path))

        for table, _ in tables:
            # Check if user_id exists
            if not table_has_column(conn, table, "user_id"):
                logger.error(f"❌ {db_name}::{table} missing user_id column")
                all_good = False
                continue

            # Check if index exists
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT name FROM sqlite_master
                WHERE type='index' AND name='idx_{table}_user_id'
            """)

            if not cursor.fetchone():
                logger.warning(f"⚠️  {db_name}::{table} missing user_id index")
                all_good = False
            else:
                logger.info(f"   ✓ {db_name}::{table} has user_id + index")

        conn.close()

    if all_good:
        logger.info("✅ Migration verification passed")
    else:
        logger.error("❌ Migration verification failed")

    return all_good


def main() -> None:
    parser = argparse.ArgumentParser(description='MedStation User Isolation Migration')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without executing')
    parser.add_argument('--backup', action='store_true', help='Backup databases and execute migration')
    parser.add_argument('--execute', action='store_true', help='Execute migration (requires manual backup first)')
    parser.add_argument('--rollback', type=str, help='Rollback to backup directory')
    parser.add_argument('--verify', action='store_true', help='Verify migration was successful')

    args = parser.parse_args()

    # Rollback mode
    if args.rollback:
        backup_dir = Path(args.rollback)
        success = rollback_migration(backup_dir)
        sys.exit(0 if success else 1)

    # Verify mode
    if args.verify:
        success = verify_migration()
        sys.exit(0 if success else 1)

    # Must specify either dry-run, backup, or execute
    if not (args.dry_run or args.backup or args.execute):
        parser.print_help()
        print("\n❌ Must specify --dry-run, --backup, or --execute")
        sys.exit(1)

    # Get first user ID
    first_user_id = get_first_user_id()

    # Backup if requested
    backup_dir = None
    if args.backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = PATHS.data_dir / f"migration_backup_{timestamp}"
        backup_databases(backup_dir)

    # Execute migration
    try:
        for db_name, tables in TABLES_TO_MIGRATE.items():
            db_path = DATABASES[db_name]
            migrate_database(db_path, tables, first_user_id, dry_run=args.dry_run)

        if not args.dry_run:
            # Verify migration
            if verify_migration():
                logger.info("\n✅ MIGRATION COMPLETE!")
                if backup_dir:
                    logger.info(f"📦 Backup saved to: {backup_dir}")
                    logger.info(f"   To rollback: python {__file__} --rollback {backup_dir}")
            else:
                logger.error("\n❌ MIGRATION COMPLETED BUT VERIFICATION FAILED")
                if backup_dir:
                    logger.info(f"   To rollback: python {__file__} --rollback {backup_dir}")
                sys.exit(1)

    except MigrationError as e:
        logger.error(f"\n❌ MIGRATION FAILED: {e}")
        if backup_dir:
            logger.info(f"   To rollback: python {__file__} --rollback {backup_dir}")
        sys.exit(1)


if __name__ == "__main__":
    main()
