#!/usr/bin/env python3
"""
Workflow Database Migration - Add user_id columns

Adds user_id column to all workflow tables for user isolation.
Migrates existing data by mapping created_by to actual user_id.

Phase 1A - User Isolation Foundation
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Database path
DB_PATH = Path(__file__).parent / "data" / "workflows.db"
BACKUP_PATH = Path(__file__).parent / "data" / f"workflows_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

def backup_database():
    """Create backup before migration"""
    import shutil
    print(f"📦 Creating backup: {BACKUP_PATH}")
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"✅ Backup created: {BACKUP_PATH}")


def get_user_id_mapping(conn):
    """
    Map created_by usernames to actual user_ids from auth database

    Returns dict: {username: user_id}
    """
    # Get auth database connection - it's in the same .neutron_data directory
    # Try multiple possible locations
    possible_paths = [
        Path(__file__).parent / ".neutron_data" / "elohimos_app.db",  # Same directory as this script
        Path("apps/backend/api/.neutron_data/elohimos_app.db"),
        Path(__file__).parent.parent.parent.parent / ".neutron_data" / "elohimos_app.db",
        Path(".neutron_data/elohimos_app.db"),
    ]

    auth_db_path = None
    for path in possible_paths:
        if path.exists():
            auth_db_path = path
            break

    if not auth_db_path:
        print(f"⚠️  Auth database not found in any of:")
        for p in possible_paths:
            print(f"     {p}")
        print("⚠️  Will use created_by as user_id (single-user mode)")
        return {}

    print(f"📋 Found auth database at: {auth_db_path}")

    auth_conn = sqlite3.connect(str(auth_db_path))
    cursor = auth_conn.cursor()

    # Get all users
    cursor.execute("SELECT username, user_id FROM users")
    mapping = {row[0]: row[1] for row in cursor.fetchall()}

    auth_conn.close()

    print(f"📋 Found {len(mapping)} users in auth database")
    for username, user_id in mapping.items():
        print(f"   {username} → {user_id}")

    return mapping


def migrate_schema(conn):
    """Add user_id columns to all tables"""
    cursor = conn.cursor()

    print("\n🔧 Adding user_id columns to tables...")

    # 1. Add user_id to workflows table
    print("   Adding user_id to workflows...")
    try:
        cursor.execute("ALTER TABLE workflows ADD COLUMN user_id TEXT")
        print("   ✅ Added user_id to workflows")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("   ⚠️  user_id column already exists in workflows")
        else:
            raise

    # 2. Add user_id to work_items table
    print("   Adding user_id to work_items...")
    try:
        cursor.execute("ALTER TABLE work_items ADD COLUMN user_id TEXT")
        print("   ✅ Added user_id to work_items")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("   ⚠️  user_id column already exists in work_items")
        else:
            raise

    # 3. Add user_id to stage_transitions table
    print("   Adding user_id to stage_transitions...")
    try:
        cursor.execute("ALTER TABLE stage_transitions ADD COLUMN user_id TEXT")
        print("   ✅ Added user_id to stage_transitions")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("   ⚠️  user_id column already exists in stage_transitions")
        else:
            raise

    # 4. Add user_id to attachments table
    print("   Adding user_id to attachments...")
    try:
        cursor.execute("ALTER TABLE attachments ADD COLUMN user_id TEXT")
        print("   ✅ Added user_id to attachments")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("   ⚠️  user_id column already exists in attachments")
        else:
            raise

    conn.commit()
    print("✅ Schema migration complete\n")


def migrate_data(conn, user_mapping):
    """Populate user_id columns based on created_by"""
    cursor = conn.cursor()

    print("📝 Migrating existing data...\n")

    # 1. Migrate workflows
    print("   Migrating workflows...")
    cursor.execute("SELECT id, created_by FROM workflows WHERE user_id IS NULL")
    workflows = cursor.fetchall()

    migrated = 0
    for workflow_id, created_by in workflows:
        # Map created_by to user_id (or use created_by if no mapping)
        user_id = user_mapping.get(created_by, created_by)
        cursor.execute("UPDATE workflows SET user_id = ? WHERE id = ?", (user_id, workflow_id))
        migrated += 1

    print(f"   ✅ Migrated {migrated} workflows")

    # 2. Migrate work_items
    print("   Migrating work_items...")
    cursor.execute("SELECT id, created_by FROM work_items WHERE user_id IS NULL")
    work_items = cursor.fetchall()

    migrated = 0
    for item_id, created_by in work_items:
        user_id = user_mapping.get(created_by, created_by)
        cursor.execute("UPDATE work_items SET user_id = ? WHERE id = ?", (user_id, item_id))
        migrated += 1

    print(f"   ✅ Migrated {migrated} work_items")

    # 3. Migrate stage_transitions (use transitioned_by)
    print("   Migrating stage_transitions...")
    cursor.execute("SELECT id, transitioned_by FROM stage_transitions WHERE user_id IS NULL")
    transitions = cursor.fetchall()

    migrated = 0
    for trans_id, transitioned_by in transitions:
        user_id = user_mapping.get(transitioned_by, transitioned_by)
        cursor.execute("UPDATE stage_transitions SET user_id = ? WHERE id = ?", (user_id, trans_id))
        migrated += 1

    print(f"   ✅ Migrated {migrated} stage_transitions")

    # 4. Migrate attachments (use uploaded_by)
    print("   Migrating attachments...")
    cursor.execute("SELECT id, uploaded_by FROM attachments WHERE user_id IS NULL")
    attachments = cursor.fetchall()

    migrated = 0
    for attach_id, uploaded_by in attachments:
        user_id = user_mapping.get(uploaded_by, uploaded_by)
        cursor.execute("UPDATE attachments SET user_id = ? WHERE id = ?", (user_id, attach_id))
        migrated += 1

    print(f"   ✅ Migrated {migrated} attachments")

    conn.commit()
    print("✅ Data migration complete\n")


def create_indexes(conn):
    """Create indexes on user_id columns for performance"""
    cursor = conn.cursor()

    print("🔍 Creating indexes...")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_user ON workflows(user_id)")
    print("   ✅ Created index on workflows(user_id)")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_items_user ON work_items(user_id)")
    print("   ✅ Created index on work_items(user_id)")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transitions_user ON stage_transitions(user_id)")
    print("   ✅ Created index on stage_transitions(user_id)")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attachments_user ON attachments(user_id)")
    print("   ✅ Created index on attachments(user_id)")

    conn.commit()
    print("✅ Indexes created\n")


def verify_migration(conn):
    """Verify migration was successful"""
    cursor = conn.cursor()

    print("🔍 Verifying migration...\n")

    # Check workflows
    cursor.execute("SELECT COUNT(*) FROM workflows")
    total_workflows = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM workflows WHERE user_id IS NOT NULL")
    migrated_workflows = cursor.fetchone()[0]

    print(f"   Workflows: {migrated_workflows}/{total_workflows} have user_id")

    # Check work_items
    cursor.execute("SELECT COUNT(*) FROM work_items")
    total_items = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM work_items WHERE user_id IS NOT NULL")
    migrated_items = cursor.fetchone()[0]

    print(f"   Work Items: {migrated_items}/{total_items} have user_id")

    # Check transitions
    cursor.execute("SELECT COUNT(*) FROM stage_transitions")
    total_trans = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stage_transitions WHERE user_id IS NOT NULL")
    migrated_trans = cursor.fetchone()[0]

    print(f"   Transitions: {migrated_trans}/{total_trans} have user_id")

    # Check attachments
    cursor.execute("SELECT COUNT(*) FROM attachments")
    total_attach = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM attachments WHERE user_id IS NOT NULL")
    migrated_attach = cursor.fetchone()[0]

    print(f"   Attachments: {migrated_attach}/{total_attach} have user_id")

    # Verify 100% migration
    success = (
        migrated_workflows == total_workflows and
        migrated_items == total_items and
        migrated_trans == total_trans and
        migrated_attach == total_attach
    )

    if success:
        print("\n✅ Migration verification PASSED - All records migrated")
    else:
        print("\n❌ Migration verification FAILED - Some records missing user_id")
        sys.exit(1)


def main():
    """Run the migration"""
    print("=" * 60)
    print("🚀 Workflow Database Migration - Add user_id columns")
    print("=" * 60)
    print()

    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)

    print(f"📂 Database: {DB_PATH}")
    print()

    # Ask for confirmation
    response = input("⚠️  This will modify the database. Continue? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Migration cancelled")
        sys.exit(0)

    # Step 1: Backup
    backup_database()

    # Step 2: Get user mapping
    conn = sqlite3.connect(str(DB_PATH))
    user_mapping = get_user_id_mapping(conn)

    # Step 3: Migrate schema
    migrate_schema(conn)

    # Step 4: Migrate data
    migrate_data(conn, user_mapping)

    # Step 5: Create indexes
    create_indexes(conn)

    # Step 6: Verify
    verify_migration(conn)

    conn.close()

    print()
    print("=" * 60)
    print("✅ Migration complete!")
    print("=" * 60)
    print()
    print(f"📦 Backup saved to: {BACKUP_PATH}")
    print()
    print("Next steps:")
    print("1. Update workflow_storage.py to filter by user_id")
    print("2. Update workflow_orchestrator.py to pass user context")
    print("3. Update workflow_service.py API endpoints")
    print("4. Test user isolation")
    print()


if __name__ == "__main__":
    main()
