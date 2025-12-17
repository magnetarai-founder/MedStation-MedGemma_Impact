"""
Vault Service Core Logic

Handles all vault operations including documents, files, folders,
tags, favorites, versioning, trash, search, sharing, ACL, and automation.

Security model:
- All encryption happens client-side using Web Crypto API
- Server only stores encrypted blobs (cannot read contents)
- Real and decoy vaults are stored separately
- No server-side password verification (zero-knowledge)
"""

import sqlite3
import logging
import base64
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from cryptography.fernet import Fernet

from api.config_paths import get_config_paths
from .schemas import (
    VaultDocument,
    VaultDocumentCreate,
    VaultDocumentUpdate,
    VaultListResponse,
    VaultFile,
    VaultFolder,
)
from . import storage
from . import encryption
from . import documents as documents_mod
from . import files as files_mod
from . import folders as folders_mod
from . import search as search_mod
from . import automation as automation_mod
from . import tags as tags_mod
from . import favorites as favorites_mod
from . import analytics as analytics_mod
from . import audit as audit_mod
from . import sharing as sharing_mod

logger = logging.getLogger(__name__)

# Configuration paths
PATHS = get_config_paths()
VAULT_DB_PATH = PATHS.data_dir / "vault.db"
VAULT_FILES_PATH = PATHS.data_dir / "vault_files"

