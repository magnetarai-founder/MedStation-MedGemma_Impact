"""
Vault Database Schema

Defines all SQLite tables, indexes, and constraints for the vault system.
Extracted from core.py during P2 decomposition.

Tables:
- vault_documents: Encrypted document storage
- vault_files: File metadata and encrypted paths
- vault_folders: Folder hierarchy
- vault_file_tags: File tagging system
- vault_file_favorites: User favorites
- vault_file_access_logs: Access tracking for recent files
- vault_storage_stats: Cached storage statistics
- vault_file_versions: File versioning
- vault_file_comments: File comments
- vault_file_shares: Shareable links
- vault_audit_logs: Audit trail
- vault_file_metadata: Custom metadata key-value pairs
- vault_pinned_files: Quick access pins
- vault_folder_colors: Folder customization
- vault_users: User accounts
- vault_file_acl: File access control lists
- vault_folder_acl: Folder access control lists
- vault_user_roles: User role assignments
- vault_share_invitations: Sharing invitations
- vault_organization_rules: Auto-organization rules
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def init_vault_schema(db_path: Path) -> None:
    """
    Initialize all vault database tables and indexes.

    Args:
        db_path: Path to the SQLite database file
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # ===== Core Tables =====
    _create_documents_table(cursor)
    _create_files_table(cursor)
    _create_folders_table(cursor)

    # ===== Organization Tables =====
    _create_tags_table(cursor)
    _create_favorites_table(cursor)
    _create_access_logs_table(cursor)
    _create_storage_stats_table(cursor)

    # ===== Advanced Features (Day 4) =====
    _create_versions_table(cursor)
    _create_comments_table(cursor)
    _create_shares_table(cursor)
    _create_audit_logs_table(cursor)
    _create_metadata_table(cursor)
    _create_pinned_files_table(cursor)
    _create_folder_colors_table(cursor)

    # ===== Performance Indexes (Day 5) =====
    _create_performance_indexes(cursor)

    # ===== User Management & Access Control (Phase B & G) =====
    _create_users_table(cursor)
    _create_file_acl_table(cursor)
    _create_folder_acl_table(cursor)
    _create_user_roles_table(cursor)
    _create_share_invitations_table(cursor)

    # ===== Organization Rules (Phase 3) =====
    _create_organization_rules_table(cursor)

    conn.commit()
    conn.close()


def _create_documents_table(cursor: sqlite3.Cursor) -> None:
    """Create vault documents table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_documents (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            encrypted_blob TEXT NOT NULL,
            encrypted_metadata TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            UNIQUE(id, user_id, vault_type)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_user_type
        ON vault_documents(user_id, vault_type, is_deleted)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_updated
        ON vault_documents(updated_at)
    """)


def _create_files_table(cursor: sqlite3.Cursor) -> None:
    """Create vault files table for file uploads"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_files (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            filename TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            mime_type TEXT,
            encrypted_path TEXT NOT NULL,
            folder_path TEXT DEFAULT '/',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            UNIQUE(id, user_id, vault_type)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_files_user_type
        ON vault_files(user_id, vault_type, is_deleted)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_files_folder
        ON vault_files(user_id, vault_type, folder_path, is_deleted)
    """)


def _create_folders_table(cursor: sqlite3.Cursor) -> None:
    """Create vault folders table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_folders (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            folder_name TEXT NOT NULL,
            folder_path TEXT NOT NULL,
            parent_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            UNIQUE(user_id, vault_type, folder_path)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_folders_user_type
        ON vault_folders(user_id, vault_type, is_deleted)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_folders_parent
        ON vault_folders(user_id, vault_type, parent_path, is_deleted)
    """)


def _create_tags_table(cursor: sqlite3.Cursor) -> None:
    """Create file tags table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_file_tags (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            tag_name TEXT NOT NULL,
            tag_color TEXT DEFAULT '#3B82F6',
            created_at TEXT NOT NULL,
            FOREIGN KEY(file_id) REFERENCES vault_files(id),
            UNIQUE(file_id, user_id, vault_type, tag_name)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_tags_file
        ON vault_file_tags(file_id, user_id, vault_type)
    """)


