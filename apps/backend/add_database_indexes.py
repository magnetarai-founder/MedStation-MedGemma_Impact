#!/usr/bin/env python3
"""
Add Database Indexes - Performance Foundation

This script analyzes and adds missing indexes to all MedStation databases.
Focus on:
1. Foreign keys (for JOINs)
2. Frequently filtered columns (user_id, team_id, session_id)
3. Timestamp columns (for sorting)
4. Composite indexes for common query patterns

Run this script to optimize database query performance.
"""

import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from api.config_paths import get_config_paths

PATHS = get_config_paths()


def get_existing_indexes(conn: sqlite3.Connection, table: str) -> List[str]:
    """Get list of existing indexes for a table."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{table}'")
    return [row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')]


def add_index_if_missing(conn: sqlite3.Connection, table: str, index_name: str, columns: str, description: str = ""):
    """Add index if it doesn't already exist."""
    existing = get_existing_indexes(conn, table)

    if index_name in existing:
        print(f"   ✓ Index {index_name} already exists")
        return False

    try:
        sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({columns})"
        conn.execute(sql)
        desc_str = f" ({description})" if description else ""
        print(f"   ✅ Created index {index_name} on {table}({columns}){desc_str}")
        return True
    except Exception as e:
        print(f"   ❌ Failed to create {index_name}: {e}")
        return False


