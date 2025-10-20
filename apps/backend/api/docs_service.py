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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Storage paths
DOCS_DB_PATH = Path(".neutron_data/docs.db")
DOCS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/v1/docs", tags=["Docs"])


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

    # Index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_updated_at ON documents(updated_at)
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
async def create_document(doc: DocumentCreate):
    """Create a new document"""
    doc_id = f"doc_{datetime.utcnow().timestamp()}_{os.urandom(4).hex()}"
    now = datetime.utcnow().isoformat()

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
            "local_user",  # TODO: Replace with actual user ID
            1 if doc.is_private else 0,
            doc.security_level,
            json.dumps([])
        ))

        conn.commit()

        # Return the created document
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
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
async def list_documents(since: Optional[str] = None):
    """
    List all documents, optionally filtered by timestamp
    Used for initial load and periodic sync
    """
    conn = get_db()
    cursor = conn.cursor()

    try:
        if since:
            cursor.execute(
                "SELECT * FROM documents WHERE updated_at > ? ORDER BY updated_at DESC",
                (since,)
            )
        else:
            cursor.execute("SELECT * FROM documents ORDER BY updated_at DESC")

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
async def get_document(doc_id: str):
    """Get a specific document by ID"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Document not found")

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
async def update_document(doc_id: str, updates: DocumentUpdate):
    """Update a document (partial update)"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Check if document exists
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Document not found")

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

        cursor.execute(
            f"UPDATE documents SET {', '.join(update_fields)} WHERE id = ?",
            values
        )

        conn.commit()

        # Return updated document
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
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
async def delete_document(doc_id: str):
    """Delete a document"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Document not found")

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
async def sync_documents(request: SyncRequest):
    """
    Batch sync endpoint (Notion-style)

    Client sends all changed documents since last sync.
    Server responds with any documents that have been updated by others.

    Conflict resolution: Last-write-wins based on timestamps.
    """
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    conflicts = []
    updated_documents = []

    try:
        # Process each document in the batch
        for doc_data in request.documents:
            doc_id = doc_data.get("id")

            if not doc_id:
                continue

            # Check if document exists
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
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
                        WHERE id = ?
                    """, (
                        doc_data.get("title", row["title"]),
                        json.dumps(doc_data.get("content", json.loads(row["content"]))),
                        now,
                        1 if doc_data.get("is_private", bool(row["is_private"])) else 0,
                        doc_data.get("security_level", row["security_level"]),
                        json.dumps(doc_data.get("shared_with", json.loads(row["shared_with"]))),
                        doc_id
                    ))
            else:
                # Document doesn't exist - create it
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
                    doc_data.get("created_by", "local_user"),
                    1 if doc_data.get("is_private", False) else 0,
                    doc_data.get("security_level"),
                    json.dumps(doc_data.get("shared_with", []))
                ))

        conn.commit()

        # Get all documents updated since last sync (or all if first sync)
        if request.last_sync:
            cursor.execute(
                "SELECT * FROM documents WHERE updated_at > ?",
                (request.last_sync,)
            )
        else:
            cursor.execute("SELECT * FROM documents")

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
