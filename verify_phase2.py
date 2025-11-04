#!/usr/bin/env python3
"""
Phase 2 RBAC Verification Script

Checks that all Phase 2 components are in place and functional.
"""

import sqlite3
import sys
from pathlib import Path

# Add API to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend" / "api"))

from config_paths import get_config_paths

def verify_migration():
    """Verify Phase 2 migration was applied"""
    paths = get_config_paths()
    app_db = paths.app_db

    print(f"Checking database: {app_db}")
    print(f"Database exists: {app_db.exists()}\n")

    if not app_db.exists():
        print("❌ Database not found!")
        return False

    conn = sqlite3.connect(str(app_db))
    cur = conn.cursor()

    # Check migration record
    try:
        cur.execute("SELECT migration_name, applied_at FROM migrations WHERE migration_name LIKE '%phase2%'")
        migration = cur.fetchone()
        if migration:
            print(f"✅ Migration applied: {migration[0]} at {migration[1]}")
        else:
            print("❌ Phase 2 migration not recorded in migrations table")
            return False
    except sqlite3.OperationalError as e:
        print(f"❌ Error checking migrations: {e}")
        return False

    # Check tables exist
    tables_needed = [
        'permissions',
        'permission_profiles',
        'profile_permissions',
        'permission_sets',
        'user_permission_profiles',
        'user_permission_sets'
    ]

    print("\nChecking RBAC tables:")
    for table in tables_needed:
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if cur.fetchone():
            print(f"  ✅ {table}")
        else:
            print(f"  ❌ {table} missing")
            return False

    # Check seed counts
    print("\nChecking seed data:")
    cur.execute("SELECT COUNT(*) FROM permissions")
    perm_count = cur.fetchone()[0]
    print(f"  Permissions: {perm_count} (expected: 31)")

    cur.execute("SELECT COUNT(*) FROM permission_profiles")
    profile_count = cur.fetchone()[0]
    print(f"  Profiles: {profile_count} (expected: 3)")

    cur.execute("SELECT COUNT(*) FROM profile_permissions")
    grant_count = cur.fetchone()[0]
    print(f"  Grants: {grant_count} (expected: 93)")

    conn.close()

    if perm_count >= 31 and profile_count >= 3 and grant_count >= 93:
        print("\n✅ All seed data present")
        return True
    else:
        print("\n❌ Seed data incomplete")
        return False


def verify_decorators():
    """Verify permission decorators are in place"""
    print("\n" + "="*60)
    print("Checking permission decorators in code:")
    print("="*60)

    checks = [
        ("apps/backend/api/main.py", "@require_perm(\"data.run_sql\")"),
        ("apps/backend/api/main.py", "@require_perm(\"data.export\")"),
        ("apps/backend/api/docs_service.py", "@require_perm(\"docs.update\""),
        ("apps/backend/api/workflow_service.py", "@require_perm(\"workflows.edit\""),
        ("apps/backend/api/vault_service.py", "@require_perm(\"vault.documents.create\""),
        ("apps/backend/api/admin_service.py", "@require_perm(\"system.view_admin_dashboard\")"),
    ]

    all_found = True
    for filepath, pattern in checks:
        full_path = Path(__file__).parent / filepath
        if full_path.exists():
            content = full_path.read_text()
            if pattern in content:
                print(f"  ✅ {filepath}: {pattern}")
            else:
                print(f"  ❌ {filepath}: {pattern} NOT FOUND")
                all_found = False
        else:
            print(f"  ❌ {filepath} does not exist")
            all_found = False

    return all_found


if __name__ == "__main__":
    print("="*60)
    print("PHASE 2 RBAC VERIFICATION")
    print("="*60 + "\n")

    migration_ok = verify_migration()
    decorators_ok = verify_decorators()

    print("\n" + "="*60)
    if migration_ok and decorators_ok:
        print("✅ PHASE 2 COMPLETE - All checks passed!")
    else:
        print("❌ PHASE 2 INCOMPLETE - Some checks failed")
    print("="*60)

    sys.exit(0 if (migration_ok and decorators_ok) else 1)
