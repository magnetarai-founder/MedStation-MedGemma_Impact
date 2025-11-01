#!/usr/bin/env python3
"""
Vault Service for ElohimOS
Secure storage for encrypted documents with plausible deniability
Backend handles encrypted blobs only - all encryption happens client-side
"""

import sqlite3
import logging
import base64
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from auth_middleware import get_current_user
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Import security utilities
from utils import sanitize_filename

# Import WebSocket connection manager
from .websocket_manager import manager

# Database path
VAULT_DB_PATH = Path(".neutron_data/vault.db")
VAULT_FILES_PATH = Path(".neutron_data/vault_files")


# ===== Models =====

class VaultDocument(BaseModel):
    """Encrypted vault document"""
    id: str
    user_id: str
    vault_type: str = Field(..., description="'real' or 'decoy'")
    encrypted_blob: str = Field(..., description="Client-side encrypted document data")
    encrypted_metadata: str = Field(..., description="Client-side encrypted metadata")
    created_at: str
    updated_at: str
    size_bytes: int


class VaultDocumentCreate(BaseModel):
    """Request to create vault document"""
    id: str
    vault_type: str  # 'real' or 'decoy'
    encrypted_blob: str
    encrypted_metadata: str


class VaultDocumentUpdate(BaseModel):
    """Request to update vault document"""
    encrypted_blob: str
    encrypted_metadata: str


class VaultListResponse(BaseModel):
    """List of vault documents"""
    documents: List[VaultDocument]
    total_count: int


class VaultFile(BaseModel):
    """Encrypted vault file"""
    id: str
    user_id: str
    vault_type: str
    filename: str
    file_size: int
    mime_type: str
    encrypted_path: str
    folder_path: str = "/"  # Default to root folder
    created_at: str
    updated_at: str


class VaultFolder(BaseModel):
    """Vault folder"""
    id: str
    user_id: str
    vault_type: str
    folder_name: str
    folder_path: str  # Full path like "/Documents/Medical"
    parent_path: str  # Parent folder path
    created_at: str
    updated_at: str


# ===== Service =====

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

    def store_document(self, user_id: str, doc: VaultDocumentCreate) -> VaultDocument:
        """
        Store encrypted vault document

        Args:
            user_id: User ID from auth
            doc: Encrypted document data

        Returns:
            Stored vault document
        """
        now = datetime.utcnow().isoformat()
        size_bytes = len(doc.encrypted_blob) + len(doc.encrypted_metadata)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO vault_documents
                (id, user_id, vault_type, encrypted_blob, encrypted_metadata,
                 created_at, updated_at, size_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.id,
                user_id,
                doc.vault_type,
                doc.encrypted_blob,
                doc.encrypted_metadata,
                now,
                now,
                size_bytes
            ))

            conn.commit()

            return VaultDocument(
                id=doc.id,
                user_id=user_id,
                vault_type=doc.vault_type,
                encrypted_blob=doc.encrypted_blob,
                encrypted_metadata=doc.encrypted_metadata,
                created_at=now,
                updated_at=now,
                size_bytes=size_bytes
            )

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to store vault document: {e}")
            raise
        finally:
            conn.close()

    def get_document(self, user_id: str, doc_id: str, vault_type: str) -> Optional[VaultDocument]:
        """Get encrypted vault document by ID"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, user_id, vault_type, encrypted_blob, encrypted_metadata,
                   created_at, updated_at, size_bytes
            FROM vault_documents
            WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
        """, (doc_id, user_id, vault_type))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return VaultDocument(
            id=row[0],
            user_id=row[1],
            vault_type=row[2],
            encrypted_blob=row[3],
            encrypted_metadata=row[4],
            created_at=row[5],
            updated_at=row[6],
            size_bytes=row[7]
        )

    def list_documents(self, user_id: str, vault_type: str) -> VaultListResponse:
        """List all vault documents for a user and vault type"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, user_id, vault_type, encrypted_blob, encrypted_metadata,
                   created_at, updated_at, size_bytes
            FROM vault_documents
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
            ORDER BY updated_at DESC
        """, (user_id, vault_type))

        rows = cursor.fetchall()
        conn.close()

        documents = [
            VaultDocument(
                id=row[0],
                user_id=row[1],
                vault_type=row[2],
                encrypted_blob=row[3],
                encrypted_metadata=row[4],
                created_at=row[5],
                updated_at=row[6],
                size_bytes=row[7]
            )
            for row in rows
        ]

        return VaultListResponse(
            documents=documents,
            total_count=len(documents)
        )

    def update_document(self, user_id: str, doc_id: str, vault_type: str, update: VaultDocumentUpdate) -> VaultDocument:
        """Update encrypted vault document"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()
        size_bytes = len(update.encrypted_blob) + len(update.encrypted_metadata)

        try:
            cursor.execute("""
                UPDATE vault_documents
                SET encrypted_blob = ?,
                    encrypted_metadata = ?,
                    updated_at = ?,
                    size_bytes = ?
                WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
            """, (
                update.encrypted_blob,
                update.encrypted_metadata,
                now,
                size_bytes,
                doc_id,
                user_id,
                vault_type
            ))

            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Document not found")

            conn.commit()

            # Fetch updated document
            updated_doc = self.get_document(user_id, doc_id, vault_type)
            if not updated_doc:
                raise HTTPException(status_code=500, detail="Failed to retrieve updated document")

            return updated_doc

        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update vault document: {e}")
            raise
        finally:
            conn.close()

    def delete_document(self, user_id: str, doc_id: str, vault_type: str) -> bool:
        """Soft-delete vault document"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()

        try:
            cursor.execute("""
                UPDATE vault_documents
                SET is_deleted = 1,
                    deleted_at = ?
                WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
            """, (now, doc_id, user_id, vault_type))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete vault document: {e}")
            raise
        finally:
            conn.close()

    def get_vault_stats(self, user_id: str, vault_type: str) -> Dict[str, Any]:
        """Get vault statistics"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as doc_count,
                SUM(size_bytes) as total_size
            FROM vault_documents
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
        """, (user_id, vault_type))

        row = cursor.fetchone()
        conn.close()

        return {
            "document_count": row[0] or 0,
            "total_size_bytes": row[1] or 0,
            "vault_type": vault_type
        }

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


def get_vault_service() -> VaultService:
    """Get singleton vault service instance"""
    global _vault_service
    if _vault_service is None:
        _vault_service = VaultService()
    return _vault_service


# ===== Router =====

router = APIRouter(
    prefix="/api/v1/vault",
    tags=["Vault"],
    dependencies=[Depends(get_current_user)]  # Require auth for ALL vault endpoints
)


@router.post("/documents", response_model=VaultDocument)
async def create_vault_document(
    vault_type: str,
    document: VaultDocumentCreate,
    current_user: Dict = Depends(get_current_user)
):
    """
    Store encrypted vault document

    Security: All encryption happens client-side
    Server only stores encrypted blobs
    """
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if document.vault_type != vault_type:
        raise HTTPException(status_code=400, detail="Vault type mismatch")

    service = get_vault_service()
    return service.store_document(user_id, document)


