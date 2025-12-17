#!/usr/bin/env python3
"""
Phase 3 Team Mode Migration

Enables full Team Mode with:
- Team membership, invites, and roles
- Team-scoped RBAC (profiles/sets per team)
- Team vault with team-level encryption
- Team-scoped Docs/Workflows
- Offline/P2P team sync support

"Two are better than one... for if they fall, one will lift up his companion" - Ecclesiastes 4:9-10
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

MIGRATION_NAME = "2025_11_10_phase3_team_mode"


def check_migration_applied(db_path: Path) -> bool:
    """Check if Phase 3 migration has already been applied"""
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        # Check migrations table
        cur.execute(
            "SELECT 1 FROM migrations WHERE migration_name = ?",
            (MIGRATION_NAME,)
        )
        result = cur.fetchone()
        conn.close()

        return result is not None
    except sqlite3.OperationalError:
        return False


def create_team_tables(conn: sqlite3.Connection) -> None:
    """Create team-related tables in app_db"""
    cursor = conn.cursor()

    logger.info("Creating teams table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (created_by) REFERENCES users(user_id)
        )
    """)

    logger.info("Creating team_members table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            team_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('super_admin','admin','member','guest')),
            job_role TEXT,
            joined_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            PRIMARY KEY (team_id, user_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)

    logger.info("Creating team_invites table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_invites (
            invite_id TEXT PRIMARY KEY,
            team_id TEXT NOT NULL,
            email_or_username TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('super_admin','admin','member','guest')),
            invited_by TEXT NOT NULL,
            invited_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','expired','cancelled')),
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
            FOREIGN KEY (invited_by) REFERENCES users(user_id)
        )
    """)

    # Indexes for performance
    logger.info("Creating team indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_invites_team ON team_invites(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_invites_email ON team_invites(email_or_username)")

    conn.commit()
    logger.info("✅ Team tables created successfully")


def add_team_id_to_vault(vault_db_path: Path) -> None:
    """Add team_id column to vault tables"""
    if not vault_db_path.exists():
        logger.warning(f"Vault DB not found at {vault_db_path}, skipping vault migration")
        return

    conn = sqlite3.connect(str(vault_db_path))
    cursor = conn.cursor()

    logger.info("Adding team_id to vault tables...")

    # Add team_id to vault_documents
    try:
        cursor.execute("ALTER TABLE vault_documents ADD COLUMN team_id TEXT")
        logger.info("  ✅ Added team_id to vault_documents")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            logger.info("  ⚠️  team_id already exists in vault_documents")
        else:
            raise

    # Add team_id to vault_files
    try:
        cursor.execute("ALTER TABLE vault_files ADD COLUMN team_id TEXT")
        logger.info("  ✅ Added team_id to vault_files")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            logger.info("  ⚠️  team_id already exists in vault_files")
        else:
            raise

    # Add team_id to vault_folders
    try:
        cursor.execute("ALTER TABLE vault_folders ADD COLUMN team_id TEXT")
        logger.info("  ✅ Added team_id to vault_folders")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            logger.info("  ⚠️  team_id already exists in vault_folders")
        else:
            raise

    # Create indexes for team-scoped queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_documents_team
        ON vault_documents(team_id, vault_type, is_deleted)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_files_team
        ON vault_files(team_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_folders_team
        ON vault_folders(team_id)
    """)

    conn.commit()
    conn.close()
    logger.info("✅ Vault team_id columns and indexes added")


