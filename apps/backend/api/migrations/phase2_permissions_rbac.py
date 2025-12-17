"""
Phase 2 Migration: Salesforce-style RBAC Permission System

This migration:
1. Creates RBAC schema tables (permissions, profiles, permission_sets, assignments)
2. Seeds permission registry with feature, resource, and system permissions
3. Creates base permission profiles (Admin, Member, Guest)
4. Creates indexes for performance
5. Records completion in migrations table

Non-interactive and idempotent - safe to run multiple times.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
import json

logger = logging.getLogger(__name__)

MIGRATION_NAME = "2025_11_04_phase2_permissions_rbac"


def check_migration_applied(app_db_path: Path) -> bool:
    """
    Check if Phase 2 migration has already been applied

    Args:
        app_db_path: Path to app database

    Returns:
        True if migration already applied
    """
    try:
        conn = sqlite3.connect(str(app_db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM migrations
            WHERE migration_name = ?
        """, (MIGRATION_NAME,))

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0
    except Exception as e:
        logger.warning(f"Could not check migration status: {e}")
        return False


def create_rbac_schema(conn: sqlite3.Connection) -> None:
    """
    Create RBAC schema tables

    Tables:
    - permissions: Permission registry (feature, resource, system)
    - permission_profiles: Reusable role-based permission bundles
    - profile_permissions: Join table (profile -> permissions)
    - permission_sets: Ad-hoc permission grants
    - user_permission_profiles: User -> profile assignments
    - user_permission_sets: User -> permission set assignments
    """
    cursor = conn.cursor()

    logger.info("  Creating RBAC schema tables...")

    # Table 1: permissions (registry)
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
    logger.info("    ✓ permissions table")

    # Table 2: permission_profiles
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
    logger.info("    ✓ permission_profiles table")

    # Table 3: profile_permissions (join)
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
    logger.info("    ✓ profile_permissions table")

    # Table 4: permission_sets
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
    logger.info("    ✓ permission_sets table")

    # Table 5: user_permission_profiles (user -> profile)
    # NOTE: Named differently from user_profiles to avoid conflict with existing table
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
    logger.info("    ✓ user_permission_profiles table")

    # Table 6: user_permission_sets (user -> permission set)
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
    logger.info("    ✓ user_permission_sets table")

    conn.commit()