def _create_favorites_table(cursor: sqlite3.Cursor) -> None:
    """Create file favorites table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_file_favorites (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            created_at TEXT NOT NULL,
            FOREIGN KEY(file_id) REFERENCES vault_files(id),
            UNIQUE(file_id, user_id, vault_type)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_favorites_user
        ON vault_file_favorites(user_id, vault_type)
    """)


def _create_access_logs_table(cursor: sqlite3.Cursor) -> None:
    """Create file access logs table for recent files tracking"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_file_access_logs (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            access_type TEXT NOT NULL CHECK(access_type IN ('view', 'download', 'preview')),
            accessed_at TEXT NOT NULL,
            FOREIGN KEY(file_id) REFERENCES vault_files(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_access_logs
        ON vault_file_access_logs(user_id, vault_type, accessed_at)
    """)


def _create_storage_stats_table(cursor: sqlite3.Cursor) -> None:
    """Create storage statistics cache table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_storage_stats (
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            total_files INTEGER NOT NULL,
            total_size_bytes INTEGER NOT NULL,
            last_updated TEXT NOT NULL,
            PRIMARY KEY(user_id, vault_type)
        )
    """)


def _create_versions_table(cursor: sqlite3.Cursor) -> None:
    """Create file versions table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_file_versions (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            version_number INTEGER NOT NULL,
            encrypted_path TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            mime_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            comment TEXT,
            FOREIGN KEY(file_id) REFERENCES vault_files(id),
            UNIQUE(file_id, version_number)
        )
    """)


def _create_comments_table(cursor: sqlite3.Cursor) -> None:
    """Create file comments table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_file_comments (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            comment_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY(file_id) REFERENCES vault_files(id)
        )
    """)


def _create_shares_table(cursor: sqlite3.Cursor) -> None:
    """Create file shares/links table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_file_shares (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            share_token TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            expires_at TEXT,
            max_downloads INTEGER,
            download_count INTEGER DEFAULT 0,
            permissions TEXT NOT NULL CHECK(permissions IN ('view', 'download')),
            created_at TEXT NOT NULL,
            last_accessed TEXT,
            FOREIGN KEY(file_id) REFERENCES vault_files(id)
        )
    """)


def _create_audit_logs_table(cursor: sqlite3.Cursor) -> None:
    """Create audit logs table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_audit_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL
        )
    """)


def _create_metadata_table(cursor: sqlite3.Cursor) -> None:
    """Create file metadata table for custom fields"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_file_metadata (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY(file_id) REFERENCES vault_files(id),
            UNIQUE(file_id, user_id, vault_type, key)
        )
    """)


def _create_pinned_files_table(cursor: sqlite3.Cursor) -> None:
    """Create pinned files table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_pinned_files (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            pin_order INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(file_id) REFERENCES vault_files(id),
            UNIQUE(file_id, user_id, vault_type)
        )
    """)


def _create_folder_colors_table(cursor: sqlite3.Cursor) -> None:
    """Create folder colors table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_folder_colors (
            id TEXT PRIMARY KEY,
            folder_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL CHECK(vault_type IN ('real', 'decoy')),
            color TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(folder_id) REFERENCES vault_folders(id),
            UNIQUE(folder_id, user_id, vault_type)
        )
    """)


def _create_performance_indexes(cursor: sqlite3.Cursor) -> None:
    """Create additional performance indexes"""
    # Indexes for vault_files
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_files_created
        ON vault_files(created_at)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_files_mime
        ON vault_files(mime_type)
    """)

    # Indexes for vault_file_tags
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_tags_name
        ON vault_file_tags(tag_name)
    """)

    # Indexes for vault_file_shares
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_shares_token
        ON vault_file_shares(share_token)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_shares_file
        ON vault_file_shares(file_id)
    """)

    # Indexes for vault_audit_logs
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_audit_created
        ON vault_audit_logs(created_at)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_audit_action
        ON vault_audit_logs(action)
    """)

    # Indexes for vault_file_versions
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_versions_file
        ON vault_file_versions(file_id, version_number)
    """)

    # Indexes for vault_file_comments
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_comments_file
        ON vault_file_comments(file_id, created_at)
    """)

    # Indexes for vault_file_metadata
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_metadata_file
        ON vault_file_metadata(file_id, key)
    """)

    # Indexes for vault_pinned_files
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_pinned_user
        ON vault_pinned_files(user_id, vault_type, pin_order)
    """)


