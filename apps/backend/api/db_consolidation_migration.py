"""
One-time database consolidation migration

Consolidates 7+ databases into 3:
- elohimos_app.db (auth, users, docs, chat, workflows)
- vault.db (security-sensitive, kept separate)
- datasets.db (user data, kept separate)

Run this ONCE to migrate existing data.
"""

import re
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

# Security: Regex pattern for valid SQLite identifiers (table/column names)
# Only allows alphanumeric characters and underscores, must start with letter or underscore
_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_identifier(name: str, kind: str = "identifier") -> None:
    """
    Validate SQL identifier to prevent SQL injection.

    Args:
        name: The identifier to validate (table name, column name, etc.)
        kind: Type of identifier for error messages

    Raises:
        ValueError: If identifier contains invalid characters
    """
    if not isinstance(name, str) or not _IDENTIFIER_PATTERN.match(name):
        raise ValueError(f"Invalid {kind}: {name!r} - must match pattern [a-zA-Z_][a-zA-Z0-9_]*")

# Use centralized config paths
from api.config_paths import get_config_paths
PATHS = get_config_paths()

# Old database paths
OLD_DBS = {
    "auth": PATHS.data_dir / "auth.db",
    "users": PATHS.data_dir / "users.db",
    "docs": PATHS.data_dir / "docs.db",
    "chat": PATHS.memory_dir / "chat_memory.db",
    "workflows": PATHS.data_dir / "workflows.db",  # Now stored in .neutron_data/
}

# New consolidated database
NEW_APP_DB = PATHS.data_dir / "elohimos_app.db"

# Backup directory
BACKUP_DIR = PATHS.data_dir / f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def backup_old_databases() -> None:
    """Backup old databases before migration"""
    print("📦 Backing up old databases...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    for name, db_path in OLD_DBS.items():
        if db_path.exists():
            backup_path = BACKUP_DIR / f"{name}_{db_path.name}"
            shutil.copy2(db_path, backup_path)
            print(f"   ✓ Backed up {db_path} → {backup_path}")


def attach_and_copy(conn: sqlite3.Connection, db_name: str, db_path: Path) -> None:
    """Attach a database and copy all its tables"""
    if not db_path.exists():
        print(f"   ⚠️  Skipping {db_name} (file not found: {db_path})")
        return

    cursor = conn.cursor()

    try:
        # Attach the old database
        cursor.execute(f"ATTACH DATABASE '{db_path}' AS {db_name}")

        # Get all tables from the attached database
        cursor.execute(f"SELECT name FROM {db_name}.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()

        if not tables:
            print(f"   ⚠️  No tables found in {db_name}")
            cursor.execute(f"DETACH DATABASE {db_name}")
            return

        for (table_name,) in tables:
            # Security: Validate table name before using in SQL
            # This prevents SQL injection if the source database contains malicious table names
            _validate_identifier(table_name, "table name")

            # Get table schema (db_name is from hardcoded OLD_DBS dict, table_name is now validated)
            cursor.execute(f"SELECT sql FROM {db_name}.sqlite_master WHERE type='table' AND name='{table_name}'")
            create_sql = cursor.fetchone()[0]

            # Create table in new database if it doesn't exist
            cursor.execute(create_sql)

            # Copy data
            cursor.execute(f"SELECT COUNT(*) FROM {db_name}.{table_name}")
            row_count = cursor.fetchone()[0]

            if row_count > 0:
                cursor.execute(f"INSERT OR IGNORE INTO {table_name} SELECT * FROM {db_name}.{table_name}")
                print(f"   ✓ Copied {row_count} rows from {db_name}.{table_name}")
            else:
                print(f"   - {db_name}.{table_name} is empty")

        # Detach database
        cursor.execute(f"DETACH DATABASE {db_name}")

    except Exception as e:
        print(f"   ❌ Error migrating {db_name}: {e}")
        try:
            cursor.execute(f"DETACH DATABASE {db_name}")
        except sqlite3.Error:
            pass  # Database already detached or doesn't exist


def migrate_databases() -> None:
    """Main migration function"""
    print("=" * 80)
    print("DATABASE CONSOLIDATION MIGRATION")
    print("=" * 80)

    # Check if already migrated
    if NEW_APP_DB.exists():
        response = input(f"\n⚠️  {NEW_APP_DB} already exists. Overwrite? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled.")
            return

    # Backup old databases
    backup_old_databases()

    # Create new consolidated database
    print(f"\n🔧 Creating new consolidated database: {NEW_APP_DB}")
    NEW_APP_DB.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(NEW_APP_DB)
    conn.execute("PRAGMA foreign_keys = ON")

    # Migrate each old database
    print("\n📊 Migrating data...")
    for db_name, db_path in OLD_DBS.items():
        print(f"\n{db_name.upper()} ({db_path}):")
        attach_and_copy(conn, db_name, db_path)

    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print("✅ MIGRATION COMPLETE")
    print("=" * 80)
    print(f"\nNew database: {NEW_APP_DB}")
    print(f"Backups saved to: {BACKUP_DIR}")
    print("\nOld databases are still in place. After verifying the migration,")
    print("you can safely delete them.")


if __name__ == "__main__":
    migrate_databases()