@router.get("/documents", response_model=VaultListResponse)
async def list_vault_documents(
    vault_type: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    List all vault documents

    Returns encrypted blobs that must be decrypted client-side
    """
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    return service.list_documents(user_id, vault_type)


@router.get("/documents/{doc_id}", response_model=VaultDocument)
async def get_vault_document(doc_id: str, vault_type: str):
    """Get single vault document"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    doc = service.get_document(user_id, doc_id, vault_type)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc


@router.put("/documents/{doc_id}", response_model=VaultDocument)
async def update_vault_document(
    doc_id: str,
    vault_type: str,
    update: VaultDocumentUpdate
):
    """Update vault document"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    return service.update_document(user_id, doc_id, vault_type, update)


@router.delete("/documents/{doc_id}")
async def delete_vault_document(doc_id: str, vault_type: str):
    """Delete vault document (soft delete)"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    success = service.delete_document(user_id, doc_id, vault_type)

    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"success": True, "message": "Document deleted"}


@router.get("/stats")
async def get_vault_stats(vault_type: str):
    """Get vault statistics"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    return service.get_vault_stats(user_id, vault_type)


@router.post("/upload", response_model=VaultFile)
async def upload_vault_file(
    request: Request,
    file: UploadFile = File(...),
    vault_passphrase: str = Form(...),
    vault_type: str = Form(default="real"),
    folder_path: str = Form(default="/")
):
    """
    Upload and encrypt file to vault

    Args:
        file: File to upload
        vault_passphrase: Vault passphrase for encryption
        vault_type: 'real' or 'decoy' (default: 'real')
        folder_path: Folder path to upload to (default: '/')

    Returns:
        VaultFile metadata
    """
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    # Read file data
    file_data = await file.read()

    if not file_data:
        raise HTTPException(status_code=400, detail="Empty file")

    # Get MIME type
    mime_type = file.content_type or "application/octet-stream"

    # Upload and encrypt
    service = get_vault_service()
    try:
        # Sanitize filename to prevent path traversal (HIGH-01)
        safe_filename = sanitize_filename(file.filename or "untitled")
        vault_file = service.upload_file(
            user_id=user_id,
            file_data=file_data,
            filename=safe_filename,
            mime_type=mime_type,
            vault_type=vault_type,
            passphrase=vault_passphrase,
            folder_path=folder_path
        )

        # Broadcast file upload event to connected clients
        await manager.broadcast_file_event(
            event_type="file_uploaded",
            file_data=vault_file,
            vault_type=vault_type,
            user_id=user_id
        )

        return vault_file
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/upload-chunk")
async def upload_chunk(
    request: Request,
    chunk: UploadFile = File(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    file_id: str = Form(...),
    filename: str = Form(...),
    vault_passphrase: str = Form(...),
    vault_type: str = Form(default="real"),
    folder_path: str = Form(default="/")
):
    """
    Upload file in chunks for large files

    Chunks are stored temporarily and assembled when all chunks are received

    Args:
        chunk: File chunk to upload
        chunk_index: Index of this chunk (0-based)
        total_chunks: Total number of chunks for this file
        file_id: Unique identifier for this file (should be same for all chunks)
        filename: Original filename
        vault_passphrase: Vault passphrase for encryption
        vault_type: 'real' or 'decoy' (default: 'real')
        folder_path: Folder path to upload to (default: '/')

    Returns:
        Status and progress information
    """
    import shutil

    user_id = "default_user"
    service = get_vault_service()

    # Create temp directory for chunks
    temp_dir = service.files_path / "temp_chunks" / file_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Save chunk
    chunk_path = temp_dir / f"chunk_{chunk_index}"
    chunk_data = await chunk.read()
    with open(chunk_path, 'wb') as f:
        f.write(chunk_data)

    # Check if all chunks received
    received_chunks = list(temp_dir.glob("chunk_*"))

    if len(received_chunks) == total_chunks:
        # Assemble complete file
        complete_file = b""
        for i in range(total_chunks):
            chunk_file = temp_dir / f"chunk_{i}"
            if not chunk_file.exists():
                raise HTTPException(status_code=400, detail=f"Missing chunk {i}")
            with open(chunk_file, 'rb') as f:
                complete_file += f.read()

        # Detect MIME type from filename
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/octet-stream"

        # Upload assembled file
        try:
            vault_file = service.upload_file(
                user_id=user_id,
                file_data=complete_file,
                filename=filename,
                mime_type=mime_type,
                vault_type=vault_type,
                passphrase=vault_passphrase,
                folder_path=folder_path
            )

            # Cleanup temp chunks
            shutil.rmtree(temp_dir)

            return {
                "status": "complete",
                "file": vault_file,
                "chunks_received": len(received_chunks),
                "total_chunks": total_chunks
            }
        except Exception as e:
            logger.error(f"Chunked upload assembly failed: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    return {
        "status": "uploading",
        "chunks_received": len(received_chunks),
        "total_chunks": total_chunks
    }


@router.get("/files", response_model=List[VaultFile])
async def list_vault_files(vault_type: str = "real", folder_path: str = None):
    """List all uploaded vault files, optionally filtered by folder"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    return service.list_files(user_id, vault_type, folder_path)


