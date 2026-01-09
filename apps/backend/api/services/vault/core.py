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
from . import comments as comments_mod
from .schema import init_vault_schema

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

    def _init_db(self) -> None:
        """Initialize SQLite database schema (delegated to schema module)"""
        init_vault_schema(self.db_path)

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

    def log_file_access(self, user_id: str, vault_type: str, file_id: str, access_type: str = "view") -> None:
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
        return comments_mod.add_file_comment(self, user_id, vault_type, file_id, comment_text)

    def get_file_comments(self, user_id: str, vault_type: str, file_id: str) -> List[Dict[str, Any]]:
        """Get all comments for a file"""
        return comments_mod.get_file_comments(self, user_id, vault_type, file_id)

    def update_file_comment(self, user_id: str, vault_type: str, comment_id: str,
                           comment_text: str) -> Dict[str, Any]:
        """Update a comment"""
        return comments_mod.update_file_comment(self, user_id, vault_type, comment_id, comment_text)

    def delete_file_comment(self, user_id: str, vault_type: str, comment_id: str) -> bool:
        """Delete a comment"""
        return comments_mod.delete_file_comment(self, user_id, vault_type, comment_id)

    # ===== Day 4: File Metadata =====

    def set_file_metadata(self, user_id: str, vault_type: str, file_id: str,
                         key: str, value: str) -> Dict[str, Any]:
        """Set custom metadata for a file"""
        return comments_mod.set_file_metadata(self, user_id, vault_type, file_id, key, value)

    def get_file_metadata(self, user_id: str, vault_type: str, file_id: str) -> Dict[str, str]:
        """Get all metadata for a file"""
        return comments_mod.get_file_metadata(self, user_id, vault_type, file_id)

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
