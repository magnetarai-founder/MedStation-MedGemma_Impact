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
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
import logging

from fastapi import APIRouter, HTTPException, Request, Depends, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.routes.schemas import SuccessResponse

# Import user service (migrated to services layer)
try:
    from services.users import get_or_create_user_profile as get_or_create_user
except ImportError:
    from api.services.users import get_or_create_user_profile as get_or_create_user

# Phase 2: Import permission decorators
# Phase 3: Import team-aware decorators and membership helpers
try:
    from permission_engine import require_perm, require_perm_team
    from auth_middleware import get_current_user
    from team_service import is_team_member
except ImportError:
    from api.permission_engine import require_perm, require_perm_team
    from api.auth_middleware import get_current_user
    from api.team_service import is_team_member

logger = logging.getLogger(__name__)

# Storage paths - use centralized config_paths
try:
    from config_paths import get_config_paths
except ImportError:
    from api.config_paths import get_config_paths
PATHS = get_config_paths()
DOCS_DB_PATH = PATHS.data_dir / "docs.db"
DOCS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Whitelisted columns for SQL UPDATE to prevent injection
DOCUMENT_UPDATE_COLUMNS = frozenset({
    "title", "content", "is_private", "security_level", "shared_with", "updated_at"
})


def build_safe_update(updates_dict: Dict[str, Any], allowed_columns: frozenset) -> tuple:
    """
    Build safe SQL UPDATE clause with whitelist validation.

    Args:
        updates_dict: Dict of column_name -> value pairs
        allowed_columns: Frozenset of allowed column names

    Returns:
        Tuple of (update_clauses, params) for use in SQL query

    Raises:
        ValueError: If any column is not in the whitelist
    """
    clauses = []
    params = []

    for column, value in updates_dict.items():
        if column not in allowed_columns:
            raise ValueError(f"Invalid column for update: {column}")
        clauses.append(f"{column} = ?")
        params.append(value)

    return clauses, params


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
    team_id: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "id": "doc_123",
                "type": "doc",
                "title": "My Document",
                "content": {},
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00",
                "created_by": "user_123",
                "is_private": False,
                "shared_with": []
            }
        }
    }


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
            shared_with TEXT DEFAULT '[]',
            team_id TEXT
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

    # Index for team documents (Phase 3)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_team_id ON documents(team_id)
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
async def create_document(
    request: Request,
    doc: DocumentCreate,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a new document (Phase 3: team-aware)

    - If team_id is provided, creates a team document
    - If team_id is None, creates a personal document
    - Checks team membership before allowing team document creation
    """
    user_id = current_user["user_id"]

    # Phase 3: Check team membership if creating team document
    if team_id:
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    doc_id = f"doc_{datetime.now(UTC).timestamp()}_{os.urandom(4).hex()}"
    now = datetime.now(UTC).isoformat()

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Phase 3: Include team_id in insert
        cursor.execute("""
            INSERT INTO documents (
                id, type, title, content, created_at, updated_at,
                created_by, is_private, security_level, shared_with, team_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps([]),
            team_id  # Phase 3: team_id
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
            shared_with=json.loads(row["shared_with"]),
            team_id=row["team_id"] if "team_id" in row.keys() else None
        )

    except Exception as e:
        logger.error(f"Failed to create document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/documents")
async def list_documents(
    since: Optional[str] = None,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    List user's documents, optionally filtered by timestamp (Phase 3: team-aware)
    Used for initial load and periodic sync

    - If team_id is provided, lists team documents (if member)
    - If team_id is None, lists personal documents
    """
    user_id = current_user["user_id"]

    # Phase 3: Check team membership if listing team documents
    if team_id:
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Phase 3: Filter by team_id
        if team_id:
            # Team documents: filter by team_id
            if since:
                cursor.execute("""
                    SELECT * FROM documents
                    WHERE team_id = ? AND updated_at > ?
                    ORDER BY updated_at DESC
                """, (team_id, since))
            else:
                cursor.execute("""
                    SELECT * FROM documents
                    WHERE team_id = ?
                    ORDER BY updated_at DESC
                """, (team_id,))
        else:
            # Personal documents: team_id IS NULL and created_by = user_id
            if since:
                cursor.execute("""
                    SELECT * FROM documents
                    WHERE created_by = ? AND team_id IS NULL AND updated_at > ?
                    ORDER BY updated_at DESC
                """, (user_id, since))
            else:
                cursor.execute("""
                    SELECT * FROM documents
                    WHERE created_by = ? AND team_id IS NULL
                    ORDER BY updated_at DESC
                """, (user_id,))

        rows = cursor.fetchall()

        documents = []
        for row in rows:
            # Explicitly construct dictionary to ensure all fields are present
            doc_dict = {
                "id": row["id"],
                "type": row["type"],
                "title": row["title"],
                "content": json.loads(row["content"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "created_by": row["created_by"],
                "is_private": bool(row["is_private"]),
                "security_level": row["security_level"],
                "shared_with": json.loads(row["shared_with"]),
                "team_id": row["team_id"] if "team_id" in row.keys() else None
            }
            documents.append(doc_dict)

        # Log first document for debugging
        if documents:
            print(f"✅ DOCS DEBUG: Returning {len(documents)} documents with fields: {list(documents[0].keys())}", flush=True)
            print(f"📦 DOCS DEBUG: First document JSON: {json.dumps(documents[0], indent=2)}", flush=True)
        else:
            print("⚠️ DOCS DEBUG: No documents found", flush=True)

        return SuccessResponse(data=documents, message=f"Found {len(documents)} document(s)")

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/documents/{doc_id}", response_model=Document)
async def get_document(
    doc_id: str,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get a specific document by ID (Phase 3: team-aware)

    - For personal documents: user must own it
    - For team documents: user must be team member
    """
    user_id = current_user["user_id"]

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Phase 3: Check team membership if accessing team document
        if team_id:
            if not is_team_member(team_id, user_id):
                raise HTTPException(status_code=403, detail="Not a member of this team")

            # Team document: verify team_id matches
            cursor.execute("""
                SELECT * FROM documents
                WHERE id = ? AND team_id = ?
            """, (doc_id, team_id))
        else:
            # Personal document: verify ownership and team_id IS NULL
            cursor.execute("""
                SELECT * FROM documents
                WHERE id = ? AND created_by = ? AND team_id IS NULL
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
            shared_with=json.loads(row["shared_with"]),
            team_id=row["team_id"] if "team_id" in row.keys() else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.patch("/documents/{doc_id}", response_model=Document)
async def update_document(
    doc_id: str,
    updates: DocumentUpdate,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Update a document (partial update, Phase 3: team-aware)

    - For personal documents: user must own it
    - For team documents: user must be team member
    """
    user_id = current_user["user_id"]

    # Phase 3: Check team membership if updating team document
    if team_id:
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Phase 3: Check if document exists with team context
        if team_id:
            # Team document: verify team_id matches
            cursor.execute("""
                SELECT * FROM documents
                WHERE id = ? AND team_id = ?
            """, (doc_id, team_id))
        else:
            # Personal document: verify ownership and team_id IS NULL
            cursor.execute("""
                SELECT * FROM documents
                WHERE id = ? AND created_by = ? AND team_id IS NULL
            """, (doc_id, user_id))

        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Document not found or access denied")

        # Build update dict with whitelisted columns only
        updates_dict = {}
        if updates.title is not None:
            updates_dict["title"] = updates.title
        if updates.content is not None:
            updates_dict["content"] = json.dumps(updates.content)
        if updates.is_private is not None:
            updates_dict["is_private"] = 1 if updates.is_private else 0
        if updates.security_level is not None:
            updates_dict["security_level"] = updates.security_level
        if updates.shared_with is not None:
            updates_dict["shared_with"] = json.dumps(updates.shared_with)

        # Always update timestamp
        now = datetime.now(UTC).isoformat()
        updates_dict["updated_at"] = now

        # Use safe builder with whitelist validation
        update_fields, values = build_safe_update(updates_dict, DOCUMENT_UPDATE_COLUMNS)
        values.append(doc_id)

        # Phase 3: Update with team context
        if team_id:
            cursor.execute(
                f"UPDATE documents SET {', '.join(update_fields)} WHERE id = ? AND team_id = ?",
                values + [team_id]
            )
        else:
            values.append(user_id)
            cursor.execute(
                f"UPDATE documents SET {', '.join(update_fields)} WHERE id = ? AND created_by = ? AND team_id IS NULL",
                values
            )

        conn.commit()

        # Return updated document (verify context)
        if team_id:
            cursor.execute("""
                SELECT * FROM documents
                WHERE id = ? AND team_id = ?
            """, (doc_id, team_id))
        else:
            cursor.execute("""
                SELECT * FROM documents
                WHERE id = ? AND created_by = ? AND team_id IS NULL
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
            shared_with=json.loads(row["shared_with"]),
            team_id=row["team_id"] if "team_id" in row.keys() else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.delete("/documents/{doc_id}")
async def delete_document(
    request: Request,
    doc_id: str,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Delete a document (Phase 3: team-aware)

    - For personal documents: user must own it
    - For team documents: user must be team member (permissions checked via decorator)
    """
    user_id = current_user["user_id"]

    # Phase 3: Check team membership if deleting team document
    if team_id:
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    conn = get_db()
    cursor = conn.cursor()

    try:
        if team_id:
            # Team document: verify team_id matches
            cursor.execute("""
                DELETE FROM documents
                WHERE id = ? AND team_id = ?
            """, (doc_id, team_id))
        else:
            # Personal document: verify ownership and team_id IS NULL
            cursor.execute("""
                DELETE FROM documents
                WHERE id = ? AND created_by = ? AND team_id IS NULL
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
    now = datetime.now(UTC).isoformat()
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