def _create_users_table(cursor: sqlite3.Cursor) -> None:
    """Create users table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            last_login TEXT
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_users_email
        ON vault_users(email)
    """)


def _create_file_acl_table(cursor: sqlite3.Cursor) -> None:
    """Create file access control lists table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_file_acl (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            permission TEXT NOT NULL CHECK(permission IN ('read', 'write', 'delete', 'share')),
            granted_by TEXT NOT NULL,
            granted_at TEXT NOT NULL,
            expires_at TEXT,
            FOREIGN KEY(file_id) REFERENCES vault_files(id),
            FOREIGN KEY(user_id) REFERENCES vault_users(user_id),
            FOREIGN KEY(granted_by) REFERENCES vault_users(user_id),
            UNIQUE(file_id, user_id, permission)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_acl_file
        ON vault_file_acl(file_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_acl_user
        ON vault_file_acl(user_id)
    """)


def _create_folder_acl_table(cursor: sqlite3.Cursor) -> None:
    """Create folder access control lists table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_folder_acl (
            id TEXT PRIMARY KEY,
            folder_path TEXT NOT NULL,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL,
            permission TEXT NOT NULL CHECK(permission IN ('read', 'write', 'delete', 'share')),
            granted_by TEXT NOT NULL,
            granted_at TEXT NOT NULL,
            expires_at TEXT,
            FOREIGN KEY(user_id) REFERENCES vault_users(user_id),
            FOREIGN KEY(granted_by) REFERENCES vault_users(user_id),
            UNIQUE(folder_path, user_id, vault_type, permission)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_folder_acl_path
        ON vault_folder_acl(folder_path, vault_type)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_folder_acl_user
        ON vault_folder_acl(user_id)
    """)


def _create_user_roles_table(cursor: sqlite3.Cursor) -> None:
    """Create user roles table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_user_roles (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('owner', 'admin', 'editor', 'viewer')),
            granted_by TEXT NOT NULL,
            granted_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES vault_users(user_id),
            FOREIGN KEY(granted_by) REFERENCES vault_users(user_id),
            UNIQUE(user_id, vault_type)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_roles_user
        ON vault_user_roles(user_id, vault_type)
    """)


def _create_share_invitations_table(cursor: sqlite3.Cursor) -> None:
    """Create sharing invitations table"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_share_invitations (
            id TEXT PRIMARY KEY,
            resource_type TEXT NOT NULL CHECK(resource_type IN ('file', 'folder')),
            resource_id TEXT NOT NULL,
            from_user_id TEXT NOT NULL,
            to_user_email TEXT NOT NULL,
            permission TEXT NOT NULL,
            invitation_token TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'declined', 'expired')),
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            accepted_at TEXT,
            FOREIGN KEY(from_user_id) REFERENCES vault_users(user_id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_invitations_email
        ON vault_share_invitations(to_user_email, status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_invitations_token
        ON vault_share_invitations(invitation_token)
    """)


def _create_organization_rules_table(cursor: sqlite3.Cursor) -> None:
    """Create organization rules table for auto-filing"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_organization_rules (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            vault_type TEXT NOT NULL,
            rule_name TEXT NOT NULL,
            rule_type TEXT NOT NULL CHECK(rule_type IN ('mime_type', 'file_extension', 'file_size', 'filename_pattern', 'date')),
            condition_value TEXT NOT NULL,
            action_type TEXT NOT NULL CHECK(action_type IN ('move_to_folder', 'add_tag', 'set_color')),
            action_value TEXT NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            last_run TEXT,
            files_processed INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES vault_users(user_id),
            UNIQUE(user_id, vault_type, rule_name)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vault_rules_user
        ON vault_organization_rules(user_id, vault_type, is_enabled)
    """)


__all__ = ["init_vault_schema"]