def create_indexes(conn: sqlite3.Connection) -> None:
    """Create performance indexes"""
    cursor = conn.cursor()

    logger.info("  Creating indexes...")

    indexes = [
        ("idx_permissions_key", "permissions", "permission_key"),
        ("idx_permissions_category", "permissions", "category"),
        ("idx_profiles_role", "permission_profiles", "applies_to_role"),
        ("idx_profiles_active", "permission_profiles", "is_active"),
        ("idx_user_profiles_user", "user_permission_profiles", "user_id"),
        ("idx_user_profiles_profile", "user_permission_profiles", "profile_id"),
        ("idx_user_sets_user", "user_permission_sets", "user_id"),
        ("idx_user_sets_set", "user_permission_sets", "permission_set_id"),
    ]

    for index_name, table_name, column_name in indexes:
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table_name}({column_name})
        """)
        logger.info(f"    ✓ {index_name}")

    conn.commit()


def seed_permissions(conn: sqlite3.Connection) -> None:
    """
    Seed permission registry

    Categories:
    - feature: High-level feature access (chat, vault, workflows, etc.)
    - resource: CRUD operations on specific resources
    - system: Administrative and system-level operations
    """
    cursor = conn.cursor()

    logger.info("  Seeding permission registry...")

    now = datetime.now(UTC).isoformat()

    permissions = []

    # ===== FEATURE PERMISSIONS (boolean) =====
    feature_perms = [
        ("chat.use", "Use Chat", "Access to AI chat feature"),
        ("vault.use", "Use Vault", "Access to personal vault feature"),
        ("workflows.use", "Use Workflows", "Access to workflow automation feature"),
        ("docs.use", "Use Docs", "Access to document management"),
        ("data.run_sql", "Run SQL Queries", "Execute SQL queries against data"),
        ("data.export", "Export Data", "Export data to files"),
        ("insights.use", "Use Insights", "Access to analytics and insights"),
        ("code.use", "Use Code Editor", "Access to code editing features"),
        ("team.use", "Use Team Features", "Access to team collaboration features"),
        ("panic.use", "Trigger Panic Mode", "Ability to trigger panic mode"),
        ("backups.use", "Use Backups", "Access to backup and restore features"),
    ]

    for key, name, desc in feature_perms:
        perm_id = f"perm_{key.replace('.', '_')}"
        permissions.append((
            perm_id, key, name, desc, "feature", None, "boolean", 0, now
        ))

    # ===== VAULT RESOURCE PERMISSIONS (level-based) =====
    vault_resource_perms = [
        ("vault.documents.create", "Create Vault Documents", "Create new documents in vault"),
        ("vault.documents.read", "Read Vault Documents", "Read documents from vault"),
        ("vault.documents.update", "Update Vault Documents", "Modify existing vault documents"),
        ("vault.documents.delete", "Delete Vault Documents", "Delete documents from vault"),
        ("vault.documents.share", "Share Vault Documents", "Share vault documents with others"),
    ]

    for key, name, desc in vault_resource_perms:
        perm_id = f"perm_{key.replace('.', '_')}"
        permissions.append((
            perm_id, key, name, desc, "resource", "vault", "level", 0, now
        ))

    # ===== WORKFLOW RESOURCE PERMISSIONS (level-based) =====
    workflow_resource_perms = [
        ("workflows.create", "Create Workflows", "Create new workflow definitions"),
        ("workflows.view", "View Workflows", "View workflow definitions and instances"),
        ("workflows.edit", "Edit Workflows", "Modify workflow definitions"),
        ("workflows.delete", "Delete Workflows", "Delete workflow definitions"),
        ("workflows.manage", "Manage Workflows", "Advanced workflow management (triggers, approvals)"),
    ]

    for key, name, desc in workflow_resource_perms:
        perm_id = f"perm_{key.replace('.', '_')}"
        permissions.append((
            perm_id, key, name, desc, "resource", "workflows", "level", 0, now
        ))

    # ===== DOCS RESOURCE PERMISSIONS (level-based) =====
    docs_resource_perms = [
        ("docs.create", "Create Documents", "Create new documents"),
        ("docs.read", "Read Documents", "Read documents"),
        ("docs.update", "Update Documents", "Modify existing documents"),
        ("docs.delete", "Delete Documents", "Delete documents"),
        ("docs.share", "Share Documents", "Share documents with others"),
    ]

    for key, name, desc in docs_resource_perms:
        perm_id = f"perm_{key.replace('.', '_')}"
        permissions.append((
            perm_id, key, name, desc, "resource", "docs", "level", 0, now
        ))

    # ===== SYSTEM PERMISSIONS (boolean, is_system=1) =====
    system_perms = [
        ("system.view_admin_dashboard", "View Admin Dashboard", "Access to admin dashboard and metrics"),
        ("system.manage_users", "Manage Users", "Create, edit, delete users"),
        ("system.view_audit_logs", "View Audit Logs", "Access to system audit logs"),
        ("system.manage_permissions", "Manage Permissions", "Manage permission profiles and assignments"),
        ("system.manage_settings", "Manage System Settings", "Modify system configuration"),
    ]

    for key, name, desc in system_perms:
        perm_id = f"perm_{key.replace('.', '_')}"
        permissions.append((
            perm_id, key, name, desc, "system", None, "boolean", 1, now
        ))

    # Insert all permissions
    cursor.executemany("""
        INSERT OR IGNORE INTO permissions (
            permission_id, permission_key, permission_name, permission_description,
            category, subcategory, permission_type, is_system, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, permissions)

    logger.info(f"    ✓ Seeded {len(permissions)} permissions")
    conn.commit()


