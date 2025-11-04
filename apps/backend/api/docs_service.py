"""
Docs & Sheets Service

Foundation must be solid.
"The Lord is my rock, my firm foundation." - Psalm 18:2

This service provides collaborative document storage and syncing
for Documents, Spreadsheets, and Insights Lab.

Implements Notion-style periodic sync with conflict resolution.
"""

import os
import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

# Import user service
try:
    from user_service import get_or_create_user
except ImportError:
    from api.user_service import get_or_create_user

# Phase 2: Import permission decorators
try:
    from permission_engine import require_perm
    from auth_middleware import get_current_user
except ImportError:
    from api.permission_engine import require_perm
    from api.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

# Storage paths - use centralized config_paths
from config_paths import get_config_paths
PATHS = get_config_paths()
DOCS_DB_PATH = PATHS.data_dir / "docs.db"
DOCS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

from typing import Dict
from fastapi import Depends
from auth_middleware import get_current_user

router = APIRouter(
    prefix="/api/v1/docs",
    tags=["Docs"]
    # Auth handled per-endpoint to access user_id
)


# ===== Models =====

class DocumentCreate(BaseModel):
    type: str = Field(..., description="doc, sheet, or insight")
    title: str
    content: Any
    is_private: bool = False
    security_level: Optional[str] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[Any] = None
    is_private: Optional[bool] = None
    security_level: Optional[str] = None
    shared_with: Optional[List[str]] = None


class Document(BaseModel):
    id: str
    type: str
    title: str
    content: Any
    created_at: str
    updated_at: str
    created_by: str
    is_private: bool = False
    security_level: Optional[str] = None
    shared_with: List[str] = Field(default_factory=list)


class SyncRequest(BaseModel):
    """Batch sync request for multiple documents"""
    documents: List[Dict[str, Any]]
    last_sync: Optional[str] = None


class SyncResponse(BaseModel):
    """Sync response with updated documents and conflicts"""
    updated_documents: List[Document]
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    sync_timestamp: str


# ===== Database =====

def init_db():
    """Initialize the documents database"""
    conn = sqlite3.connect(DOCS_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            is_private INTEGER DEFAULT 0,
            security_level TEXT,
            shared_with TEXT DEFAULT '[]'
        )
    """)

    # Indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_updated_at ON documents(updated_at)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_by ON documents(created_by)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_by_updated ON documents(created_by, updated_at)
    """)

    conn.commit()
    conn.close()
    logger.info("📁 Documents database initialized")


# Initialize on module load
init_db()


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DOCS_DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


# ===== CRUD Operations =====