@router.get("/files-paginated")
async def get_vault_files_paginated(
    vault_type: str = "real",
    folder_path: str = "/",
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "name"
):
    """
    Get vault files with pagination

    Args:
        vault_type: 'real' or 'decoy'
        folder_path: Folder path to list files from
        page: Page number (1-indexed)
        page_size: Number of files per page
        sort_by: Sort field ('name', 'date', or 'size')

    Returns:
        Paginated list of files with metadata
    """
    user_id = "default_user"
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")

    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="page_size must be between 1 and 100")

    # Calculate offset
    offset = (page - 1) * page_size

    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Get total count
        cursor.execute("""
            SELECT COUNT(*) FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
        """, (user_id, vault_type, folder_path))
        total_count = cursor.fetchone()[0]

        # Get paginated files
        order_clause = {
            'name': 'filename ASC',
            'date': 'created_at DESC',
            'size': 'file_size DESC'
        }.get(sort_by, 'filename ASC')

        cursor.execute(f"""
            SELECT * FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        """, (user_id, vault_type, folder_path, page_size, offset))

        files = []
        for row in cursor.fetchall():
            files.append({
                "id": row[0],
                "user_id": row[1],
                "vault_type": row[2],
                "filename": row[3],
                "file_size": row[4],
                "mime_type": row[5],
                "encrypted_path": row[6],
                "folder_path": row[7],
                "created_at": row[8],
                "updated_at": row[9]
            })

        total_pages = (total_count + page_size - 1) // page_size

        return {
            "files": files,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    finally:
        conn.close()


@router.get("/files/{file_id}/thumbnail")
async def get_file_thumbnail(
    file_id: str,
    vault_type: str = "real",
    vault_passphrase: str = ""
):
    """
    Get thumbnail for image files

    Decrypts the file and generates a thumbnail on the fly.
    Returns 200x200 JPEG thumbnail.
    """
    from fastapi.responses import Response

    user_id = "default_user"
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if not vault_passphrase:
        raise HTTPException(status_code=400, detail="vault_passphrase is required")

    # Get file metadata
    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM vault_files
        WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
    """, (file_id, user_id, vault_type))

    file_row = cursor.fetchone()
    conn.close()

    if not file_row:
        raise HTTPException(status_code=404, detail="File not found")

    # Check if file is an image
    if not file_row['mime_type'].startswith('image/'):
        raise HTTPException(status_code=400, detail="File is not an image")

    # Read and decrypt file
    encrypted_path = file_row['encrypted_path']
    file_path = service.files_path / encrypted_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File data not found")

    with open(file_path, 'rb') as f:
        encrypted_data = f.read()

    # Decrypt file
    encryption_key, _ = service._get_encryption_key(vault_passphrase)
    fernet = Fernet(encryption_key)

    try:
        decrypted_data = fernet.decrypt(encrypted_data)
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise HTTPException(status_code=400, detail="Decryption failed - invalid passphrase?")

    # Generate thumbnail
    thumbnail = service.generate_thumbnail(decrypted_data, max_size=(200, 200))

    if not thumbnail:
        raise HTTPException(status_code=500, detail="Thumbnail generation failed")

    return Response(content=thumbnail, media_type="image/jpeg")


@router.get("/files/{file_id}/download")
async def download_vault_file(
    file_id: str,
    vault_type: str = "real",
    vault_passphrase: str = ""
):
    """Download and decrypt a vault file"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if not vault_passphrase:
        raise HTTPException(status_code=400, detail="vault_passphrase is required")

    service = get_vault_service()

    # Get file metadata
    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM vault_files
        WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
    """, (file_id, user_id, vault_type))

    file_row = cursor.fetchone()
    conn.close()

    if not file_row:
        raise HTTPException(status_code=404, detail="File not found")

    # Read encrypted file from disk
    encrypted_file_path = Path(file_row['encrypted_path'])

    if not encrypted_file_path.exists():
        raise HTTPException(status_code=404, detail="Encrypted file not found on disk")

    try:
        with open(encrypted_file_path, 'rb') as f:
            encrypted_data = f.read()

        # Decrypt the file
        key, _ = service._get_encryption_key(vault_passphrase)
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data)

        # Write decrypted data to temporary file
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_row['filename']}")
        temp_file.write(decrypted_data)
        temp_file.close()

        return FileResponse(
            path=temp_file.name,
            filename=file_row['filename'],
            media_type=file_row['mime_type'] or 'application/octet-stream',
            headers={"Content-Disposition": f"attachment; filename=\"{file_row['filename']}\""}
        )

    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to decrypt file: {str(e)}")


@router.post("/folders", response_model=VaultFolder)
async def create_vault_folder(
    folder_name: str = Form(...),
    vault_type: str = Form(default="real"),
    parent_path: str = Form(default="/")
):
    """Create a new folder in the vault"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    try:
        folder = service.create_folder(user_id, vault_type, folder_name, parent_path)
        return folder
    except Exception as e:
        logger.error(f"Folder creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Folder creation failed: {str(e)}")


@router.get("/folders", response_model=List[VaultFolder])
async def list_vault_folders(vault_type: str = "real", parent_path: str = None):
    """List folders, optionally filtered by parent path"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    return service.list_folders(user_id, vault_type, parent_path)


@router.delete("/folders")
async def delete_vault_folder(folder_path: str, vault_type: str = "real"):
    """Delete a folder (and all its contents)"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    success = service.delete_folder(user_id, vault_type, folder_path)

    if not success:
        raise HTTPException(status_code=404, detail="Folder not found")

    return {"success": True, "message": "Folder deleted"}


@router.delete("/files/{file_id}")
async def delete_vault_file(file_id: str, vault_type: str = "real"):
    """Delete a file"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    success = service.delete_file(user_id, vault_type, file_id)

    if not success:
        raise HTTPException(status_code=404, detail="File not found")

    # Broadcast file deletion event
    await manager.broadcast_file_event(
        event_type="file_deleted",
        file_data={"id": file_id},
        vault_type=vault_type,
        user_id=user_id
    )

    return {"success": True, "message": "File deleted"}


@router.put("/files/{file_id}/rename")
async def rename_vault_file(file_id: str, new_filename: str, vault_type: str = "real"):
    """Rename a file"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if not new_filename or not new_filename.strip():
        raise HTTPException(status_code=400, detail="new_filename is required")

    service = get_vault_service()
    success = service.rename_file(user_id, vault_type, file_id, new_filename.strip())

    if not success:
        raise HTTPException(status_code=404, detail="File not found")

    # Broadcast file rename event
    await manager.broadcast_file_event(
        event_type="file_renamed",
        file_data={"id": file_id, "new_filename": new_filename.strip()},
        vault_type=vault_type,
        user_id=user_id
    )

    return {"success": True, "message": "File renamed", "new_filename": new_filename.strip()}


@router.put("/files/{file_id}/move")
async def move_vault_file(file_id: str, new_folder_path: str, vault_type: str = "real"):
    """Move a file to a different folder"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    success = service.move_file(user_id, vault_type, file_id, new_folder_path)

    if not success:
        raise HTTPException(status_code=404, detail="File not found")

    # Broadcast file move event
    await manager.broadcast_file_event(
        event_type="file_moved",
        file_data={"id": file_id, "new_folder_path": new_folder_path},
        vault_type=vault_type,
        user_id=user_id
    )

    return {"success": True, "message": "File moved", "new_folder_path": new_folder_path}


@router.put("/folders/rename")
async def rename_vault_folder(old_path: str, new_name: str, vault_type: str = "real"):
    """Rename a folder"""
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if not new_name or not new_name.strip():
        raise HTTPException(status_code=400, detail="new_name is required")

    service = get_vault_service()
    success = service.rename_folder(user_id, vault_type, old_path, new_name.strip())

    if not success:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Calculate new path for response
    parent_path = old_path.rsplit('/', 1)[0] if old_path.count('/') > 0 else '/'
    new_path = f"{parent_path}/{new_name.strip()}" if parent_path != '/' else f"/{new_name.strip()}"

    return {"success": True, "message": "Folder renamed", "new_path": new_path}


@router.get("/health")
async def vault_health():
    """Health check for vault service"""
    return {
        "vault_service": "operational",
        "encryption": "server-side with Fernet (AES-128)",
        "storage": "SQLite + encrypted files on disk",
        "file_uploads": "supported"
    }


# ===== Tags Endpoints =====

@router.post("/files/{file_id}/tags")
async def add_file_tag(
    file_id: str,
    tag_name: str = Form(...),
    tag_color: str = Form("#3B82F6"),
    vault_type: str = Form("real")
):
    """Add a tag to a file"""
    service = get_vault_service()
    user_id = "default_user"  # TODO: Get from auth

    try:
        result = service.add_tag_to_file(user_id, vault_type, file_id, tag_name, tag_color)
        return result
    except Exception as e:
        logger.error(f"Failed to add tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/tags/{tag_name}")
async def remove_file_tag(
    file_id: str,
    tag_name: str,
    vault_type: str = "real"
):
    """Remove a tag from a file"""
    service = get_vault_service()
    user_id = "default_user"  # TODO: Get from auth

    try:
        success = service.remove_tag_from_file(user_id, vault_type, file_id, tag_name)
        if not success:
            raise HTTPException(status_code=404, detail="Tag not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/tags")
async def get_file_tags(
    file_id: str,
    vault_type: str = "real"
):
    """Get all tags for a file"""
    service = get_vault_service()
    user_id = "default_user"  # TODO: Get from auth

    try:
        tags = service.get_file_tags(user_id, vault_type, file_id)
        return {"tags": tags}
    except Exception as e:
        logger.error(f"Failed to get tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Favorites Endpoints =====

@router.post("/files/{file_id}/favorite")
async def add_favorite_file(
    file_id: str,
    vault_type: str = Form("real")
):
    """Add file to favorites"""
    service = get_vault_service()
    user_id = "default_user"  # TODO: Get from auth

    try:
        result = service.add_favorite(user_id, vault_type, file_id)
        return result
    except Exception as e:
        logger.error(f"Failed to add favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/favorite")
async def remove_favorite_file(
    file_id: str,
    vault_type: str = "real"
):
    """Remove file from favorites"""
    service = get_vault_service()
    user_id = "default_user"  # TODO: Get from auth

    try:
        success = service.remove_favorite(user_id, vault_type, file_id)
        if not success:
            raise HTTPException(status_code=404, detail="Favorite not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favorites")
async def get_favorite_files(vault_type: str = "real"):
    """Get list of favorite file IDs"""
    service = get_vault_service()
    user_id = "default_user"  # TODO: Get from auth

    try:
        favorites = service.get_favorites(user_id, vault_type)
        return {"favorites": favorites}
    except Exception as e:
        logger.error(f"Failed to get favorites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Recent Files Endpoints =====

@router.post("/files/{file_id}/log-access")
async def log_file_access_endpoint(
    file_id: str,
    access_type: str = Form("view"),
    vault_type: str = Form("real")
):
    """Log file access (for recent files tracking)"""
    service = get_vault_service()
    user_id = "default_user"  # TODO: Get from auth

    try:
        service.log_file_access(user_id, vault_type, file_id, access_type)
        return {"success": True}
    except Exception as e:
        logger.warning(f"Failed to log file access: {e}")
        return {"success": False}


@router.get("/recent-files")
async def get_recent_files_endpoint(
    vault_type: str = "real",
    limit: int = 10
):
    """Get recently accessed files"""
    service = get_vault_service()
    user_id = "default_user"  # TODO: Get from auth

    try:
        recent = service.get_recent_files(user_id, vault_type, limit)
        return {"recent_files": recent}
    except Exception as e:
        logger.error(f"Failed to get recent files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Storage Statistics Endpoint =====

@router.get("/storage-stats")
async def get_storage_statistics(vault_type: str = "real"):
    """Get storage statistics and analytics"""
    service = get_vault_service()
    user_id = "default_user"  # TODO: Get from auth

    try:
        stats = service.get_storage_stats(user_id, vault_type)
        return stats
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Secure Deletion Endpoint =====

@router.delete("/files/{file_id}/secure")
async def secure_delete_file_endpoint(
    file_id: str,
    vault_type: str = "real"
):
    """Securely delete a file (overwrites with random data before deletion)"""
    service = get_vault_service()
    user_id = "default_user"  # TODO: Get from auth

    try:
        success = service.secure_delete_file(user_id, vault_type, file_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
        return {"success": True, "message": "File securely deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to securely delete file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: File Versioning Endpoints =====

@router.get("/files/{file_id}/versions")
async def get_file_versions_endpoint(
    file_id: str,
    vault_type: str = "real"
):
    """Get all versions of a file"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        versions = service.get_file_versions(user_id, vault_type, file_id)
        return {"versions": versions}
    except Exception as e:
        logger.error(f"Failed to get file versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/{file_id}/versions/{version_id}/restore")
async def restore_file_version_endpoint(
    file_id: str,
    version_id: str,
    vault_type: str = Form("real")
):
    """Restore a file to a previous version"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        result = service.restore_file_version(user_id, vault_type, file_id, version_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore file version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/versions/{version_id}")
async def delete_file_version_endpoint(
    file_id: str,
    version_id: str,
    vault_type: str = "real"
):
    """Delete a specific file version"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        success = service.delete_file_version(user_id, vault_type, version_id)
        if not success:
            raise HTTPException(status_code=404, detail="Version not found")
        return {"success": True, "message": "Version deleted"}
    except Exception as e:
        logger.error(f"Failed to delete file version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: Trash/Recycle Bin Endpoints =====

@router.post("/files/{file_id}/trash")
async def move_to_trash_endpoint(
    file_id: str,
    vault_type: str = Form("real")
):
    """Move a file to trash (soft delete)"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        result = service.move_to_trash(user_id, vault_type, file_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to move file to trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/{file_id}/restore")
async def restore_from_trash_endpoint(
    file_id: str,
    vault_type: str = Form("real")
):
    """Restore a file from trash"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        result = service.restore_from_trash(user_id, vault_type, file_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore file from trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trash")
async def get_trash_files_endpoint(vault_type: str = "real"):
    """Get all files in trash"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        trash_files = service.get_trash_files(user_id, vault_type)
        return {"trash_files": trash_files}
    except Exception as e:
        logger.error(f"Failed to get trash files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/trash/empty")
async def empty_trash_endpoint(vault_type: str = "real"):
    """Permanently delete all files in trash"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        result = service.empty_trash(user_id, vault_type)
        return result
    except Exception as e:
        logger.error(f"Failed to empty trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: Advanced Search Endpoints =====

@router.get("/search")
async def search_files_endpoint(
    vault_type: str = "real",
    query: str = None,
    mime_type: str = None,
    tags: str = None,  # Comma-separated tags
    date_from: str = None,
    date_to: str = None,
    min_size: int = None,
    max_size: int = None,
    folder_path: str = None
):
    """Advanced file search with multiple filters"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        # Parse tags if provided
        tags_list = tags.split(",") if tags else None

        results = service.search_files(
            user_id, vault_type, query, mime_type, tags_list,
            date_from, date_to, min_size, max_size, folder_path
        )
        return {"results": results}
    except Exception as e:
        logger.error(f"Failed to search files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: File Sharing Endpoints =====

@router.post("/files/{file_id}/share")
async def create_share_link_endpoint(
    file_id: str,
    vault_type: str = Form("real"),
    password: str = Form(None),
    expires_at: str = Form(None),
    max_downloads: int = Form(None),
    permissions: str = Form("download")
):
    """Create a shareable link for a file"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        result = service.create_share_link(
            user_id, vault_type, file_id, password,
            expires_at, max_downloads, permissions
        )
        return result
    except Exception as e:
        logger.error(f"Failed to create share link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/shares")
async def get_file_shares_endpoint(
    file_id: str,
    vault_type: str = "real"
):
    """Get all share links for a file"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        shares = service.get_file_shares(user_id, vault_type, file_id)
        return {"shares": shares}
    except Exception as e:
        logger.error(f"Failed to get file shares: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/shares/{share_id}")
async def revoke_share_link_endpoint(
    share_id: str,
    vault_type: str = "real"
):
    """Revoke a share link"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        success = service.revoke_share_link(user_id, vault_type, share_id)
        if not success:
            raise HTTPException(status_code=404, detail="Share link not found")
        return {"success": True, "message": "Share link revoked"}
    except Exception as e:
        logger.error(f"Failed to revoke share link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/share/{share_token}")
async def access_share_link_endpoint(
    share_token: str,
    password: str = None
):
    """Access a shared file via share token"""
    service = get_vault_service()

    try:
        # Get share details
        share_info = service.get_share_link(share_token)

        # Verify password if required
        if share_info["requires_password"]:
            if not password:
                raise HTTPException(status_code=401, detail="Password required")
            if not service.verify_share_password(share_token, password):
                raise HTTPException(status_code=401, detail="Invalid password")

        return share_info
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to access share link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: Audit Logs Endpoints =====

@router.get("/audit-logs")
async def get_audit_logs_endpoint(
    vault_type: str = None,
    action: str = None,
    resource_type: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100
):
    """Get audit logs with filters"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        logs = service.get_audit_logs(
            user_id, vault_type, action, resource_type,
            date_from, date_to, limit
        )
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: File Comments Endpoints =====

@router.post("/files/{file_id}/comments")
async def add_file_comment_endpoint(
    file_id: str,
    comment_text: str = Form(...),
    vault_type: str = Form("real")
):
    """Add a comment to a file"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        result = service.add_file_comment(user_id, vault_type, file_id, comment_text)
        return result
    except Exception as e:
        logger.error(f"Failed to add comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/comments")
async def get_file_comments_endpoint(
    file_id: str,
    vault_type: str = "real"
):
    """Get all comments for a file"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        comments = service.get_file_comments(user_id, vault_type, file_id)
        return {"comments": comments}
    except Exception as e:
        logger.error(f"Failed to get comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/comments/{comment_id}")
async def update_file_comment_endpoint(
    comment_id: str,
    comment_text: str = Form(...),
    vault_type: str = Form("real")
):
    """Update a comment"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        result = service.update_file_comment(user_id, vault_type, comment_id, comment_text)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/comments/{comment_id}")