def optimize_chat_memory_db():
    """Add indexes to chat_memory.db"""
    print("\n📊 Optimizing chat_memory.db...")

    db_path = PATHS.data_dir / "memory" / "chat_memory.db"
    if not db_path.exists():
        print(f"   ⚠️  Database not found: {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    added = 0

    # chat_sessions indexes
    added += add_index_if_missing(conn, "chat_sessions", "idx_sessions_user_id", "user_id", "user lookup")
    added += add_index_if_missing(conn, "chat_sessions", "idx_sessions_team_id", "team_id", "team filtering")
    added += add_index_if_missing(conn, "chat_sessions", "idx_sessions_updated", "updated_at DESC", "recent sessions")
    added += add_index_if_missing(conn, "chat_sessions", "idx_sessions_created", "created_at DESC", "session history")

    # chat_messages indexes
    added += add_index_if_missing(conn, "chat_messages", "idx_messages_user_id", "user_id", "user messages")
    added += add_index_if_missing(conn, "chat_messages", "idx_messages_team_id", "team_id", "team messages")
    added += add_index_if_missing(conn, "chat_messages", "idx_messages_role", "role", "filter by role")
    added += add_index_if_missing(conn, "chat_messages", "idx_messages_session_time", "session_id, timestamp", "session messages chronological")

    # message_embeddings indexes
    added += add_index_if_missing(conn, "message_embeddings", "idx_embeddings_message_id", "message_id", "message lookup")
    added += add_index_if_missing(conn, "chat_messages", "idx_messages_id", "id", "embedding FK lookup")
    added += add_index_if_missing(conn, "message_embeddings", "idx_embeddings_team_id", "team_id", "team filtering")

    # document_chunks indexes
    added += add_index_if_missing(conn, "document_chunks", "idx_chunks_user_id", "user_id", "user documents")
    added += add_index_if_missing(conn, "document_chunks", "idx_chunks_team_id", "team_id", "team documents")

    # conversation_summaries indexes
    added += add_index_if_missing(conn, "conversation_summaries", "idx_summaries_user_id", "user_id", "user summaries")
    added += add_index_if_missing(conn, "conversation_summaries", "idx_summaries_team_id", "team_id", "team summaries")

    conn.commit()
    conn.close()

    print(f"   📈 Added {added} new indexes to chat_memory.db")


def optimize_teams_db():
    """Add indexes to teams.db"""
    print("\n📊 Optimizing teams.db...")

    db_path = PATHS.data_dir / "teams.db"
    if not db_path.exists():
        print(f"   ⚠️  Database not found: {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    added = 0

    # team_members indexes
    added += add_index_if_missing(conn, "team_members", "idx_members_team_id", "team_id", "team lookup")
    added += add_index_if_missing(conn, "team_members", "idx_members_user_id", "user_id", "user teams")
    added += add_index_if_missing(conn, "team_members", "idx_members_role", "role", "filter by role")
    added += add_index_if_missing(conn, "team_members", "idx_members_job_role", "job_role", "filter by job")
    added += add_index_if_missing(conn, "team_members", "idx_members_joined", "joined_at DESC", "recent joins")
    added += add_index_if_missing(conn, "team_members", "idx_members_last_seen", "last_seen DESC", "active members")

    # team_vault_items indexes
    added += add_index_if_missing(conn, "team_vault_items", "idx_vault_team_id", "team_id", "team vault")
    added += add_index_if_missing(conn, "team_vault_items", "idx_vault_item_id", "item_id", "item lookup")
    added += add_index_if_missing(conn, "team_vault_items", "idx_vault_type", "item_type", "filter by type")
    added += add_index_if_missing(conn, "team_vault_items", "idx_vault_created_by", "created_by", "creator lookup")
    added += add_index_if_missing(conn, "team_vault_items", "idx_vault_created_at", "created_at DESC", "recent items")
    added += add_index_if_missing(conn, "team_vault_items", "idx_vault_is_deleted", "is_deleted", "active items")
    added += add_index_if_missing(conn, "team_vault_items", "idx_vault_team_type_deleted", "team_id, item_type, is_deleted", "filtered listing")

    # team_vault_permissions indexes
    added += add_index_if_missing(conn, "team_vault_permissions", "idx_vault_perms_item", "item_id", "item permissions")
    added += add_index_if_missing(conn, "team_vault_permissions", "idx_vault_perms_team", "team_id", "team permissions")
    added += add_index_if_missing(conn, "team_vault_permissions", "idx_vault_perms_grant_value", "grant_value", "user/role lookup")

    # invite_codes indexes
    added += add_index_if_missing(conn, "invite_codes", "idx_invites_team", "team_id", "team invites")
    added += add_index_if_missing(conn, "invite_codes", "idx_invites_created_by", "created_by", "creator lookup")
    added += add_index_if_missing(conn, "invite_codes", "idx_invites_expires", "expires_at", "expiration check")

    # workflow_permissions indexes (if table exists)
    try:
        conn.execute("SELECT 1 FROM workflow_permissions LIMIT 1")
        added += add_index_if_missing(conn, "workflow_permissions", "idx_workflow_perms_team", "team_id", "team workflows")
        added += add_index_if_missing(conn, "workflow_permissions", "idx_workflow_perms_template", "template_id", "template lookup")
    except sqlite3.OperationalError:
        pass  # Table doesn't exist

    # queues indexes
    try:
        conn.execute("SELECT 1 FROM queues LIMIT 1")
        added += add_index_if_missing(conn, "queues", "idx_queues_team", "team_id", "team queues")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

    print(f"   📈 Added {added} new indexes to teams.db")


def optimize_app_db():
    """Add indexes to medstationos_app.db (users, sessions, permissions)"""
    print("\n📊 Optimizing medstationos_app.db...")

    db_path = PATHS.app_db
    if not db_path.exists():
        print(f"   ⚠️  Database not found: {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    added = 0

    # users table indexes
    added += add_index_if_missing(conn, "users", "idx_users_email", "email", "email lookup")
    added += add_index_if_missing(conn, "users", "idx_users_username", "username", "username lookup")
    added += add_index_if_missing(conn, "users", "idx_users_role", "role", "filter by role")
    added += add_index_if_missing(conn, "users", "idx_users_job_role", "job_role", "filter by job")

    # sessions indexes - already exist from previous work

    # user_profiles table (if exists)
    try:
        conn.execute("SELECT 1 FROM user_profiles LIMIT 1")
        added += add_index_if_missing(conn, "user_profiles", "idx_profiles_user_id", "user_id", "user lookup")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

    print(f"   📈 Added {added} new indexes to medstationos_app.db")


def analyze_index_impact():
    """Analyze which tables will benefit most from indexing."""
    print("\n📊 Index Impact Analysis:")
    print("=" * 70)

    # Chat memory
    db_path = PATHS.data_dir / "memory" / "chat_memory.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM chat_messages")
        msg_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM message_embeddings")
        embed_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chat_sessions")
        session_count = cursor.fetchone()[0]

        print(f"\n💬 chat_memory.db:")
        print(f"   • {session_count:,} chat sessions")
        print(f"   • {msg_count:,} messages")
        print(f"   • {embed_count:,} embeddings")

        if msg_count > 1000:
            print(f"   🎯 HIGH IMPACT: Indexes will significantly improve query performance")
        elif msg_count > 100:
            print(f"   ⚡ MEDIUM IMPACT: Noticeable performance improvement expected")
        else:
            print(f"   ✓ LOW IMPACT: Small dataset, but good for future growth")

        conn.close()

    # Teams
    db_path = PATHS.data_dir / "teams.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM teams")
            team_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM team_members")
            member_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM team_vault_items")
            vault_count = cursor.fetchone()[0]

            print(f"\n👥 teams.db:")
            print(f"   • {team_count:,} teams")
            print(f"   • {member_count:,} team members")
            print(f"   • {vault_count:,} vault items")

            if vault_count > 100 or member_count > 50:
                print(f"   🎯 HIGH IMPACT: Vault and member queries will be much faster")
            else:
                print(f"   ✓ GOOD FOUNDATION: Indexes ready for scale")
        except sqlite3.Error:
            print(f"\n👥 teams.db: Schema exists, ready for indexing")

        conn.close()


def main():
    """Main execution."""
    print("=" * 70)
    print("🔧 DATABASE INDEX OPTIMIZATION")
    print("=" * 70)
    print("\nAdding missing indexes for optimal query performance...")
    print("Focus: Foreign keys, filters, timestamps, composite patterns")

    # Analyze current state
    analyze_index_impact()

    print("\n" + "=" * 70)
    print("ADDING INDEXES")
    print("=" * 70)

    # Add indexes to each database
    optimize_chat_memory_db()
    optimize_teams_db()
    optimize_app_db()

    print("\n" + "=" * 70)
    print("✅ INDEX OPTIMIZATION COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Run your app and monitor query performance")
    print("  2. Use EXPLAIN QUERY PLAN to verify index usage")
    print("  3. Monitor cache hit rates with /api/cache/stats")
    print("\nExpected improvements:")
    print("  • JOIN queries: 10-100x faster")
    print("  • Filtered queries: 5-50x faster")
    print("  • Sorted queries: 2-10x faster")
    print("\n")


if __name__ == "__main__":
    main()