def seed_base_profiles(conn: sqlite3.Connection) -> None:
    """
    Seed base permission profiles

    Profiles:
    1. Admin Profile (applies_to_role='admin')
    2. Member Profile (applies_to_role='member')
    3. Guest Profile (applies_to_role='guest')
    """
    cursor = conn.cursor()

    logger.info("  Seeding base permission profiles...")

    now = datetime.now(UTC).isoformat()

    # Profile 1: Admin Profile
    cursor.execute("""
        INSERT OR IGNORE INTO permission_profiles (
            profile_id, profile_name, profile_description, team_id,
            applies_to_role, created_by, created_at, modified_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "profile_admin_base",
        "Admin Profile",
        "Default permissions for Admin role users",
        None,
        "admin",
        "system",
        now,
        now,
        1
    ))

    # Profile 2: Member Profile
    cursor.execute("""
        INSERT OR IGNORE INTO permission_profiles (
            profile_id, profile_name, profile_description, team_id,
            applies_to_role, created_by, created_at, modified_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "profile_member_base",
        "Member Profile",
        "Default permissions for Member role users",
        None,
        "member",
        "system",
        now,
        now,
        1
    ))

    # Profile 3: Guest Profile
    cursor.execute("""
        INSERT OR IGNORE INTO permission_profiles (
            profile_id, profile_name, profile_description, team_id,
            applies_to_role, created_by, created_at, modified_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "profile_guest_base",
        "Guest Profile",
        "Default permissions for Guest role users",
        None,
        "guest",
        "system",
        now,
        now,
        1
    ))

    logger.info("    ✓ Created 3 base profiles")
    conn.commit()


def seed_profile_permissions(conn: sqlite3.Connection) -> None:
    """
    Attach permissions to base profiles

    Admin Profile:
    - All feature permissions
    - Resource permissions: write level
    - System permissions: limited (no manage_permissions by default)

    Member Profile:
    - Core features: chat, vault, workflows, docs
    - Resource permissions: write level
    - No data.export, no system permissions

    Guest Profile:
    - Limited features: chat, docs (read-only)
    - Resource permissions: read level only
    - No system permissions
    """
    cursor = conn.cursor()

    logger.info("  Attaching permissions to profiles...")

    grants = []

    # ===== ADMIN PROFILE GRANTS =====
    admin_feature_grants = [
        "chat.use", "vault.use", "workflows.use", "docs.use",
        "data.run_sql", "data.export", "insights.use", "code.use",
        "team.use", "panic.use", "backups.use"
    ]

    for perm_key in admin_feature_grants:
        perm_id = f"perm_{perm_key.replace('.', '_')}"
        grants.append(("profile_admin_base", perm_id, 1, None, None))

    # Admin resource grants (write level)
    admin_resource_grants = [
        ("vault.documents.create", "write"),
        ("vault.documents.read", "write"),
        ("vault.documents.update", "write"),
        ("vault.documents.delete", "write"),
        ("vault.documents.share", "read"),
        ("workflows.create", "write"),
        ("workflows.view", "write"),
        ("workflows.edit", "write"),
        ("workflows.delete", "write"),
        ("workflows.manage", "read"),
        ("docs.create", "write"),
        ("docs.read", "write"),
        ("docs.update", "write"),
        ("docs.delete", "write"),
        ("docs.share", "read"),
    ]

    for perm_key, level in admin_resource_grants:
        perm_id = f"perm_{perm_key.replace('.', '_')}"
        grants.append(("profile_admin_base", perm_id, 1, level, None))

    # Admin system grants (limited)
    admin_system_grants = [
        "system.view_admin_dashboard",
        "system.manage_users",
        "system.view_audit_logs",
        "system.manage_settings",
    ]

    for perm_key in admin_system_grants:
        perm_id = f"perm_{perm_key.replace('.', '_')}"
        grants.append(("profile_admin_base", perm_id, 1, None, None))

    # Explicitly deny manage_permissions for admin (only super_admin/founder can do this)
    grants.append(("profile_admin_base", "perm_system_manage_permissions", 0, None, None))

    # ===== MEMBER PROFILE GRANTS =====
    member_feature_grants = [
        "chat.use", "vault.use", "workflows.use", "docs.use", "data.run_sql"
    ]

    for perm_key in member_feature_grants:
        perm_id = f"perm_{perm_key.replace('.', '_')}"
        grants.append(("profile_member_base", perm_id, 1, None, None))

    # Member resource grants (write level on own resources)
    member_resource_grants = [
        ("vault.documents.create", "write"),
        ("vault.documents.read", "write"),
        ("vault.documents.update", "write"),
        ("vault.documents.delete", "write"),
        ("vault.documents.share", "none"),
        ("workflows.create", "write"),
        ("workflows.view", "write"),
        ("workflows.edit", "write"),
        ("workflows.delete", "read"),  # Own only
        ("workflows.manage", "none"),
        ("docs.create", "write"),
        ("docs.read", "write"),
        ("docs.update", "write"),
        ("docs.delete", "write"),
        ("docs.share", "none"),
    ]

    for perm_key, level in member_resource_grants:
        perm_id = f"perm_{perm_key.replace('.', '_')}"
        grants.append(("profile_member_base", perm_id, 1, level, None))

    # Member: explicitly deny data.export and all system perms
    member_denies = [
        "data.export", "insights.use", "code.use", "team.use", "panic.use", "backups.use",
        "system.view_admin_dashboard", "system.manage_users", "system.view_audit_logs",
        "system.manage_permissions", "system.manage_settings"
    ]

    for perm_key in member_denies:
        perm_id = f"perm_{perm_key.replace('.', '_')}"
        grants.append(("profile_member_base", perm_id, 0, None, None))

    # ===== GUEST PROFILE GRANTS =====
    guest_feature_grants = [
        "chat.use", "docs.use"
    ]

    for perm_key in guest_feature_grants:
        perm_id = f"perm_{perm_key.replace('.', '_')}"
        grants.append(("profile_guest_base", perm_id, 1, None, None))

    # Guest resource grants (read-only)
    guest_resource_grants = [
        ("vault.documents.create", "none"),
        ("vault.documents.read", "read"),
        ("vault.documents.update", "none"),
        ("vault.documents.delete", "none"),
        ("vault.documents.share", "none"),
        ("workflows.create", "none"),
        ("workflows.view", "read"),
        ("workflows.edit", "none"),
        ("workflows.delete", "none"),
        ("workflows.manage", "none"),
        ("docs.create", "none"),
        ("docs.read", "read"),
        ("docs.update", "none"),
        ("docs.delete", "none"),
        ("docs.share", "none"),
    ]

    for perm_key, level in guest_resource_grants:
        perm_id = f"perm_{perm_key.replace('.', '_')}"
        grants.append(("profile_guest_base", perm_id, 1, level, None))

    # Guest: deny everything else
    guest_denies = [
        "vault.use", "workflows.use", "data.run_sql", "data.export",
        "insights.use", "code.use", "team.use", "panic.use", "backups.use",
        "system.view_admin_dashboard", "system.manage_users", "system.view_audit_logs",
        "system.manage_permissions", "system.manage_settings"
    ]

    for perm_key in guest_denies:
        perm_id = f"perm_{perm_key.replace('.', '_')}"
        grants.append(("profile_guest_base", perm_id, 0, None, None))

    # Insert all grants
    cursor.executemany("""
        INSERT OR IGNORE INTO profile_permissions (
            profile_id, permission_id, is_granted, permission_level, permission_scope
        ) VALUES (?, ?, ?, ?, ?)
    """, grants)

    logger.info(f"    ✓ Attached {len(grants)} permission grants to profiles")
    conn.commit()


def record_migration(conn: sqlite3.Connection) -> None:
    """Record migration completion in migrations table"""
    cursor = conn.cursor()

    now = datetime.now(UTC).isoformat()

    cursor.execute("""
        INSERT OR IGNORE INTO migrations (migration_name, applied_at)
        VALUES (?, ?)
    """, (MIGRATION_NAME, now))

    conn.commit()
    logger.info(f"  ✓ Recorded migration: {MIGRATION_NAME}")


def migrate_phase2_permissions_rbac(app_db_path: Path) -> bool:
    """
    Main Phase 2 migration function

    Creates RBAC schema, seeds permissions and profiles.

    Args:
        app_db_path: Path to app database (elohimos_app.db)

    Returns:
        True if migration succeeded, False otherwise
    """
    logger.info("=" * 60)
    logger.info("Phase 2 Migration: Salesforce-style RBAC")
    logger.info("=" * 60)

    try:
        # Connect to app_db
        conn = sqlite3.connect(str(app_db_path))
        conn.row_factory = sqlite3.Row

        # Step 1: Create schema
        create_rbac_schema(conn)

        # Step 2: Create indexes
        create_indexes(conn)

        # Step 3: Seed permissions
        seed_permissions(conn)

        # Step 4: Seed base profiles
        seed_base_profiles(conn)

        # Step 5: Attach permissions to profiles
        seed_profile_permissions(conn)

        # Step 6: Record migration
        record_migration(conn)

        conn.close()

        logger.info("=" * 60)
        logger.info("✅ Phase 2 migration completed successfully")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ Phase 2 migration failed: {e}", exc_info=True)
        return False


# For standalone testing
if __name__ == "__main__":
    import sys
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # Get app_db path
    try:
        from config_paths import get_config_paths
        paths = get_config_paths()
        app_db = paths.app_db
    except Exception:
        app_db = Path(__file__).parent.parent.parent.parent / ".neutron_data" / "elohimos_app.db"

    print(f"\nUsing app_db: {app_db}\n")

    if check_migration_applied(app_db):
        print("⚠️  Phase 2 migration already applied")
        sys.exit(0)

    success = migrate_phase2_permissions_rbac(app_db)
    sys.exit(0 if success else 1)