async def delete_file_comment_endpoint(
    comment_id: str,
    vault_type: str = "real"
):
    """Delete a comment"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        success = service.delete_file_comment(user_id, vault_type, comment_id)
        if not success:
            raise HTTPException(status_code=404, detail="Comment not found")
        return {"success": True, "message": "Comment deleted"}
    except Exception as e:
        logger.error(f"Failed to delete comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: File Metadata Endpoints =====

@router.post("/files/{file_id}/metadata")
async def set_file_metadata_endpoint(
    file_id: str,
    key: str = Form(...),
    value: str = Form(...),
    vault_type: str = Form("real")
):
    """Set custom metadata for a file"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        result = service.set_file_metadata(user_id, vault_type, file_id, key, value)
        return result
    except Exception as e:
        logger.error(f"Failed to set metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/metadata")
async def get_file_metadata_endpoint(
    file_id: str,
    vault_type: str = "real"
):
    """Get all metadata for a file"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        metadata = service.get_file_metadata(user_id, vault_type, file_id)
        return {"metadata": metadata}
    except Exception as e:
        logger.error(f"Failed to get metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: Organization Features Endpoints =====

@router.post("/files/{file_id}/pin")
async def pin_file_endpoint(
    file_id: str,
    pin_order: int = Form(0),
    vault_type: str = Form("real")
):
    """Pin a file for quick access"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        result = service.pin_file(user_id, vault_type, file_id, pin_order)
        return result
    except Exception as e:
        logger.error(f"Failed to pin file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/pin")
