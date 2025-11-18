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
from datetime import datetime
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
        return storage.store_document_record(user_id, doc, team_id)

    def get_document(self, user_id: str, doc_id: str, vault_type: str, team_id: Optional[str] = None) -> Optional[VaultDocument]:
        """Get encrypted vault document by ID (Phase 3: optional team scope)"""
        return storage.get_document_record(user_id, doc_id, vault_type, team_id)

    def list_documents(self, user_id: str, vault_type: str, team_id: Optional[str] = None) -> VaultListResponse:
        """
        List all vault documents for a user and vault type

        Phase 3: if team_id is provided, return team-scoped documents.
        """
        documents = storage.list_documents_records(user_id, vault_type, team_id)
        return VaultListResponse(
            documents=documents,
            total_count=len(documents)
        )

    def update_document(self, user_id: str, doc_id: str, vault_type: str, update: VaultDocumentUpdate, team_id: Optional[str] = None) -> VaultDocument:
        """Update encrypted vault document (Phase 3: optional team scope)"""
        from fastapi import HTTPException

        success, rowcount = storage.update_document_record(user_id, doc_id, vault_type, update, team_id)

        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Document not found")

        # Fetch updated document
        updated_doc = self.get_document(user_id, doc_id, vault_type, team_id=team_id)
        if not updated_doc:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated document")

        return updated_doc

    def delete_document(self, user_id: str, doc_id: str, vault_type: str, team_id: Optional[str] = None) -> bool:
        """Soft-delete vault document (Phase 3: optional team scope)"""
        return storage.delete_document_record(user_id, doc_id, vault_type, team_id)

    def get_vault_stats(self, user_id: str, vault_type: str) -> Dict[str, Any]:
        """Get vault statistics"""
        return storage.get_vault_stats_record(user_id, vault_type)

    def _get_encryption_key(self, passphrase: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
        """
        Generate encryption key from passphrase using PBKDF2

        Returns:
            tuple: (encryption_key, salt) - Both as bytes
        """
        # Use provided salt or generate new one
        if salt is None:
            salt = hashlib.sha256(b"elohimos_vault_salt_v1").digest()[:16]

        # Use PBKDF2 with 600,000 iterations (OWASP 2023 recommendation)
        key_material = hashlib.pbkdf2_hmac(
            'sha256',
            passphrase.encode('utf-8'),
            salt,
            600000,  # iterations
            dklen=32  # 256-bit key
        )
        key = base64.urlsafe_b64encode(key_material)
        return key, salt

    def _generate_file_key(self) -> bytes:
        """Generate a random 256-bit key for file-level encryption"""
        import os
        file_key = os.urandom(32)  # 256 bits
        return base64.urlsafe_b64encode(file_key)

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
        import uuid

        # Generate unique file ID
        file_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        # Encrypt file data
        key, salt = self._get_encryption_key(passphrase)
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(file_data)

        # Save encrypted file to disk
        encrypted_filename = f"{file_id}_{hashlib.sha256(filename.encode()).hexdigest()}.enc"
        encrypted_path = self.files_path / encrypted_filename

        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)

        # Store metadata in database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO vault_files
                (id, user_id, vault_type, filename, file_size, mime_type,
                 encrypted_path, folder_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                user_id,
                vault_type,
                filename,
                len(file_data),
                mime_type,
                str(encrypted_path),
                folder_path,
                now,
                now
            ))

            conn.commit()

            return VaultFile(
                id=file_id,
                user_id=user_id,
                vault_type=vault_type,
                filename=filename,
                file_size=len(file_data),
                mime_type=mime_type,
                encrypted_path=str(encrypted_path),
                folder_path=folder_path,
                created_at=now,
                updated_at=now
            )

        except Exception as e:
            conn.rollback()
            # Clean up file if database insert fails
            if encrypted_path.exists():
                encrypted_path.unlink()
            logger.error(f"Failed to upload file: {e}")
            raise
        finally:
            conn.close()

    def list_files(self, user_id: str, vault_type: str, folder_path: str = None) -> List[VaultFile]:
        """List vault files, optionally filtered by folder"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        if folder_path is not None:
            # List files in specific folder only
            cursor.execute("""
                SELECT id, user_id, vault_type, filename, file_size, mime_type,
                       encrypted_path, folder_path, created_at, updated_at
                FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
                ORDER BY created_at DESC
            """, (user_id, vault_type, folder_path))
        else:
            # List all files
            cursor.execute("""
                SELECT id, user_id, vault_type, filename, file_size, mime_type,
                       encrypted_path, folder_path, created_at, updated_at
                FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
                ORDER BY created_at DESC
            """, (user_id, vault_type))

        rows = cursor.fetchall()
        conn.close()

        return [
            VaultFile(
                id=row[0],
                user_id=row[1],
                vault_type=row[2],
                filename=row[3],
                file_size=row[4],
                mime_type=row[5],
                encrypted_path=row[6],
                folder_path=row[7],
                created_at=row[8],
                updated_at=row[9]
            )
            for row in rows
        ]

    def create_folder(
        self,
        user_id: str,
        vault_type: str,
        folder_name: str,
        parent_path: str = "/"
    ) -> VaultFolder:
        """Create a new folder in the vault"""
        import uuid

        # Build full folder path
        if parent_path == "/":
            folder_path = f"/{folder_name}"
        else:
            folder_path = f"{parent_path}/{folder_name}"

        folder_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO vault_folders
                (id, user_id, vault_type, folder_name, folder_path, parent_path,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                folder_id,
                user_id,
                vault_type,
                folder_name,
                folder_path,
                parent_path,
                now,
                now
            ))

            conn.commit()

            return VaultFolder(
                id=folder_id,
                user_id=user_id,
                vault_type=vault_type,
                folder_name=folder_name,
                folder_path=folder_path,
                parent_path=parent_path,
                created_at=now,
                updated_at=now
            )

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create folder: {e}")
            raise
        finally:
            conn.close()

    def list_folders(self, user_id: str, vault_type: str, parent_path: str = None) -> List[VaultFolder]:
        """List folders, optionally filtered by parent path"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        if parent_path is not None:
            cursor.execute("""
                SELECT id, user_id, vault_type, folder_name, folder_path, parent_path,
                       created_at, updated_at
                FROM vault_folders
                WHERE user_id = ? AND vault_type = ? AND parent_path = ? AND is_deleted = 0
                ORDER BY folder_name ASC
            """, (user_id, vault_type, parent_path))
        else:
            cursor.execute("""
                SELECT id, user_id, vault_type, folder_name, folder_path, parent_path,
                       created_at, updated_at
                FROM vault_folders
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
                ORDER BY folder_name ASC
            """, (user_id, vault_type))

        rows = cursor.fetchall()
        conn.close()

        return [
            VaultFolder(
                id=row[0],
                user_id=row[1],
                vault_type=row[2],
                folder_name=row[3],
                folder_path=row[4],
                parent_path=row[5],
                created_at=row[6],
                updated_at=row[7]
            )
            for row in rows
        ]

    def delete_folder(self, user_id: str, vault_type: str, folder_path: str) -> bool:
        """Soft-delete a folder (and all files/subfolders in it)"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        try:
            # Delete folder
            cursor.execute("""
                UPDATE vault_folders
                SET is_deleted = 1, deleted_at = ?
                WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
            """, (now, user_id, vault_type, folder_path))

            # Delete all files in this folder
            cursor.execute("""
                UPDATE vault_files
                SET is_deleted = 1, deleted_at = ?
                WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
            """, (now, user_id, vault_type, folder_path))

            # Delete all subfolders (folders that start with this path)
            cursor.execute("""
                UPDATE vault_folders
                SET is_deleted = 1, deleted_at = ?
                WHERE user_id = ? AND vault_type = ?
                AND folder_path LIKE ? AND is_deleted = 0
            """, (now, user_id, vault_type, f"{folder_path}/%"))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete folder: {e}")
            raise
        finally:
            conn.close()

    def delete_file(self, user_id: str, vault_type: str, file_id: str) -> bool:
        """Soft-delete a file"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        try:
            cursor.execute("""
                UPDATE vault_files
                SET is_deleted = 1, deleted_at = ?
                WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
            """, (now, file_id, user_id, vault_type))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete file: {e}")
            raise
        finally:
            conn.close()

    def rename_file(self, user_id: str, vault_type: str, file_id: str, new_filename: str) -> bool:
        """Rename a file"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        try:
            cursor.execute("""
                UPDATE vault_files
                SET filename = ?, updated_at = ?
                WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
            """, (new_filename, now, file_id, user_id, vault_type))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to rename file: {e}")
            raise
        finally:
            conn.close()

    def rename_folder(self, user_id: str, vault_type: str, old_path: str, new_name: str) -> bool:
        """Rename a folder and update all nested paths"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        try:
            # Calculate new path
            parent_path = old_path.rsplit('/', 1)[0] if old_path.count('/') > 0 else '/'
            new_path = f"{parent_path}/{new_name}" if parent_path != '/' else f"/{new_name}"

            # Update the folder itself
            cursor.execute("""
                UPDATE vault_folders
                SET folder_name = ?, folder_path = ?, updated_at = ?
                WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
            """, (new_name, new_path, now, user_id, vault_type, old_path))

            # Update all subfolders
            cursor.execute("""
                UPDATE vault_folders
                SET folder_path = REPLACE(folder_path, ?, ?), updated_at = ?
                WHERE user_id = ? AND vault_type = ?
                AND folder_path LIKE ? AND is_deleted = 0
            """, (old_path, new_path, now, user_id, vault_type, f"{old_path}/%"))

            # Update all files in this folder
            cursor.execute("""
                UPDATE vault_files
                SET folder_path = ?, updated_at = ?
                WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
            """, (new_path, now, user_id, vault_type, old_path))

            # Update files in subfolders
            cursor.execute("""
                UPDATE vault_files
                SET folder_path = REPLACE(folder_path, ?, ?), updated_at = ?
                WHERE user_id = ? AND vault_type = ?
                AND folder_path LIKE ? AND is_deleted = 0
            """, (old_path, new_path, now, user_id, vault_type, f"{old_path}/%"))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to rename folder: {e}")
            raise
        finally:
            conn.close()

    def move_file(self, user_id: str, vault_type: str, file_id: str, new_folder_path: str) -> bool:
        """Move a file to a different folder"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        try:
            cursor.execute("""
                UPDATE vault_files
                SET folder_path = ?, updated_at = ?
                WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
            """, (new_folder_path, now, file_id, user_id, vault_type))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to move file: {e}")
            raise
        finally:
            conn.close()

    # ===== Tags Management =====

    def add_tag_to_file(self, user_id: str, vault_type: str, file_id: str, tag_name: str, tag_color: str = "#3B82F6") -> Dict[str, Any]:
        """Add a tag to a file"""
        import uuid
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        tag_id = str(uuid.uuid4())

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO vault_file_tags (id, file_id, user_id, vault_type, tag_name, tag_color, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (tag_id, file_id, user_id, vault_type, tag_name, tag_color, now))

            conn.commit()
            return {"id": tag_id, "file_id": file_id, "tag_name": tag_name, "tag_color": tag_color, "created_at": now}

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add tag: {e}")
            raise
        finally:
            conn.close()

    def remove_tag_from_file(self, user_id: str, vault_type: str, file_id: str, tag_name: str) -> bool:
        """Remove a tag from a file"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM vault_file_tags
                WHERE file_id = ? AND user_id = ? AND vault_type = ? AND tag_name = ?
            """, (file_id, user_id, vault_type, tag_name))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to remove tag: {e}")
            raise
        finally:
            conn.close()

    def get_file_tags(self, user_id: str, vault_type: str, file_id: str) -> List[Dict[str, Any]]:
        """Get all tags for a file"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, tag_name, tag_color, created_at
                FROM vault_file_tags
                WHERE file_id = ? AND user_id = ? AND vault_type = ?
                ORDER BY created_at DESC
            """, (file_id, user_id, vault_type))

            return [dict(row) for row in cursor.fetchall()]

        finally:
            conn.close()

    # ===== Favorites Management =====

    def add_favorite(self, user_id: str, vault_type: str, file_id: str) -> Dict[str, Any]:
        """Add file to favorites"""
        import uuid
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        favorite_id = str(uuid.uuid4())

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO vault_file_favorites (id, file_id, user_id, vault_type, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (favorite_id, file_id, user_id, vault_type, now))

            conn.commit()
            return {"id": favorite_id, "file_id": file_id, "created_at": now}

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add favorite: {e}")
            raise
        finally:
            conn.close()

    def remove_favorite(self, user_id: str, vault_type: str, file_id: str) -> bool:
        """Remove file from favorites"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM vault_file_favorites
                WHERE file_id = ? AND user_id = ? AND vault_type = ?
            """, (file_id, user_id, vault_type))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to remove favorite: {e}")
            raise
        finally:
            conn.close()

    def get_favorites(self, user_id: str, vault_type: str) -> List[str]:
        """Get list of favorite file IDs"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT file_id
                FROM vault_file_favorites
                WHERE user_id = ? AND vault_type = ?
                ORDER BY created_at DESC
            """, (user_id, vault_type))

            return [row[0] for row in cursor.fetchall()]

        finally:
            conn.close()

    # ===== Access Logging & Recent Files =====

    def log_file_access(self, user_id: str, vault_type: str, file_id: str, access_type: str = "view"):
        """Log file access for recent files tracking"""
        import uuid
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        log_id = str(uuid.uuid4())

        try:
            cursor.execute("""
                INSERT INTO vault_file_access_logs (id, file_id, user_id, vault_type, access_type, accessed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (log_id, file_id, user_id, vault_type, access_type, now))

            conn.commit()

        except Exception as e:
            # Don't fail the main operation if logging fails
            logger.warning(f"Failed to log file access: {e}")
        finally:
            conn.close()

    def get_recent_files(self, user_id: str, vault_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently accessed files"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT DISTINCT
                    vf.id, vf.filename, vf.file_size, vf.mime_type, vf.folder_path,
                    vf.created_at, vf.updated_at,
                    MAX(val.accessed_at) as last_accessed
                FROM vault_files vf
                INNER JOIN vault_file_access_logs val ON vf.id = val.file_id
                WHERE vf.user_id = ? AND vf.vault_type = ? AND vf.is_deleted = 0
                GROUP BY vf.id
                ORDER BY last_accessed DESC
                LIMIT ?
            """, (user_id, vault_type, limit))

            return [dict(row) for row in cursor.fetchall()]

        finally:
            conn.close()

    # ===== Storage Statistics =====

    def get_storage_stats(self, user_id: str, vault_type: str) -> Dict[str, Any]:
        """Get storage statistics"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Get total files and size
            cursor.execute("""
                SELECT COUNT(*) as total_files, COALESCE(SUM(file_size), 0) as total_size
                FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
            """, (user_id, vault_type))

            total_files, total_size = cursor.fetchone()

            # Get file type breakdown
            cursor.execute("""
                SELECT
                    CASE
                        WHEN mime_type LIKE 'image/%' THEN 'images'
                        WHEN mime_type LIKE 'video/%' THEN 'videos'
                        WHEN mime_type LIKE 'audio/%' THEN 'audio'
                        WHEN mime_type LIKE 'application/pdf' THEN 'documents'
                        WHEN mime_type LIKE 'text/%' THEN 'documents'
                        ELSE 'other'
                    END as category,
                    COUNT(*) as count,
                    COALESCE(SUM(file_size), 0) as size
                FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
                GROUP BY category
            """, (user_id, vault_type))

            breakdown = []
            for row in cursor.fetchall():
                category, count, size = row
                breakdown.append({"category": category, "count": count, "size": size})

            # Get largest files
            cursor.execute("""
                SELECT id, filename, file_size, mime_type, folder_path
                FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
                ORDER BY file_size DESC
                LIMIT 10
            """, (user_id, vault_type))

            largest_files = []
            for row in cursor.fetchall():
                largest_files.append({
                    "id": row[0],
                    "filename": row[1],
                    "file_size": row[2],
                    "mime_type": row[3],
                    "folder_path": row[4]
                })

            return {
                "total_files": total_files,
                "total_size": total_size,
                "breakdown": breakdown,
                "largest_files": largest_files
            }

        finally:
            conn.close()

    # ===== Secure Deletion =====

    def secure_delete_file(self, user_id: str, vault_type: str, file_id: str) -> bool:
        """Securely delete a file by overwriting with random data before deletion"""
        import os
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Get file path
            cursor.execute("""
                SELECT encrypted_path
                FROM vault_files
                WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
            """, (file_id, user_id, vault_type))

            result = cursor.fetchone()
            if not result:
                return False

            encrypted_path = result[0]
            file_path = self.files_path / encrypted_path

            # Securely overwrite file with random data (3 passes)
            if file_path.exists():
                file_size = file_path.stat().st_size
                with open(file_path, 'wb') as f:
                    for _ in range(3):
                        f.seek(0)
                        f.write(os.urandom(file_size))
                        f.flush()
                        os.fsync(f.fileno())

                # Delete the file
                os.remove(file_path)

            # Mark as deleted in database
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                UPDATE vault_files
                SET is_deleted = 1, deleted_at = ?
                WHERE id = ? AND user_id = ? AND vault_type = ?
            """, (now, file_id, user_id, vault_type))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to securely delete file: {e}")
            raise
        finally:
            conn.close()

    # ===== Day 4: File Versioning =====

    def create_file_version(self, user_id: str, vault_type: str, file_id: str,
                           encrypted_path: str, file_size: int, mime_type: str,
                           comment: str = None) -> Dict[str, Any]:
        """Create a new version of a file"""
        import uuid
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Get current version count
            cursor.execute("""
                SELECT COALESCE(MAX(version_number), 0)
                FROM vault_file_versions
                WHERE file_id = ?
            """, (file_id,))

            current_version = cursor.fetchone()[0]
            new_version = current_version + 1

            # Create version record
            version_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO vault_file_versions (
                    id, file_id, user_id, vault_type, version_number,
                    encrypted_path, file_size, mime_type, created_at,
                    created_by, comment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (version_id, file_id, user_id, vault_type, new_version,
                  encrypted_path, file_size, mime_type, now, user_id, comment))

            conn.commit()

            return {
                "id": version_id,
                "file_id": file_id,
                "version_number": new_version,
                "file_size": file_size,
                "mime_type": mime_type,
                "created_at": now,
                "comment": comment
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create file version: {e}")
            raise
        finally:
            conn.close()

    def get_file_versions(self, user_id: str, vault_type: str, file_id: str) -> List[Dict[str, Any]]:
        """Get all versions of a file"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, version_number, file_size, mime_type,
                       created_at, created_by, comment
                FROM vault_file_versions
                WHERE file_id = ? AND user_id = ? AND vault_type = ?
                ORDER BY version_number DESC
            """, (file_id, user_id, vault_type))

            versions = []
            for row in cursor.fetchall():
                versions.append({
                    "id": row[0],
                    "version_number": row[1],
                    "file_size": row[2],
                    "mime_type": row[3],
                    "created_at": row[4],
                    "created_by": row[5],
                    "comment": row[6]
                })

            return versions

        finally:
            conn.close()

    def restore_file_version(self, user_id: str, vault_type: str, file_id: str,
                            version_id: str) -> Dict[str, Any]:
        """Restore a file to a previous version"""
        import shutil
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Get version details
            cursor.execute("""
                SELECT encrypted_path, file_size, mime_type, version_number
                FROM vault_file_versions
                WHERE id = ? AND file_id = ? AND user_id = ? AND vault_type = ?
            """, (version_id, file_id, user_id, vault_type))

            version_data = cursor.fetchone()
            if not version_data:
                raise ValueError("Version not found")

            version_encrypted_path, version_size, version_mime, version_number = version_data

            # Get current file details
            cursor.execute("""
                SELECT encrypted_path
                FROM vault_files
                WHERE id = ? AND user_id = ? AND vault_type = ?
            """, (file_id, user_id, vault_type))

            current_data = cursor.fetchone()
            if not current_data:
                raise ValueError("File not found")

            current_encrypted_path = current_data[0]

            # Copy version file to current file location
            version_path = self.files_path / version_encrypted_path
            current_path = self.files_path / current_encrypted_path

            if version_path.exists():
                shutil.copy2(version_path, current_path)

            # Update file record
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                UPDATE vault_files
                SET file_size = ?, mime_type = ?, updated_at = ?
                WHERE id = ? AND user_id = ? AND vault_type = ?
            """, (version_size, version_mime, now, file_id, user_id, vault_type))

            conn.commit()

            return {
                "id": file_id,
                "restored_version": version_number,
                "file_size": version_size,
                "updated_at": now
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to restore file version: {e}")
            raise
        finally:
            conn.close()

    def delete_file_version(self, user_id: str, vault_type: str, version_id: str) -> bool:
        """Delete a specific file version"""
        import os
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Get version file path
            cursor.execute("""
                SELECT encrypted_path
                FROM vault_file_versions
                WHERE id = ? AND user_id = ? AND vault_type = ?
            """, (version_id, user_id, vault_type))

            result = cursor.fetchone()
            if not result:
                return False

            encrypted_path = result[0]

            # Delete physical file
            file_path = self.files_path / encrypted_path
            if file_path.exists():
                os.remove(file_path)

            # Delete version record
            cursor.execute("""
                DELETE FROM vault_file_versions
                WHERE id = ? AND user_id = ? AND vault_type = ?
            """, (version_id, user_id, vault_type))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete file version: {e}")
            raise
        finally:
            conn.close()

    # ===== Day 4: Trash/Recycle Bin =====

    def move_to_trash(self, user_id: str, vault_type: str, file_id: str) -> Dict[str, Any]:
        """Move a file to trash (soft delete)"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                UPDATE vault_files
                SET is_deleted = 1, deleted_at = ?
                WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
            """, (now, file_id, user_id, vault_type))

            if cursor.rowcount == 0:
                raise ValueError("File not found or already deleted")

            conn.commit()

            return {
                "id": file_id,
                "deleted_at": now,
                "status": "moved to trash"
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to move file to trash: {e}")
            raise
        finally:
            conn.close()

    def restore_from_trash(self, user_id: str, vault_type: str, file_id: str) -> Dict[str, Any]:
        """Restore a file from trash"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE vault_files
                SET is_deleted = 0, deleted_at = NULL
                WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 1
            """, (file_id, user_id, vault_type))

            if cursor.rowcount == 0:
                raise ValueError("File not found in trash")

            conn.commit()

            return {
                "id": file_id,
                "status": "restored from trash"
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to restore file from trash: {e}")
            raise
        finally:
            conn.close()

    def get_trash_files(self, user_id: str, vault_type: str) -> List[Dict[str, Any]]:
        """Get all files in trash"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, filename, file_size, mime_type, folder_path,
                       deleted_at,
                       CASE
                           WHEN mime_type LIKE 'image/%' THEN 'images'
                           WHEN mime_type LIKE 'video/%' THEN 'videos'
                           WHEN mime_type LIKE 'audio/%' THEN 'audio'
                           WHEN mime_type LIKE 'application/pdf' THEN 'documents'
                           WHEN mime_type LIKE 'text/%' THEN 'documents'
                           ELSE 'other'
                       END as category
                FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 1
                ORDER BY deleted_at DESC
            """, (user_id, vault_type))

            trash_files = []
            for row in cursor.fetchall():
                trash_files.append({
                    "id": row[0],
                    "filename": row[1],
                    "file_size": row[2],
                    "mime_type": row[3],
                    "folder_path": row[4],
                    "deleted_at": row[5],
                    "category": row[6]
                })

            return trash_files

        finally:
            conn.close()

    def empty_trash(self, user_id: str, vault_type: str) -> Dict[str, Any]:
        """Permanently delete all files in trash"""
        import os
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Get all trashed files
            cursor.execute("""
                SELECT id, encrypted_path
                FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 1
            """, (user_id, vault_type))

            trashed_files = cursor.fetchall()
            deleted_count = 0

            # Delete physical files
            for file_id, encrypted_path in trashed_files:
                file_path = self.files_path / encrypted_path
                if file_path.exists():
                    os.remove(file_path)
                deleted_count += 1

            # Delete from database
            cursor.execute("""
                DELETE FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 1
            """, (user_id, vault_type))

            conn.commit()

            return {
                "deleted_count": deleted_count,
                "status": "trash emptied"
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to empty trash: {e}")
            raise
        finally:
            conn.close()

    # ===== Day 4: Advanced Search =====

    def search_files(self, user_id: str, vault_type: str, query: str = None,
                    mime_type: str = None, tags: List[str] = None,
                    date_from: str = None, date_to: str = None,
                    min_size: int = None, max_size: int = None,
                    folder_path: str = None) -> List[Dict[str, Any]]:
        """Advanced file search with multiple filters"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Build dynamic query
            sql = """
                SELECT DISTINCT f.id, f.filename, f.file_size, f.mime_type,
                       f.folder_path, f.created_at, f.updated_at,
                       CASE
                           WHEN f.mime_type LIKE 'image/%' THEN 'images'
                           WHEN f.mime_type LIKE 'video/%' THEN 'videos'
                           WHEN f.mime_type LIKE 'audio/%' THEN 'audio'
                           WHEN f.mime_type LIKE 'application/pdf' THEN 'documents'
                           WHEN f.mime_type LIKE 'text/%' THEN 'documents'
                           ELSE 'other'
                       END as category
                FROM vault_files f
            """

            conditions = ["f.user_id = ?", "f.vault_type = ?", "f.is_deleted = 0"]
            params = [user_id, vault_type]

            # Add tag join if searching by tags
            if tags:
                sql += " LEFT JOIN vault_file_tags t ON f.id = t.file_id"
                tag_conditions = " OR ".join(["t.tag_name = ?"] * len(tags))
                conditions.append(f"({tag_conditions})")
                params.extend(tags)

            # Text search
            if query:
                conditions.append("f.filename LIKE ?")
                params.append(f"%{query}%")

            # MIME type filter
            if mime_type:
                conditions.append("f.mime_type LIKE ?")
                params.append(f"{mime_type}%")

            # Date range
            if date_from:
                conditions.append("f.created_at >= ?")
                params.append(date_from)
            if date_to:
                conditions.append("f.created_at <= ?")
                params.append(date_to)

            # Size range
            if min_size is not None:
                conditions.append("f.file_size >= ?")
                params.append(min_size)
            if max_size is not None:
                conditions.append("f.file_size <= ?")
                params.append(max_size)

            # Folder filter
            if folder_path:
                conditions.append("f.folder_path = ?")
                params.append(folder_path)

            sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY f.updated_at DESC"

            cursor.execute(sql, params)

            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "filename": row[1],
                    "file_size": row[2],
                    "mime_type": row[3],
                    "folder_path": row[4],
                    "created_at": row[5],
                    "updated_at": row[6],
                    "category": row[7]
                })

            return results

        finally:
            conn.close()

    # ===== Day 4: File Sharing =====

    def create_share_link(self, user_id: str, vault_type: str, file_id: str,
                         password: str = None, expires_at: str = None,
                         max_downloads: int = None, permissions: str = "download") -> Dict[str, Any]:
        """Create a shareable link for a file"""
        import uuid
        import hashlib
        import secrets
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Generate secure share token
            share_token = secrets.token_urlsafe(32)
            share_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            # Hash password if provided
            password_hash = None
            if password:
                password_hash = hashlib.sha256(password.encode()).hexdigest()

            cursor.execute("""
                INSERT INTO vault_file_shares (
                    id, file_id, user_id, vault_type, share_token,
                    password_hash, expires_at, max_downloads, permissions,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (share_id, file_id, user_id, vault_type, share_token,
                  password_hash, expires_at, max_downloads, permissions, now))

            conn.commit()

            return {
                "id": share_id,
                "share_token": share_token,
                "expires_at": expires_at,
                "max_downloads": max_downloads,
                "permissions": permissions,
                "created_at": now
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create share link: {e}")
            raise
        finally:
            conn.close()

    def get_share_link(self, share_token: str) -> Dict[str, Any]:
        """Get share link details"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT s.id, s.file_id, s.password_hash, s.expires_at,
                       s.max_downloads, s.download_count, s.permissions,
                       f.filename, f.file_size, f.mime_type
                FROM vault_file_shares s
                JOIN vault_files f ON s.file_id = f.id
                WHERE s.share_token = ?
            """, (share_token,))

            result = cursor.fetchone()
            if not result:
                raise ValueError("Share link not found")

            share_id, file_id, password_hash, expires_at, max_downloads, \
                download_count, permissions, filename, file_size, mime_type = result

            # Check if expired
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at)
                if datetime.utcnow() > expires_dt:
                    raise ValueError("Share link has expired")

            # Check download limit
            if max_downloads and download_count >= max_downloads:
                raise ValueError("Download limit reached")

            return {
                "id": share_id,
                "file_id": file_id,
                "filename": filename,
                "file_size": file_size,
                "mime_type": mime_type,
                "requires_password": password_hash is not None,
                "permissions": permissions,
                "download_count": download_count,
                "max_downloads": max_downloads
            }

        finally:
            conn.close()

    def verify_share_password(self, share_token: str, password: str) -> bool:
        """Verify password for a share link"""
        import hashlib
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT password_hash
                FROM vault_file_shares
                WHERE share_token = ?
            """, (share_token,))

            result = cursor.fetchone()
            if not result or not result[0]:
                return True  # No password required

            stored_hash = result[0]
            provided_hash = hashlib.sha256(password.encode()).hexdigest()

            return stored_hash == provided_hash

        finally:
            conn.close()

    def increment_share_download(self, share_token: str) -> None:
        """Increment download counter for a share"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                UPDATE vault_file_shares
                SET download_count = download_count + 1,
                    last_accessed = ?
                WHERE share_token = ?
            """, (now, share_token))

            conn.commit()

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to increment share download: {e}")
            raise
        finally:
            conn.close()

    def revoke_share_link(self, user_id: str, vault_type: str, share_id: str) -> bool:
        """Revoke a share link"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM vault_file_shares
                WHERE id = ? AND user_id = ? AND vault_type = ?
            """, (share_id, user_id, vault_type))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to revoke share link: {e}")
            raise
        finally:
            conn.close()

    def get_file_shares(self, user_id: str, vault_type: str, file_id: str) -> List[Dict[str, Any]]:
        """Get all share links for a file"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, share_token, expires_at, max_downloads,
                       download_count, permissions, created_at, last_accessed
                FROM vault_file_shares
                WHERE file_id = ? AND user_id = ? AND vault_type = ?
                ORDER BY created_at DESC
            """, (file_id, user_id, vault_type))

            shares = []
            for row in cursor.fetchall():
                shares.append({
                    "id": row[0],
                    "share_token": row[1],
                    "expires_at": row[2],
                    "max_downloads": row[3],
                    "download_count": row[4],
                    "permissions": row[5],
                    "created_at": row[6],
                    "last_accessed": row[7]
                })

            return shares

        finally:
            conn.close()

    # ===== Day 4: Audit Logs =====

    def log_audit(self, user_id: str, vault_type: str, action: str,
                  resource_type: str, resource_id: str = None,
                  details: str = None, ip_address: str = None,
                  user_agent: str = None) -> str:
        """Log an audit event"""
        import uuid
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            log_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO vault_audit_logs (
                    id, user_id, vault_type, action, resource_type,
                    resource_id, details, ip_address, user_agent, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (log_id, user_id, vault_type, action, resource_type,
                  resource_id, details, ip_address, user_agent, now))

            conn.commit()
            return log_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to log audit: {e}")
            raise
        finally:
            conn.close()

    def get_audit_logs(self, user_id: str, vault_type: str = None,
                      action: str = None, resource_type: str = None,
                      date_from: str = None, date_to: str = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit logs with filters"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            sql = """
                SELECT id, user_id, vault_type, action, resource_type,
                       resource_id, details, ip_address, user_agent, created_at
                FROM vault_audit_logs
                WHERE user_id = ?
            """
            params = [user_id]

            if vault_type:
                sql += " AND vault_type = ?"
                params.append(vault_type)

            if action:
                sql += " AND action = ?"
                params.append(action)

            if resource_type:
                sql += " AND resource_type = ?"
                params.append(resource_type)

            if date_from:
                sql += " AND created_at >= ?"
                params.append(date_from)

            if date_to:
                sql += " AND created_at <= ?"
                params.append(date_to)

            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(sql, params)

            logs = []
            for row in cursor.fetchall():
                logs.append({
                    "id": row[0],
                    "user_id": row[1],
                    "vault_type": row[2],
                    "action": row[3],
                    "resource_type": row[4],
                    "resource_id": row[5],
                    "details": row[6],
                    "ip_address": row[7],
                    "user_agent": row[8],
                    "created_at": row[9]
                })

            return logs

        finally:
            conn.close()

    # ===== Day 4: File Comments =====

    def add_file_comment(self, user_id: str, vault_type: str, file_id: str,
                        comment_text: str) -> Dict[str, Any]:
        """Add a comment to a file"""
        import uuid
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            comment_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

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
            now = datetime.utcnow().isoformat()

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
            now = datetime.utcnow().isoformat()

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
        import uuid
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            pin_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO vault_pinned_files (
                    id, file_id, user_id, vault_type, pin_order, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (pin_id, file_id, user_id, vault_type, pin_order, now))

            conn.commit()

            return {
                "id": pin_id,
                "file_id": file_id,
                "pin_order": pin_order,
                "created_at": now
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to pin file: {e}")
            raise
        finally:
            conn.close()

    def unpin_file(self, user_id: str, vault_type: str, file_id: str) -> bool:
        """Unpin a file"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM vault_pinned_files
                WHERE file_id = ? AND user_id = ? AND vault_type = ?
            """, (file_id, user_id, vault_type))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to unpin file: {e}")
            raise
        finally:
            conn.close()

    def get_pinned_files(self, user_id: str, vault_type: str) -> List[Dict[str, Any]]:
        """Get all pinned files"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT f.id, f.filename, f.file_size, f.mime_type,
                       f.folder_path, p.pin_order, p.created_at
                FROM vault_pinned_files p
                JOIN vault_files f ON p.file_id = f.id
                WHERE p.user_id = ? AND p.vault_type = ? AND f.is_deleted = 0
                ORDER BY p.pin_order ASC, p.created_at DESC
            """, (user_id, vault_type))

            pinned = []
            for row in cursor.fetchall():
                pinned.append({
                    "id": row[0],
                    "filename": row[1],
                    "file_size": row[2],
                    "mime_type": row[3],
                    "folder_path": row[4],
                    "pin_order": row[5],
                    "pinned_at": row[6]
                })

            return pinned

        finally:
            conn.close()

    def set_folder_color(self, user_id: str, vault_type: str, folder_id: str,
                        color: str) -> Dict[str, Any]:
        """Set color for a folder"""
        import uuid
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            now = datetime.utcnow().isoformat()

            # Try to update existing color
            cursor.execute("""
                UPDATE vault_folder_colors
                SET color = ?
                WHERE folder_id = ? AND user_id = ? AND vault_type = ?
            """, (color, folder_id, user_id, vault_type))

            # If no rows updated, insert new color
            if cursor.rowcount == 0:
                color_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO vault_folder_colors (
                        id, folder_id, user_id, vault_type, color, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (color_id, folder_id, user_id, vault_type, color, now))

            conn.commit()

            return {
                "folder_id": folder_id,
                "color": color
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to set folder color: {e}")
            raise
        finally:
            conn.close()

    def get_folder_colors(self, user_id: str, vault_type: str) -> Dict[str, str]:
        """Get all folder colors"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT folder_id, color
                FROM vault_folder_colors
                WHERE user_id = ? AND vault_type = ?
            """, (user_id, vault_type))

            colors = {}
            for row in cursor.fetchall():
                colors[row[0]] = row[1]

            return colors

        finally:
            conn.close()

    # ===== Day 4: Backup & Export =====

    def export_vault_data(self, user_id: str, vault_type: str) -> Dict[str, Any]:
        """Export vault metadata for backup"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Export files metadata
            cursor.execute("""
                SELECT id, filename, file_size, mime_type, folder_path,
                       encrypted_path,
                       CASE
                           WHEN mime_type LIKE 'image/%' THEN 'images'
                           WHEN mime_type LIKE 'video/%' THEN 'videos'
                           WHEN mime_type LIKE 'audio/%' THEN 'audio'
                           WHEN mime_type LIKE 'application/pdf' THEN 'documents'
                           WHEN mime_type LIKE 'text/%' THEN 'documents'
                           ELSE 'other'
                       END as category,
                       created_at, updated_at
                FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
            """, (user_id, vault_type))

            files = []
            for row in cursor.fetchall():
                files.append({
                    "id": row[0],
                    "filename": row[1],
                    "file_size": row[2],
                    "mime_type": row[3],
                    "folder_path": row[4],
                    "encrypted_path": row[5],
                    "category": row[6],
                    "created_at": row[7],
                    "updated_at": row[8]
                })

            # Export folders
            cursor.execute("""
                SELECT id, folder_name, folder_path, parent_path, created_at
                FROM vault_folders
                WHERE user_id = ? AND vault_type = ?
            """, (user_id, vault_type))

            folders = []
            for row in cursor.fetchall():
                folders.append({
                    "id": row[0],
                    "folder_name": row[1],
                    "folder_path": row[2],
                    "parent_path": row[3],
                    "created_at": row[4]
                })

            # Export tags
            cursor.execute("""
                SELECT file_id, tag_name, tag_color
                FROM vault_file_tags
                WHERE user_id = ? AND vault_type = ?
            """, (user_id, vault_type))

            tags = []
            for row in cursor.fetchall():
                tags.append({
                    "file_id": row[0],
                    "tag_name": row[1],
                    "tag_color": row[2]
                })

            return {
                "vault_type": vault_type,
                "export_date": datetime.utcnow().isoformat(),
                "files": files,
                "folders": folders,
                "tags": tags
            }

        finally:
            conn.close()

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
