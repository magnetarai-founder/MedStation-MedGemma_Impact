#!/usr/bin/env python3
"""
Vault Service for ElohimOS
Secure storage for encrypted documents with plausible deniability
Backend handles encrypted blobs only - all encryption happens client-side
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Database path
VAULT_DB_PATH = Path(".neutron_data/vault.db")


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
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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


# Singleton instance
_vault_service: Optional[VaultService] = None


def get_vault_service() -> VaultService:
    """Get singleton vault service instance"""
    global _vault_service
    if _vault_service is None:
        _vault_service = VaultService()
    return _vault_service


# ===== Router =====

router = APIRouter(prefix="/api/v1/vault", tags=["Vault"])


@router.post("/documents", response_model=VaultDocument)
async def create_vault_document(
    vault_type: str,
    document: VaultDocumentCreate
):
    """
    Store encrypted vault document

    Security: All encryption happens client-side
    Server only stores encrypted blobs
    """
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if document.vault_type != vault_type:
        raise HTTPException(status_code=400, detail="Vault type mismatch")

    service = get_vault_service()
    return service.store_document(user_id, document)


@router.get("/documents", response_model=VaultListResponse)
async def list_vault_documents(vault_type: str):
    """
    List all vault documents

    Returns encrypted blobs that must be decrypted client-side
    """
    # TODO: Get real user_id from auth middleware
    user_id = "default_user"

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


@router.get("/health")
async def vault_health():
    """Health check for vault service"""
    return {
        "vault_service": "operational",
        "encryption": "client-side (zero-knowledge)",
        "storage": "SQLite encrypted blobs"
    }
