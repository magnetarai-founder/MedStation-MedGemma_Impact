"""
One-time database consolidation migration

Consolidates 7+ databases into 3:
- elohimos_app.db (auth, users, docs, chat, workflows)
- vault.db (security-sensitive, kept separate)
- datasets.db (user data, kept separate)

Run this ONCE to migrate existing data.
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

# Old database paths
OLD_DBS = {
    "auth": Path(".neutron_data/auth.db"),
    "users": Path(".neutron_data/users.db"),
    "docs": Path(".neutron_data/docs.db"),
    "chat": Path(".neutron_data/memory/chat_memory.db"),
    "workflows": Path("data/workflows.db"),
}

# New consolidated database
NEW_APP_DB = Path(".neutron_data/elohimos_app.db")

# Backup directory
BACKUP_DIR = Path(".neutron_data/db_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))


def backup_old_databases():
    """Backup old databases before migration"""
    print("📦 Backing up old databases...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    for name, db_path in OLD_DBS.items():
        if db_path.exists():
            backup_path = BACKUP_DIR / f"{name}_{db_path.name}"
            shutil.copy2(db_path, backup_path)
            print(f"   ✓ Backed up {db_path} → {backup_path}")


def attach_and_copy(conn, db_name, db_path):
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
            # Get table schema
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
        except:
            pass


def migrate_databases():
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