def add_team_id_to_docs(docs_db_path: Path) -> None:
    """Add team_id column to docs tables"""
    if not docs_db_path.exists():
        logger.warning(f"Docs DB not found at {docs_db_path}, skipping docs migration")
        return

    conn = sqlite3.connect(str(docs_db_path))
    cursor = conn.cursor()

    logger.info("Adding team_id to docs tables...")

    # Add team_id to documents
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN team_id TEXT")
        logger.info("  ✅ Added team_id to documents")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            logger.info("  ⚠️  team_id already exists in documents")
        else:
            raise

    # Create index for team-scoped queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_team_updated
        ON documents(team_id, updated_at)
    """)

    conn.commit()
    conn.close()
    logger.info("✅ Docs team_id column and indexes added")


def add_team_id_to_workflows(workflows_db_path: Path) -> None:
    """Add team_id column to workflow tables"""
    if not workflows_db_path.exists():
        logger.warning(f"Workflows DB not found at {workflows_db_path}, skipping workflows migration")
        return

    conn = sqlite3.connect(str(workflows_db_path))
    cursor = conn.cursor()

    logger.info("Adding team_id to workflow tables...")

    # Add team_id to workflows
    try:
        cursor.execute("ALTER TABLE workflows ADD COLUMN team_id TEXT")
        logger.info("  ✅ Added team_id to workflows")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            logger.info("  ⚠️  team_id already exists in workflows")
        else:
            raise

    # Add team_id to work_items
    try:
        cursor.execute("ALTER TABLE work_items ADD COLUMN team_id TEXT")
        logger.info("  ✅ Added team_id to work_items")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            logger.info("  ⚠️  team_id already exists in work_items")
        else:
            raise

    # Add team_id to stage_transitions
    try:
        cursor.execute("ALTER TABLE stage_transitions ADD COLUMN team_id TEXT")
        logger.info("  ✅ Added team_id to stage_transitions")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            logger.info("  ⚠️  team_id already exists in stage_transitions")
        else:
            raise

    # Add team_id to attachments
    try:
        cursor.execute("ALTER TABLE attachments ADD COLUMN team_id TEXT")
        logger.info("  ✅ Added team_id to attachments")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            logger.info("  ⚠️  team_id already exists in attachments")
        else:
            raise

    # Create indexes for team-scoped queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_team ON workflows(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_items_team ON work_items(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stage_transitions_team ON stage_transitions(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attachments_team ON attachments(team_id)")

    conn.commit()
    conn.close()
    logger.info("✅ Workflows team_id columns and indexes added")


def update_rbac_for_teams(conn: sqlite3.Connection) -> None:
    """Ensure RBAC tables support team-scoped profiles/sets"""
    cursor = conn.cursor()

    logger.info("Verifying RBAC team support...")

    # Verify permission_profiles has team_id (should exist from Phase 2)
    cursor.execute("PRAGMA table_info(permission_profiles)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'team_id' not in columns:
        logger.warning("⚠️  permission_profiles missing team_id column - this should have been added in Phase 2")
        # Add it if missing
        cursor.execute("ALTER TABLE permission_profiles ADD COLUMN team_id TEXT")
        logger.info("  ✅ Added team_id to permission_profiles")

    # Verify permission_sets has team_id (should exist from Phase 2)
    cursor.execute("PRAGMA table_info(permission_sets)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'team_id' not in columns:
        logger.warning("⚠️  permission_sets missing team_id column - this should have been added in Phase 2")
        cursor.execute("ALTER TABLE permission_sets ADD COLUMN team_id TEXT")
        logger.info("  ✅ Added team_id to permission_sets")

    # Add indexes for team-scoped queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_permission_profiles_team
        ON permission_profiles(team_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_permission_sets_team
        ON permission_sets(team_id)
    """)

    conn.commit()
    logger.info("✅ RBAC team support verified")


def record_migration(conn: sqlite3.Connection) -> None:
    """Record migration in migrations table"""
    cursor = conn.cursor()
    now = datetime.now(UTC).isoformat()

    cursor.execute("""
        INSERT INTO migrations (migration_name, applied_at)
        VALUES (?, ?)
    """, (MIGRATION_NAME, now))

    conn.commit()
    logger.info(f"✅ Migration recorded: {MIGRATION_NAME} at {now}")


def migrate_phase3_team_mode(app_db: Path) -> bool:
    """
    Run Phase 3 Team Mode migration

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("=" * 60)
    logger.info("PHASE 3: TEAM MODE MIGRATION")
    logger.info("=" * 60)
    logger.info(f"App Database: {app_db}")

    if not app_db.exists():
        logger.error(f"❌ App database not found: {app_db}")
        return False

    if check_migration_applied(app_db):
        logger.info("⚠️  Phase 3 migration already applied")
        return True

    try:
        # Get paths for other databases
        from config_paths import get_config_paths
        paths = get_config_paths()

        # Main app_db connection
        conn = sqlite3.connect(str(app_db))

        # Create team tables in app_db
        create_team_tables(conn)

        # Update RBAC tables for team support
        update_rbac_for_teams(conn)

        # Record migration
        record_migration(conn)

        conn.close()

        # Add team_id to vault tables
        vault_db_path = paths.data_dir / "vault.db"
        add_team_id_to_vault(vault_db_path)

        # Add team_id to docs tables
        docs_db_path = paths.data_dir / "docs.db"
        add_team_id_to_docs(docs_db_path)

        # Add team_id to workflows tables
        workflows_db_path = paths.data_dir / "workflows.db"
        add_team_id_to_workflows(workflows_db_path)

        logger.info("=" * 60)
        logger.info("✅ PHASE 3 MIGRATION COMPLETE")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ Phase 3 migration failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # For standalone testing
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from config_paths import get_config_paths

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s - %(message)s"
    )

    paths = get_config_paths()
    success = migrate_phase3_team_mode(paths.app_db)

    sys.exit(0 if success else 1)