@router.post("/documents", response_model=Document)
@require_perm("docs.create", level="write")
async def create_document(
    request: Request,
    doc: DocumentCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Create a new document"""
    doc_id = f"doc_{datetime.utcnow().timestamp()}_{os.urandom(4).hex()}"
    now = datetime.utcnow().isoformat()
    user_id = current_user["user_id"]

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO documents (
                id, type, title, content, created_at, updated_at,
                created_by, is_private, security_level, shared_with
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            doc.type,
            doc.title,
            json.dumps(doc.content),
            now,
            now,
            user_id,
            1 if doc.is_private else 0,
            doc.security_level,
            json.dumps([])
        ))

        conn.commit()

        # Return the created document (verify ownership)
        cursor.execute("""
            SELECT * FROM documents
            WHERE id = ? AND created_by = ?
        """, (doc_id, user_id))
        row = cursor.fetchone()

        return Document(
            id=row["id"],
            type=row["type"],
            title=row["title"],
            content=json.loads(row["content"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
            is_private=bool(row["is_private"]),
            security_level=row["security_level"],
            shared_with=json.loads(row["shared_with"])
        )

    except Exception as e:
        logger.error(f"Failed to create document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/documents", response_model=List[Document])
@require_perm("docs.read", level="read")
async def list_documents(
    since: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    List user's documents, optionally filtered by timestamp
    Used for initial load and periodic sync
    """
    conn = get_db()
    cursor = conn.cursor()
    user_id = current_user["user_id"]

    try:
        if since:
            cursor.execute("""
                SELECT * FROM documents
                WHERE created_by = ? AND updated_at > ?
                ORDER BY updated_at DESC
            """, (user_id, since))
        else:
            cursor.execute("""
                SELECT * FROM documents
                WHERE created_by = ?
                ORDER BY updated_at DESC
            """, (user_id,))

        rows = cursor.fetchall()

        documents = []
        for row in rows:
            documents.append(Document(
                id=row["id"],
                type=row["type"],
                title=row["title"],
                content=json.loads(row["content"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                created_by=row["created_by"],
                is_private=bool(row["is_private"]),
                security_level=row["security_level"],
                shared_with=json.loads(row["shared_with"])
            ))

        return documents

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/documents/{doc_id}", response_model=Document)
@require_perm("docs.read", level="read")
async def get_document(doc_id: str, current_user: Dict = Depends(get_current_user)):
    """Get a specific document by ID (user must own it)"""
    conn = get_db()
    cursor = conn.cursor()
    user_id = current_user["user_id"]

    try:
        cursor.execute("""
            SELECT * FROM documents
            WHERE id = ? AND created_by = ?
        """, (doc_id, user_id))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Document not found or access denied")

        return Document(
            id=row["id"],
            type=row["type"],
            title=row["title"],
            content=json.loads(row["content"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
            is_private=bool(row["is_private"]),
            security_level=row["security_level"],
            shared_with=json.loads(row["shared_with"])
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.patch("/documents/{doc_id}", response_model=Document)
@require_perm("docs.update", level="write")
async def update_document(
    doc_id: str,
    updates: DocumentUpdate,
    current_user: Dict = Depends(get_current_user)
):
    """Update a document (partial update - user must own it)"""
    conn = get_db()
    cursor = conn.cursor()
    user_id = current_user["user_id"]

    try:
        # Check if document exists and user owns it
        cursor.execute("""
            SELECT * FROM documents
            WHERE id = ? AND created_by = ?
        """, (doc_id, user_id))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Document not found or access denied")

        # Build update query dynamically
        update_fields = []
        values = []

        if updates.title is not None:
            update_fields.append("title = ?")
            values.append(updates.title)

        if updates.content is not None:
            update_fields.append("content = ?")
            values.append(json.dumps(updates.content))

        if updates.is_private is not None:
            update_fields.append("is_private = ?")
            values.append(1 if updates.is_private else 0)

        if updates.security_level is not None:
            update_fields.append("security_level = ?")
            values.append(updates.security_level)

        if updates.shared_with is not None:
            update_fields.append("shared_with = ?")
            values.append(json.dumps(updates.shared_with))

        # Always update timestamp
        now = datetime.utcnow().isoformat()
        update_fields.append("updated_at = ?")
        values.append(now)

        values.append(doc_id)
        values.append(user_id)

        cursor.execute(
            f"UPDATE documents SET {', '.join(update_fields)} WHERE id = ? AND created_by = ?",
            values
        )

        conn.commit()

        # Return updated document (verify ownership)
        cursor.execute("""
            SELECT * FROM documents
            WHERE id = ? AND created_by = ?
        """, (doc_id, user_id))
        row = cursor.fetchone()

        return Document(
            id=row["id"],
            type=row["type"],
            title=row["title"],
            content=json.loads(row["content"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
            is_private=bool(row["is_private"]),
            security_level=row["security_level"],
            shared_with=json.loads(row["shared_with"])
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.delete("/documents/{doc_id}")
@require_perm("docs.delete", level="write")
async def delete_document(
    request: Request,
    doc_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Delete a document (user must own it)"""
    conn = get_db()
    cursor = conn.cursor()
    user_id = current_user["user_id"]

    try:
        cursor.execute("""
            DELETE FROM documents
            WHERE id = ? AND created_by = ?
        """, (doc_id, user_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Document not found or access denied")

        conn.commit()

        return {"status": "deleted", "id": doc_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/sync", response_model=SyncResponse)
async def sync_documents(
    request: Request,
    body: SyncRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Batch sync endpoint (Notion-style)

    Client sends all changed documents since last sync.
    Server responds with any documents that have been updated by current user.

    Conflict resolution: Last-write-wins based on timestamps.
    """
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    user_id = current_user["user_id"]
    conflicts = []
    updated_documents = []

    try:
        # Process each document in the batch
        for doc_data in body.documents:
            doc_id = doc_data.get("id")

            if not doc_id:
                continue

            # Check if document exists and user owns it
            cursor.execute("""
                SELECT * FROM documents
                WHERE id = ? AND created_by = ?
            """, (doc_id, user_id))
            row = cursor.fetchone()

            if row:
                # Document exists - check for conflicts
                server_updated = row["updated_at"]
                client_updated = doc_data.get("updated_at", "")

                if server_updated > client_updated:
                    # Server has newer version - conflict!
                    conflicts.append({
                        "id": doc_id,
                        "server_updated": server_updated,
                        "client_updated": client_updated,
                        "resolution": "server_wins"
                    })
                else:
                    # Client has newer version - update server
                    cursor.execute("""
                        UPDATE documents
                        SET title = ?, content = ?, updated_at = ?,
                            is_private = ?, security_level = ?, shared_with = ?
                        WHERE id = ? AND created_by = ?
                    """, (
                        doc_data.get("title", row["title"]),
                        json.dumps(doc_data.get("content", json.loads(row["content"]))),
                        now,
                        1 if doc_data.get("is_private", bool(row["is_private"])) else 0,
                        doc_data.get("security_level", row["security_level"]),
                        json.dumps(doc_data.get("shared_with", json.loads(row["shared_with"]))),
                        doc_id,
                        user_id
                    ))
            else:
                # Document doesn't exist - create it for current user
                cursor.execute("""
                    INSERT INTO documents (
                        id, type, title, content, created_at, updated_at,
                        created_by, is_private, security_level, shared_with
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    doc_data.get("type", "doc"),
                    doc_data.get("title", "Untitled"),
                    json.dumps(doc_data.get("content", "")),
                    doc_data.get("created_at", now),
                    now,
                    user_id,  # Always use current user
                    1 if doc_data.get("is_private", False) else 0,
                    doc_data.get("security_level"),
                    json.dumps(doc_data.get("shared_with", []))
                ))

        conn.commit()

        # Get user's documents updated since last sync (or all if first sync)
        if body.last_sync:
            cursor.execute("""
                SELECT * FROM documents
                WHERE created_by = ? AND updated_at > ?
            """, (user_id, body.last_sync))
        else:
            cursor.execute("""
                SELECT * FROM documents
                WHERE created_by = ?
            """, (user_id,))

        rows = cursor.fetchall()

        for row in rows:
            updated_documents.append(Document(
                id=row["id"],
                type=row["type"],
                title=row["title"],
                content=json.loads(row["content"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                created_by=row["created_by"],
                is_private=bool(row["is_private"]),
                security_level=row["security_level"],
                shared_with=json.loads(row["shared_with"])
            ))

        return SyncResponse(
            updated_documents=updated_documents,
            conflicts=conflicts,
            sync_timestamp=now
        )

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# Export router
__all__ = ["router"]