class VaultService:
    """
    Vault storage service

    Security model:
    - All encryption happens client-side using Web Crypto API
    - Server only stores encrypted blobs (cannot read contents)
    - Real and decoy vaults are stored separately
    - No server-side password verification (zero-knowledge)
    """

    def __init__(self):
        self.db_path = VAULT_DB_PATH
        self.files_path = VAULT_FILES_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.files_path.mkdir(parents=True, exist_ok=True)
        self.is_unlocked = False  # Track vault unlock status
        self._init_db()
        logger.info("Vault service initialized")

    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Vault documents table
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

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vault_user_type
            ON vault_documents(user_id, vault_type, is_deleted)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vault_updated
            ON vault_documents(updated_at)
        """)

        # Vault files table (for file uploads)
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

        # Vault folders table
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

        # File tags table
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

        # File favorites table
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

        # File access logs table (for recent files)
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

        # Storage statistics cache table
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

        # ===== Day 4: Advanced Features =====

        # File versions table
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

        # File comments table
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

        # File shares/links table
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

        # Audit logs table
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

        # File metadata table (custom fields)
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
                UNIQUE(file_id, key)
            )
        """)

        # Pinned files table
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

        # Folder colors table
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

        # ===== Day 5: Performance Indexes =====

        # Additional indexes for vault_files
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vault_files_created
            ON vault_files(created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vault_files_mime
            ON vault_files(mime_type)
        """)

        # Additional indexes for vault_file_tags
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

        # ===== Phase B & G: User Management & Access Control =====

        # Users table
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

        # File Access Control Lists (ACL)
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

        # Folder Access Control Lists
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

        # User Roles
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

        # Sharing Invitations
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

        # ===== Phase 3: File Organization Rules =====

        # Organization rules table
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

        conn.commit()
        conn.close()

    def store_document(self, user_id: str, doc: VaultDocumentCreate, team_id: Optional[str] = None) -> VaultDocument:
        """
        Store encrypted vault document

        Args:
            user_id: User ID from auth
            doc: Encrypted document data

        Returns:
            Stored vault document
        """
        return documents_mod.store_document(self, user_id, doc, team_id)

    def get_document(self, user_id: str, doc_id: str, vault_type: str, team_id: Optional[str] = None) -> Optional[VaultDocument]:
        """Get encrypted vault document by ID (Phase 3: optional team scope)"""
        return documents_mod.get_document(self, user_id, doc_id, vault_type, team_id)

    def list_documents(self, user_id: str, vault_type: str, team_id: Optional[str] = None) -> VaultListResponse:
        """
        List all vault documents for a user and vault type

        Phase 3: if team_id is provided, return team-scoped documents.
        """
        return documents_mod.list_documents(self, user_id, vault_type, team_id)

    def update_document(self, user_id: str, doc_id: str, vault_type: str, update: VaultDocumentUpdate, team_id: Optional[str] = None) -> VaultDocument:
        """Update encrypted vault document (Phase 3: optional team scope)"""
        return documents_mod.update_document(self, user_id, doc_id, vault_type, update, team_id)

    def delete_document(self, user_id: str, doc_id: str, vault_type: str, team_id: Optional[str] = None) -> bool:
        """Soft-delete vault document (Phase 3: optional team scope)"""
        return documents_mod.delete_document(self, user_id, doc_id, vault_type, team_id)

    def get_vault_stats(self, user_id: str, vault_type: str) -> Dict[str, Any]:
        """Get vault statistics"""
        return documents_mod.get_vault_stats(self, user_id, vault_type)

    def upload_file(
        self,
        user_id: str,
        file_data: bytes,
        filename: str,
        mime_type: str,
        vault_type: str,
        passphrase: str,
        folder_path: str = "/"
    ) -> VaultFile:
        """
        Encrypt and store file in vault

        Args:
            user_id: User ID
            file_data: Raw file bytes
            filename: Original filename
            mime_type: MIME type
            vault_type: 'real' or 'decoy'
            passphrase: Vault passphrase for encryption

        Returns:
            VaultFile metadata
        """
        return files_mod.upload_file(self, user_id, file_data, filename, mime_type, vault_type, passphrase, folder_path)

    def list_files(self, user_id: str, vault_type: str, folder_path: str = None) -> List[VaultFile]:
        """List vault files, optionally filtered by folder"""
        return files_mod.list_files(self, user_id, vault_type, folder_path)

    def create_folder(
        self,
        user_id: str,
        vault_type: str,
        folder_name: str,
        parent_path: str = "/"
    ) -> VaultFolder:
        """Create a new folder in the vault"""
        return folders_mod.create_folder(self, user_id, vault_type, folder_name, parent_path)

    def list_folders(self, user_id: str, vault_type: str, parent_path: str = None) -> List[VaultFolder]:
        """List folders, optionally filtered by parent path"""
        return folders_mod.list_folders(self, user_id, vault_type, parent_path)

    def delete_folder(self, user_id: str, vault_type: str, folder_path: str) -> bool:
        """Soft-delete a folder (and all files/subfolders in it)"""
        return folders_mod.delete_folder(self, user_id, vault_type, folder_path)

    def delete_file(self, user_id: str, vault_type: str, file_id: str) -> bool:
        """Soft-delete a file"""
        return files_mod.delete_file(self, user_id, vault_type, file_id)

    def rename_file(self, user_id: str, vault_type: str, file_id: str, new_filename: str) -> bool:
        """Rename a file"""
        return files_mod.rename_file(self, user_id, vault_type, file_id, new_filename)

    def rename_folder(self, user_id: str, vault_type: str, old_path: str, new_name: str) -> bool:
        """Rename a folder and update all nested paths"""
        return folders_mod.rename_folder(self, user_id, vault_type, old_path, new_name)

    def move_file(self, user_id: str, vault_type: str, file_id: str, new_folder_path: str) -> bool:
        """Move a file to a different folder"""
        return files_mod.move_file(self, user_id, vault_type, file_id, new_folder_path)

    # ===== Tags Management =====

    def add_tag_to_file(self, user_id: str, vault_type: str, file_id: str, tag_name: str, tag_color: str = "#3B82F6") -> Dict[str, Any]:
        """Add a tag to a file"""
        return tags_mod.add_tag_to_file(self, user_id, vault_type, file_id, tag_name, tag_color)

    def remove_tag_from_file(self, user_id: str, vault_type: str, file_id: str, tag_name: str) -> bool:
        """Remove a tag from a file"""
        return tags_mod.remove_tag_from_file(self, user_id, vault_type, file_id, tag_name)

    def get_file_tags(self, user_id: str, vault_type: str, file_id: str) -> List[Dict[str, Any]]:
        """Get all tags for a file"""
        return tags_mod.get_file_tags(self, user_id, vault_type, file_id)

    # ===== Favorites Management =====

    def add_favorite(self, user_id: str, vault_type: str, file_id: str) -> Dict[str, Any]:
        """Add file to favorites"""
        return favorites_mod.add_favorite(self, user_id, vault_type, file_id)

    def remove_favorite(self, user_id: str, vault_type: str, file_id: str) -> bool:
        """Remove file from favorites"""
        return favorites_mod.remove_favorite(self, user_id, vault_type, file_id)

    def get_favorites(self, user_id: str, vault_type: str) -> List[str]:
        """Get list of favorite file IDs"""
        return favorites_mod.get_favorites(self, user_id, vault_type)

    # ===== Access Logging & Recent Files =====

    def log_file_access(self, user_id: str, vault_type: str, file_id: str, access_type: str = "view"):
        """Log file access for recent files tracking"""
        return analytics_mod.log_file_access(self, user_id, vault_type, file_id, access_type)

    def get_recent_files(self, user_id: str, vault_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently accessed files"""
        return analytics_mod.get_recent_files(self, user_id, vault_type, limit)

    # ===== Storage Statistics =====

    def get_storage_stats(self, user_id: str, vault_type: str) -> Dict[str, Any]:
        """Get storage statistics"""
        return analytics_mod.get_storage_stats(self, user_id, vault_type)

    # ===== Secure Deletion =====

    def secure_delete_file(self, user_id: str, vault_type: str, file_id: str) -> bool:
        """Securely delete a file by overwriting with random data before deletion"""
        return files_mod.secure_delete_file(self, user_id, vault_type, file_id)

    # ===== Day 4: File Versioning =====

    def create_file_version(self, user_id: str, vault_type: str, file_id: str,
                           encrypted_path: str, file_size: int, mime_type: str,
                           comment: str = None) -> Dict[str, Any]:
        """Create a new version of a file"""
        return files_mod.create_file_version(self, user_id, vault_type, file_id, encrypted_path, file_size, mime_type, comment)

    def get_file_versions(self, user_id: str, vault_type: str, file_id: str) -> List[Dict[str, Any]]:
        """Get all versions of a file"""
        return files_mod.get_file_versions(self, user_id, vault_type, file_id)

    def restore_file_version(self, user_id: str, vault_type: str, file_id: str,
                            version_id: str) -> Dict[str, Any]:
        """Restore a file to a previous version"""
        return files_mod.restore_file_version(self, user_id, vault_type, file_id, version_id)

    def delete_file_version(self, user_id: str, vault_type: str, version_id: str) -> bool:
        """Delete a specific file version"""
        return files_mod.delete_file_version(self, user_id, vault_type, version_id)

    # ===== Day 4: Trash/Recycle Bin =====

    def move_to_trash(self, user_id: str, vault_type: str, file_id: str) -> Dict[str, Any]:
        """Move a file to trash (soft delete)"""
        return files_mod.move_to_trash(self, user_id, vault_type, file_id)

    def restore_from_trash(self, user_id: str, vault_type: str, file_id: str) -> Dict[str, Any]:
        """Restore a file from trash"""
        return files_mod.restore_from_trash(self, user_id, vault_type, file_id)

    def get_trash_files(self, user_id: str, vault_type: str) -> List[Dict[str, Any]]:
        """Get all files in trash"""
        return files_mod.get_trash_files(self, user_id, vault_type)

    def empty_trash(self, user_id: str, vault_type: str) -> Dict[str, Any]:
        """Permanently delete all files in trash"""
        return files_mod.empty_trash(self, user_id, vault_type)

    # ===== Day 4: Advanced Search =====

    def search_files(self, user_id: str, vault_type: str, query: str = None,
                    mime_type: str = None, tags: List[str] = None,
                    date_from: str = None, date_to: str = None,
                    min_size: int = None, max_size: int = None,
                    folder_path: str = None) -> List[Dict[str, Any]]:
        """Advanced file search with multiple filters"""
        return search_mod.search_files(
            self,
            user_id=user_id,
            vault_type=vault_type,
            query=query,
            mime_type=mime_type,
            tags=tags,
            date_from=date_from,
            date_to=date_to,
            min_size=min_size,
            max_size=max_size,
            folder_path=folder_path,
        )

    # ===== Day 4: File Sharing =====

    def create_share_link(self, user_id: str, vault_type: str, file_id: str,
                         password: str = None, expires_at: str = None,
                         max_downloads: int = None, permissions: str = "download") -> Dict[str, Any]:
        """Create a shareable link for a file"""
        return sharing_mod.create_share_link(self, user_id, vault_type, file_id, password, expires_at, max_downloads, permissions)

    def get_share_link(self, share_token: str) -> Dict[str, Any]:
        """Get share link details"""
        return sharing_mod.get_share_link(self, share_token)

    def verify_share_password(self, share_token: str, password: str) -> bool:
        """Verify password for a share link"""
        return sharing_mod.verify_share_password(self, share_token, password)

    def increment_share_download(self, share_token: str) -> None:
        """Increment download counter for a share"""
        return sharing_mod.increment_share_download(self, share_token)

    def revoke_share_link(self, user_id: str, vault_type: str, share_id: str) -> bool:
        """Revoke a share link"""
        return sharing_mod.revoke_share_link(self, user_id, vault_type, share_id)

    def get_file_shares(self, user_id: str, vault_type: str, file_id: str) -> List[Dict[str, Any]]:
        """Get all share links for a file"""
        return sharing_mod.get_file_shares(self, user_id, vault_type, file_id)

    # ===== Day 4: Audit Logs =====

    def log_audit(self, user_id: str, vault_type: str, action: str,
                  resource_type: str, resource_id: str = None,
                  details: str = None, ip_address: str = None,
                  user_agent: str = None) -> str:
        """Log an audit event"""
        return audit_mod.log_audit(self, user_id, vault_type, action, resource_type, resource_id, details, ip_address, user_agent)

    def get_audit_logs(self, user_id: str, vault_type: str = None,
                      action: str = None, resource_type: str = None,
                      date_from: str = None, date_to: str = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit logs with filters"""
        return audit_mod.get_audit_logs(self, user_id, vault_type, action, resource_type, date_from, date_to, limit)

    # ===== Day 4: File Comments =====

    def add_file_comment(self, user_id: str, vault_type: str, file_id: str,
                        comment_text: str) -> Dict[str, Any]:
        """Add a comment to a file"""
        import uuid
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            comment_id = str(uuid.uuid4())
            now = datetime.now(UTC).isoformat()

            cursor.execute("""
                INSERT INTO vault_file_comments (
                    id, file_id, user_id, vault_type, comment_text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (comment_id, file_id, user_id, vault_type, comment_text, now))

            conn.commit()

            return {
                "id": comment_id,
                "file_id": file_id,
                "comment_text": comment_text,
                "created_at": now
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add comment: {e}")
            raise
        finally:
            conn.close()

    def get_file_comments(self, user_id: str, vault_type: str, file_id: str) -> List[Dict[str, Any]]:
        """Get all comments for a file"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, comment_text, created_at, updated_at
                FROM vault_file_comments
                WHERE file_id = ? AND user_id = ? AND vault_type = ?
                ORDER BY created_at DESC
            """, (file_id, user_id, vault_type))

            comments = []
            for row in cursor.fetchall():
                comments.append({
                    "id": row[0],
                    "comment_text": row[1],
                    "created_at": row[2],
                    "updated_at": row[3]
                })

            return comments

        finally:
            conn.close()

    def update_file_comment(self, user_id: str, vault_type: str, comment_id: str,
                           comment_text: str) -> Dict[str, Any]:
        """Update a comment"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            now = datetime.now(UTC).isoformat()

            cursor.execute("""
                UPDATE vault_file_comments
                SET comment_text = ?, updated_at = ?
                WHERE id = ? AND user_id = ? AND vault_type = ?
            """, (comment_text, now, comment_id, user_id, vault_type))

            if cursor.rowcount == 0:
                raise ValueError("Comment not found")

            conn.commit()

            return {
                "id": comment_id,
                "comment_text": comment_text,
                "updated_at": now
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update comment: {e}")
            raise
        finally:
            conn.close()

    def delete_file_comment(self, user_id: str, vault_type: str, comment_id: str) -> bool:
        """Delete a comment"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM vault_file_comments
                WHERE id = ? AND user_id = ? AND vault_type = ?
            """, (comment_id, user_id, vault_type))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete comment: {e}")
            raise
        finally:
            conn.close()

    # ===== Day 4: File Metadata =====

    def set_file_metadata(self, user_id: str, vault_type: str, file_id: str,
                         key: str, value: str) -> Dict[str, Any]:
        """Set custom metadata for a file"""
        import uuid
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            now = datetime.now(UTC).isoformat()

            # Try to update existing metadata
            cursor.execute("""
                UPDATE vault_file_metadata
                SET value = ?, updated_at = ?
                WHERE file_id = ? AND user_id = ? AND vault_type = ? AND key = ?
            """, (value, now, file_id, user_id, vault_type, key))

            # If no rows updated, insert new metadata
            if cursor.rowcount == 0:
                metadata_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO vault_file_metadata (
                        id, file_id, user_id, vault_type, key, value, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (metadata_id, file_id, user_id, vault_type, key, value, now))

            conn.commit()

            return {
                "key": key,
                "value": value,
                "updated_at": now
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to set metadata: {e}")
            raise
        finally:
            conn.close()

    def get_file_metadata(self, user_id: str, vault_type: str, file_id: str) -> Dict[str, str]:
        """Get all metadata for a file"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT key, value
                FROM vault_file_metadata
                WHERE file_id = ? AND user_id = ? AND vault_type = ?
            """, (file_id, user_id, vault_type))

            metadata = {}
            for row in cursor.fetchall():
                metadata[row[0]] = row[1]

            return metadata

        finally:
            conn.close()

    # ===== Day 4: Organization Features =====

    def pin_file(self, user_id: str, vault_type: str, file_id: str,
                pin_order: int = 0) -> Dict[str, Any]:
        """Pin a file for quick access"""
        return automation_mod.pin_file(self, user_id, vault_type, file_id, pin_order)

    def unpin_file(self, user_id: str, vault_type: str, file_id: str) -> bool:
        """Unpin a file"""
        return automation_mod.unpin_file(self, user_id, vault_type, file_id)

    def get_pinned_files(self, user_id: str, vault_type: str) -> List[Dict[str, Any]]:
        """Get all pinned files"""
        return automation_mod.get_pinned_files(self, user_id, vault_type)

    def set_folder_color(self, user_id: str, vault_type: str, folder_id: str,
                        color: str) -> Dict[str, Any]:
        """Set color for a folder"""
        return automation_mod.set_folder_color(self, user_id, vault_type, folder_id, color)

    def get_folder_colors(self, user_id: str, vault_type: str) -> Dict[str, str]:
        """Get all folder colors"""
        return automation_mod.get_folder_colors(self, user_id, vault_type)

    # ===== Day 4: Backup & Export =====

    def export_vault_data(self, user_id: str, vault_type: str) -> Dict[str, Any]:
        """Export vault metadata for backup"""
        return automation_mod.export_vault_data(self, user_id, vault_type)

    # ===== Day 5: Performance Features =====

    def generate_thumbnail(self, file_data: bytes, max_size: tuple = (200, 200)) -> Optional[bytes]:
        """
        Generate thumbnail for image files

        Args:
            file_data: Decrypted image file data
            max_size: Maximum thumbnail size (width, height)

        Returns:
            Thumbnail image as JPEG bytes, or None if generation fails
        """
        try:
            from PIL import Image
            import io

            # Open image from bytes
            img = Image.open(io.BytesIO(file_data))

            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P', 'LA'):
                # Create white background
                if img.mode == 'RGBA' or img.mode == 'LA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                    else:
                        background.paste(img, mask=img.split()[1])  # Use alpha channel
                    img = background
                else:
                    img = img.convert('RGB')

            # Generate thumbnail
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save to bytes
            thumb_io = io.BytesIO()
            img.save(thumb_io, format='JPEG', quality=85, optimize=True)
            return thumb_io.getvalue()

        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            return None


# Singleton instance
_vault_service: Optional[VaultService] = None


# Singleton instance
_vault_service: Optional[VaultService] = None


def get_vault_service() -> VaultService:
    """Get singleton vault service instance"""
    global _vault_service
    if _vault_service is None:
        _vault_service = VaultService()
    return _vault_service