async def unpin_file_endpoint(
    file_id: str,
    vault_type: str = "real"
):
    """Unpin a file"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        success = service.unpin_file(user_id, vault_type, file_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not pinned")
        return {"success": True, "message": "File unpinned"}
    except Exception as e:
        logger.error(f"Failed to unpin file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pinned-files")
async def get_pinned_files_endpoint(vault_type: str = "real"):
    """Get all pinned files"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        pinned = service.get_pinned_files(user_id, vault_type)
        return {"pinned_files": pinned}
    except Exception as e:
        logger.error(f"Failed to get pinned files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/folders/{folder_id}/color")
async def set_folder_color_endpoint(
    folder_id: str,
    color: str = Form(...),
    vault_type: str = Form("real")
):
    """Set color for a folder"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        result = service.set_folder_color(user_id, vault_type, folder_id, color)
        return result
    except Exception as e:
        logger.error(f"Failed to set folder color: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folder-colors")
async def get_folder_colors_endpoint(vault_type: str = "real"):
    """Get all folder colors"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        colors = service.get_folder_colors(user_id, vault_type)
        return {"folder_colors": colors}
    except Exception as e:
        logger.error(f"Failed to get folder colors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: Backup & Export Endpoints =====

@router.get("/export")
async def export_vault_data_endpoint(vault_type: str = "real"):
    """Export vault metadata for backup"""
    service = get_vault_service()
    user_id = "default_user"

    try:
        export_data = service.export_vault_data(user_id, vault_type)
        return export_data
    except Exception as e:
        logger.error(f"Failed to export vault data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 5: Analytics & Insights =====

@router.get("/analytics/storage-trends")
async def get_storage_trends(
    vault_type: str = "real",
    days: int = 30
):
    """
    Get storage usage trends over time

    Args:
        vault_type: 'real' or 'decoy'
        days: Number of days to look back (default: 30)

    Returns:
        Daily storage growth data
    """
    user_id = "default_user"
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")

    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Daily storage growth
        cursor.execute("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as files_added,
                SUM(file_size) as bytes_added
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
              AND created_at >= datetime('now', '-' || ? || ' days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, (user_id, vault_type, days))

        trends = []
        for row in cursor.fetchall():
            trends.append({
                "date": row[0],
                "files_added": row[1],
                "bytes_added": row[2] or 0
            })

        # Get current totals
        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(file_size), 0)
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
        """, (user_id, vault_type))

        total_row = cursor.fetchone()
        total_files = total_row[0]
        total_bytes = total_row[1]

        return {
            "trends": trends,
            "total_files": total_files,
            "total_bytes": total_bytes,
            "days": days
        }
    finally:
        conn.close()


@router.get("/analytics/access-patterns")
async def get_access_patterns(vault_type: str = "real", limit: int = 10):
    """
    Get file access patterns and most accessed files

    Args:
        vault_type: 'real' or 'decoy'
        limit: Number of top files to return

    Returns:
        Most accessed files and access statistics
    """
    user_id = "default_user"
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Most accessed files
        cursor.execute("""
            SELECT
                f.id,
                f.filename,
                f.mime_type,
                f.file_size,
                COUNT(a.id) as access_count,
                MAX(a.accessed_at) as last_accessed
            FROM vault_files f
            LEFT JOIN vault_file_access_logs a ON f.id = a.file_id
            WHERE f.user_id = ? AND f.vault_type = ? AND f.is_deleted = 0
            GROUP BY f.id
            ORDER BY access_count DESC
            LIMIT ?
        """, (user_id, vault_type, limit))

        most_accessed = []
        for row in cursor.fetchall():
            most_accessed.append({
                "id": row[0],
                "filename": row[1],
                "mime_type": row[2],
                "file_size": row[3],
                "access_count": row[4],
                "last_accessed": row[5]
            })

        # Access by type
        cursor.execute("""
            SELECT
                access_type,
                COUNT(*) as count
            FROM vault_file_access_logs
            WHERE user_id = ? AND vault_type = ?
            GROUP BY access_type
        """, (user_id, vault_type))

        access_by_type = {}
        for row in cursor.fetchall():
            access_by_type[row[0]] = row[1]

        # Recent access activity (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*)
            FROM vault_file_access_logs
            WHERE user_id = ? AND vault_type = ?
              AND accessed_at >= datetime('now', '-1 day')
        """, (user_id, vault_type))

        recent_access_count = cursor.fetchone()[0]

        return {
            "most_accessed": most_accessed,
            "access_by_type": access_by_type,
            "recent_access_24h": recent_access_count
        }
    finally:
        conn.close()


@router.get("/analytics/activity-timeline")
async def get_activity_timeline(
    vault_type: str = "real",
    hours: int = 24,
    limit: int = 50
):
    """
    Get recent activity timeline

    Args:
        vault_type: 'real' or 'decoy'
        hours: Hours to look back
        limit: Max activities to return

    Returns:
        Recent activity events
    """
    user_id = "default_user"
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Get recent audit logs
        cursor.execute("""
            SELECT
                action,
                resource_type,
                resource_id,
                details,
                created_at
            FROM vault_audit_logs
            WHERE user_id = ? AND vault_type = ?
              AND created_at >= datetime('now', '-' || ? || ' hours')
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, vault_type, hours, limit))

        activities = []
        for row in cursor.fetchall():
            activities.append({
                "action": row[0],
                "resource_type": row[1],
                "resource_id": row[2],
                "details": row[3],
                "timestamp": row[4]
            })

        # Get activity summary
        cursor.execute("""
            SELECT
                action,
                COUNT(*) as count
            FROM vault_audit_logs
            WHERE user_id = ? AND vault_type = ?
              AND created_at >= datetime('now', '-' || ? || ' hours')
            GROUP BY action
        """, (user_id, vault_type, hours))

        action_summary = {}
        for row in cursor.fetchall():
            action_summary[row[0]] = row[1]

        return {
            "activities": activities,
            "action_summary": action_summary,
            "hours": hours,
            "total_activities": len(activities)
        }
    finally:
        conn.close()


# ===== Day 5: Real-Time Collaboration (WebSocket) =====

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    vault_type: str = "real",
    token: str = None  # Auth token from query param
):
    """
    WebSocket endpoint for real-time vault updates

    Supports:
    - Real-time file upload/delete/update notifications
    - User presence tracking
    - Activity broadcasting

    Security: Requires valid JWT token for authentication
    """
    # Verify authentication before accepting connection
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    try:
        # Verify JWT token
        import jwt
        from auth_middleware import JWT_SECRET, JWT_ALGORITHM
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        authenticated_user_id = payload.get("user_id")

        # Verify user_id matches token
        if authenticated_user_id != user_id:
            await websocket.close(code=1008, reason="User ID mismatch")
            return
    except jwt.ExpiredSignatureError:
        await websocket.close(code=1008, reason="Token expired")
        return
    except jwt.InvalidTokenError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    await manager.connect(websocket, user_id, vault_type)

    try:
        while True:
            # Receive messages for keepalive and client-initiated events
            data = await websocket.receive_text()

            # Parse incoming message
            try:
                import json
                message = json.loads(data)

                # Handle different message types
                if message.get("type") == "ping":
                    # Respond to keepalive ping
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})

                elif message.get("type") == "activity_update":
                    # Update user's last activity timestamp
                    if user_id in manager.user_presence:
                        manager.user_presence[user_id]["last_activity"] = datetime.utcnow().isoformat()

                else:
                    # Echo unknown messages for debugging
                    await websocket.send_json({"type": "echo", "received": message})

            except json.JSONDecodeError:
                # If not JSON, treat as simple keepalive string
                await websocket.send_text(f"Message received: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id, vault_type)
        logger.info(f"WebSocket disconnected: user={user_id}, vault={vault_type}")


@router.get("/ws/online-users")
async def get_online_users(vault_type: Optional[str] = None):
    """Get list of currently online users"""
    return {
        "online_users": manager.get_online_users(vault_type),
        "total_connections": manager.get_connection_count(),
        "vault_type": vault_type
    }


# ===== Phase B & G: User Management & Multi-User Features =====

@router.post("/users/register")
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    """Register a new user"""
    service = get_vault_service()

    # Generate user ID
    import uuid
    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Hash password with PBKDF2
    password_key, salt = service._get_encryption_key(password)
    password_hash = base64.b64encode(password_key).decode('utf-8')
    salt_b64 = base64.b64encode(salt).decode('utf-8')

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO vault_users (user_id, username, email, password_hash, salt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, email, password_hash, salt_b64, now, now))

        conn.commit()

        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "created_at": now
        }
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"User already exists: {str(e)}")
    finally:
        conn.close()


@router.post("/users/login")
async def login_user(
    username: str = Form(...),
    password: str = Form(...)
):
    """Login user and return user info"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM vault_users WHERE username = ? AND is_active = 1
        """, (username,))

        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Verify password
        stored_salt = base64.b64decode(user['salt'])
        password_key, _ = service._get_encryption_key(password, stored_salt)
        password_hash = base64.b64encode(password_key).decode('utf-8')

        if password_hash != user['password_hash']:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Update last login
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            UPDATE vault_users SET last_login = ? WHERE user_id = ?
        """, (now, user['user_id']))
        conn.commit()

        return {
            "user_id": user['user_id'],
            "username": user['username'],
            "email": user['email'],
            "last_login": now
        }
    finally:
        conn.close()


@router.post("/acl/grant-file-permission")
async def grant_file_permission(
    file_id: str = Form(...),
    user_id: str = Form(...),
    permission: str = Form(...),
    granted_by: str = Form(...),
    expires_at: Optional[str] = Form(None)
):
    """Grant permission to a user for a specific file"""
    service = get_vault_service()

    if permission not in ['read', 'write', 'delete', 'share']:
        raise HTTPException(status_code=400, detail="Invalid permission type")

    acl_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO vault_file_acl (id, file_id, user_id, permission, granted_by, granted_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (acl_id, file_id, user_id, permission, granted_by, now, expires_at))

        conn.commit()

        return {
            "acl_id": acl_id,
            "file_id": file_id,
            "user_id": user_id,
            "permission": permission,
            "granted_at": now
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Permission already exists")
    finally:
        conn.close()


@router.post("/acl/check-permission")
async def check_file_permission(
    file_id: str = Form(...),
    user_id: str = Form(...),
    permission: str = Form(...)
):
    """Check if user has specific permission for a file"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        # Check for unexpired permission
        cursor.execute("""
            SELECT * FROM vault_file_acl
            WHERE file_id = ? AND user_id = ? AND permission = ?
              AND (expires_at IS NULL OR expires_at > datetime('now'))
        """, (file_id, user_id, permission))

        has_permission = cursor.fetchone() is not None

        return {
            "file_id": file_id,
            "user_id": user_id,
            "permission": permission,
            "has_permission": has_permission
        }
    finally:
        conn.close()


@router.get("/acl/file-permissions/{file_id}")
async def get_file_permissions(file_id: str):
    """Get all permissions for a file"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT acl.*, u.username
            FROM vault_file_acl acl
            JOIN vault_users u ON acl.user_id = u.user_id
            WHERE acl.file_id = ?
              AND (acl.expires_at IS NULL OR acl.expires_at > datetime('now'))
        """, (file_id,))

        permissions = []
        for row in cursor.fetchall():
            permissions.append({
                "acl_id": row['id'],
                "user_id": row['user_id'],
                "username": row['username'],
                "permission": row['permission'],
                "granted_by": row['granted_by'],
                "granted_at": row['granted_at'],
                "expires_at": row['expires_at']
            })

        return {"file_id": file_id, "permissions": permissions}
    finally:
        conn.close()


@router.delete("/acl/revoke-permission/{acl_id}")
async def revoke_permission(acl_id: str):
    """Revoke a specific permission"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM vault_file_acl WHERE id = ?", (acl_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Permission not found")

        return {"success": True, "acl_id": acl_id}
    finally:
        conn.close()


@router.post("/sharing/create-invitation")
async def create_sharing_invitation(
    resource_type: str = Form(...),
    resource_id: str = Form(...),
    from_user_id: str = Form(...),
    to_user_email: str = Form(...),
    permission: str = Form(...),
    expires_in_days: int = Form(7)
):
    """Create a sharing invitation"""
    service = get_vault_service()

    if resource_type not in ['file', 'folder']:
        raise HTTPException(status_code=400, detail="Invalid resource type")

    if permission not in ['read', 'write', 'delete', 'share']:
        raise HTTPException(status_code=400, detail="Invalid permission")

    import secrets
    invitation_id = str(uuid.uuid4())
    invitation_token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires_at = (now + timedelta(days=expires_in_days)).isoformat()
    now_iso = now.isoformat()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO vault_share_invitations
            (id, resource_type, resource_id, from_user_id, to_user_email, permission,
             invitation_token, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (invitation_id, resource_type, resource_id, from_user_id, to_user_email,
              permission, invitation_token, now_iso, expires_at))

        conn.commit()

        return {
            "invitation_id": invitation_id,
            "invitation_token": invitation_token,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "to_user_email": to_user_email,
            "permission": permission,
            "expires_at": expires_at,
            "share_url": f"/api/v1/vault/sharing/accept/{invitation_token}"
        }
    finally:
        conn.close()


@router.post("/sharing/accept/{invitation_token}")
async def accept_sharing_invitation(invitation_token: str, user_id: str = Form(...)):
    """Accept a sharing invitation"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Get invitation
        cursor.execute("""
            SELECT * FROM vault_share_invitations
            WHERE invitation_token = ? AND status = 'pending'
              AND expires_at > datetime('now')
        """, (invitation_token,))

        invitation = cursor.fetchone()

        if not invitation:
            raise HTTPException(status_code=404, detail="Invalid or expired invitation")

        # Create ACL entry
        acl_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        if invitation['resource_type'] == 'file':
            cursor.execute("""
                INSERT INTO vault_file_acl (id, file_id, user_id, permission, granted_by, granted_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (acl_id, invitation['resource_id'], user_id, invitation['permission'],
                  invitation['from_user_id'], now))

        # Update invitation status
        cursor.execute("""
            UPDATE vault_share_invitations
            SET status = 'accepted', accepted_at = ?
            WHERE id = ?
        """, (now, invitation['id']))

        conn.commit()

        return {
            "success": True,
            "resource_type": invitation['resource_type'],
            "resource_id": invitation['resource_id'],
            "permission": invitation['permission']
        }
    finally:
        conn.close()


@router.post("/sharing/decline/{invitation_token}")
async def decline_sharing_invitation(invitation_token: str):
    """Decline a sharing invitation"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE vault_share_invitations
            SET status = 'declined'
            WHERE invitation_token = ? AND status = 'pending'
        """, (invitation_token,))

        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Invitation not found")

        return {"success": True}
    finally:
        conn.close()


@router.get("/sharing/my-invitations")
async def get_my_invitations(user_email: str):
    """Get all pending invitations for a user"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT i.*, u.username as from_username
            FROM vault_share_invitations i
            JOIN vault_users u ON i.from_user_id = u.user_id
            WHERE i.to_user_email = ? AND i.status = 'pending'
              AND i.expires_at > datetime('now')
            ORDER BY i.created_at DESC
        """, (user_email,))

        invitations = []
        for row in cursor.fetchall():
            invitations.append({
                "invitation_id": row['id'],
                "invitation_token": row['invitation_token'],
                "resource_type": row['resource_type'],
                "resource_id": row['resource_id'],
                "from_username": row['from_username'],
                "permission": row['permission'],
                "created_at": row['created_at'],
                "expires_at": row['expires_at']
            })

        return {"invitations": invitations}
    finally:
        conn.close()


# ===== Phase 3: File Organization Automation =====

@router.post("/automation/create-rule")
async def create_organization_rule(
    user_id: str = Form(...),
    vault_type: str = Form(...),
    rule_name: str = Form(...),
    rule_type: str = Form(...),
    condition_value: str = Form(...),
    action_type: str = Form(...),
    action_value: str = Form(...),
    priority: int = Form(0)
):
    """Create a file organization rule"""
    service = get_vault_service()
    
    valid_rule_types = ['mime_type', 'file_extension', 'file_size', 'filename_pattern', 'date']
    valid_action_types = ['move_to_folder', 'add_tag', 'set_color']
    
    if rule_type not in valid_rule_types:
        raise HTTPException(status_code=400, detail=f"Invalid rule_type. Must be one of: {valid_rule_types}")
    
    if action_type not in valid_action_types:
        raise HTTPException(status_code=400, detail=f"Invalid action_type. Must be one of: {valid_action_types}")
    
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO vault_organization_rules
            (id, user_id, vault_type, rule_name, rule_type, condition_value,
             action_type, action_value, priority, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (rule_id, user_id, vault_type, rule_name, rule_type, condition_value,
              action_type, action_value, priority, now))
        
        conn.commit()
        
        return {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "rule_type": rule_type,
            "action_type": action_type,
            "is_enabled": True,
            "created_at": now
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Rule with this name already exists")
    finally:
        conn.close()


@router.get("/automation/rules")
async def get_organization_rules(user_id: str, vault_type: str = "real"):
    """Get all organization rules for a user"""
    service = get_vault_service()
    
    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM vault_organization_rules
            WHERE user_id = ? AND vault_type = ?
            ORDER BY priority DESC, created_at ASC
        """, (user_id, vault_type))
        
        rules = []
        for row in cursor.fetchall():
            rules.append({
                "rule_id": row['id'],
                "rule_name": row['rule_name'],
                "rule_type": row['rule_type'],
                "condition_value": row['condition_value'],
                "action_type": row['action_type'],
                "action_value": row['action_value'],
                "is_enabled": bool(row['is_enabled']),
                "priority": row['priority'],
                "files_processed": row['files_processed'],
                "last_run": row['last_run'],
                "created_at": row['created_at']
            })
        
        return {"rules": rules}
    finally:
        conn.close()


@router.post("/automation/run-rules")
async def run_organization_rules(user_id: str = Form(...), vault_type: str = Form("real")):
    """Run all enabled organization rules on existing files"""
    service = get_vault_service()
    
    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get enabled rules
        cursor.execute("""
            SELECT * FROM vault_organization_rules
            WHERE user_id = ? AND vault_type = ? AND is_enabled = 1
            ORDER BY priority DESC
        """, (user_id, vault_type))
        
        rules = cursor.fetchall()
        total_processed = 0
        results = []
        
        for rule in rules:
            files_matched = 0
            
            # Get all files for this user/vault
            cursor.execute("""
                SELECT * FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
            """, (user_id, vault_type))
            
            files = cursor.fetchall()
            
            for file in files:
                matched = False
                
                # Check rule condition
                if rule['rule_type'] == 'mime_type':
                    matched = file['mime_type'].startswith(rule['condition_value'])
                
                elif rule['rule_type'] == 'file_extension':
                    matched = file['filename'].endswith(rule['condition_value'])
                
                elif rule['rule_type'] == 'file_size':
                    # Format: ">1000000" for files larger than 1MB
                    operator = rule['condition_value'][0]
                    size_limit = int(rule['condition_value'][1:])
                    if operator == '>':
                        matched = file['file_size'] > size_limit
                    elif operator == '<':
                        matched = file['file_size'] < size_limit
                
                elif rule['rule_type'] == 'filename_pattern':
                    import re
                    matched = bool(re.search(rule['condition_value'], file['filename']))
                
                # Apply action if matched
                if matched:
                    if rule['action_type'] == 'move_to_folder':
                        cursor.execute("""
                            UPDATE vault_files
                            SET folder_path = ?, updated_at = ?
                            WHERE id = ?
                        """, (rule['action_value'], datetime.utcnow().isoformat(), file['id']))
                    
                    elif rule['action_type'] == 'add_tag':
                        # Add tag if it doesn't exist
                        tag_id = str(uuid.uuid4())
                        try:
                            cursor.execute("""
                                INSERT INTO vault_file_tags
                                (id, file_id, user_id, vault_type, tag_name, created_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (tag_id, file['id'], user_id, vault_type,
                                  rule['action_value'], datetime.utcnow().isoformat()))
                        except sqlite3.IntegrityError:
                            pass  # Tag already exists
                    
                    files_matched += 1
            
            # Update rule stats
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                UPDATE vault_organization_rules
                SET last_run = ?, files_processed = files_processed + ?
                WHERE id = ?
            """, (now, files_matched, rule['id']))
            
            results.append({
                "rule_name": rule['rule_name'],
                "files_matched": files_matched
            })
            total_processed += files_matched
        
        conn.commit()
        
        return {
            "total_rules_run": len(rules),
            "total_files_processed": total_processed,
            "results": results
        }
    finally:
        conn.close()


@router.put("/automation/toggle-rule/{rule_id}")
async def toggle_rule(rule_id: str, enabled: bool = Form(...)):
    """Enable or disable a rule"""
    service = get_vault_service()
    
    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE vault_organization_rules
            SET is_enabled = ?
            WHERE id = ?
        """, (1 if enabled else 0, rule_id))
        
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return {"success": True, "rule_id": rule_id, "enabled": enabled}
    finally:
        conn.close()


@router.delete("/automation/delete-rule/{rule_id}")
async def delete_rule(rule_id: str):
    """Delete an organization rule"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM vault_organization_rules WHERE id = ?", (rule_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Rule not found")

        return {"success": True, "rule_id": rule_id}
    finally:
        conn.close()


# ===== Decoy Vault Seeding =====

@router.post("/seed-decoy-vault")
async def seed_decoy_vault_endpoint(request: Request, user_id: str = Form("default_user")):
    """
    Seed decoy vault with realistic documents for plausible deniability

    This populates the decoy vault with convincing documents like:
    - Budget spreadsheets
    - WiFi passwords
    - Shopping lists
    - Travel plans
    - Meeting notes

    Only seeds if decoy vault is empty.
    """
    try:
        from vault_seed_data import get_seeder

        seeder = get_seeder()
        result = seeder.seed_decoy_vault(user_id)

        logger.info(f"Decoy vault seeding result: {result['status']}")

        return result

    except Exception as e:
        logger.error(f"Failed to seed decoy vault: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-decoy-vault")
async def clear_decoy_vault_endpoint(request: Request, user_id: str = Form("default_user")):
    """
    Clear all decoy vault documents (for testing/re-seeding)

    WARNING: This will delete all decoy vault documents!
    Use this if you want to re-seed the decoy vault with fresh data.
    """
    try:
        from vault_seed_data import get_seeder

        seeder = get_seeder()
        result = seeder.clear_decoy_vault(user_id)

        logger.info(f"Decoy vault cleared: {result['deleted_count']} documents")

        return result

    except Exception as e:
        logger.error(f"Failed to clear decoy vault: {e}")
        raise HTTPException(status_code=500, detail=str(e))
