"""
Code Editor Database Operations
All workspace and file CRUD operations
"""

import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional
from api.elohimos_memory import ElohimOSMemory
from .models import WorkspaceResponse

logger = logging.getLogger(__name__)

# Initialize memory system
memory = ElohimOSMemory()


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_code_editor_db() -> None:
    """Initialize code editor database tables"""
    conn = memory.memory.conn

    # Workspaces table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS code_editor_workspaces (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            source_type TEXT NOT NULL CHECK(source_type IN ('disk', 'database')),
            disk_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Files table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS code_editor_files (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            content TEXT NOT NULL,
            language TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workspace_id) REFERENCES code_editor_workspaces(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    logger.info("✓ Code editor database tables initialized")


# ============================================================================
# WORKSPACE CRUD OPERATIONS
# ============================================================================

def create_workspace(name: str, source_type: str, disk_path: str = None, files: list = None) -> WorkspaceResponse:
    """Create new workspace in database and return WorkspaceResponse"""
    conn = memory.memory.conn
    workspace_id = str(uuid.uuid4())
    now = datetime.utcnow()

    if disk_path:
        conn.execute("""
            INSERT INTO code_editor_workspaces (id, name, source_type, disk_path)
            VALUES (?, ?, ?, ?)
        """, (workspace_id, name, source_type, disk_path))
    else:
        conn.execute("""
            INSERT INTO code_editor_workspaces (id, name, source_type)
            VALUES (?, ?, ?)
        """, (workspace_id, name, source_type))

    conn.commit()

    # If files provided (for disk workspaces), create them
    if files:
        for file_data in files:
            create_file(
                workspace_id=workspace_id,
                name=file_data.get('name', 'unnamed'),
                path=file_data.get('path', ''),
                content=file_data.get('content', ''),
                language=file_data.get('language', 'plaintext')
            )

    # Return workspace response
    return WorkspaceResponse(
        id=workspace_id,
        name=name,
        source_type=source_type,
        disk_path=disk_path,
        created_at=now,
        updated_at=now
    )


def get_workspace(workspace_id: str) -> Optional[WorkspaceResponse]:
    """Get workspace by ID, returns WorkspaceResponse or None"""
    conn = memory.memory.conn

    row = conn.execute("""
        SELECT id, name, source_type, disk_path, created_at, updated_at
        FROM code_editor_workspaces
        WHERE id = ?
    """, (workspace_id,)).fetchone()

    if not row:
        return None

    return WorkspaceResponse(
        id=row[0],
        name=row[1],
        source_type=row[2],
        disk_path=row[3],
        created_at=datetime.fromisoformat(row[4]) if row[4] else datetime.utcnow(),
        updated_at=datetime.fromisoformat(row[5]) if row[5] else datetime.utcnow()
    )


def list_workspaces() -> List[WorkspaceResponse]:
    """List all workspaces"""
    conn = memory.memory.conn

    rows = conn.execute("""
        SELECT id, name, source_type, disk_path, created_at, updated_at
        FROM code_editor_workspaces
        ORDER BY updated_at DESC
    """).fetchall()

    workspaces = []
    for row in rows:
        workspaces.append(WorkspaceResponse(
            id=row[0],
            name=row[1],
            source_type=row[2],
            disk_path=row[3],
            created_at=datetime.fromisoformat(row[4]) if row[4] else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row[5]) if row[5] else datetime.utcnow()
        ))

    return workspaces


def update_workspace_timestamp(workspace_id: str) -> None:
    """Update workspace updated_at timestamp"""
    conn = memory.memory.conn

    conn.execute("""
        UPDATE code_editor_workspaces
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (workspace_id,))

    conn.commit()


def delete_workspace(workspace_id: str) -> None:
    """Delete workspace (CASCADE will delete files)"""
    conn = memory.memory.conn

    conn.execute("DELETE FROM code_editor_workspaces WHERE id = ?", (workspace_id,))
    conn.commit()


# ============================================================================
# FILE CRUD OPERATIONS
# ============================================================================

def create_file(workspace_id: str, name: str, path: str, content: str, language: str, file_id: str = None) -> str:
    """Create new file in database. Auto-generates file_id if not provided."""
    conn = memory.memory.conn

    # Auto-generate file_id if not provided
    if file_id is None:
        file_id = str(uuid.uuid4())

    conn.execute("""
        INSERT INTO code_editor_files (id, workspace_id, name, path, content, language)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (file_id, workspace_id, name, path, content, language))

    conn.commit()
    return file_id


def get_file(file_id: str) -> Optional[Any]:
    """Get file by ID"""
    conn = memory.memory.conn

    file = conn.execute("""
        SELECT id, workspace_id, name, path, content, language, created_at, updated_at
        FROM code_editor_files
        WHERE id = ?
    """, (file_id,)).fetchone()

    return file


def get_file_for_diff(file_id: str) -> Optional[Any]:
    """Get file content and updated_at for diff operations"""
    conn = memory.memory.conn

    file = conn.execute("""
        SELECT content, updated_at
        FROM code_editor_files
        WHERE id = ?
    """, (file_id,)).fetchone()

    return file


def get_files_by_workspace(workspace_id: str) -> List[Any]:
    """Get all files for a workspace"""
    conn = memory.memory.conn

    files = conn.execute("""
        SELECT id, name, path, content
        FROM code_editor_files
        WHERE workspace_id = ?
        ORDER BY path
    """, (workspace_id,)).fetchall()

    return files


def get_file_info_before_delete(file_id: str) -> Optional[Any]:
    """Get file info before deletion"""
    conn = memory.memory.conn

    file_info = conn.execute("""
        SELECT workspace_id, path
        FROM code_editor_files
        WHERE id = ?
    """, (file_id,)).fetchone()

    return file_info


def update_file(file_id: str, updates: dict) -> None:
    """Update file with dynamic fields"""
    conn = memory.memory.conn

    # Build update query
    update_parts = []
    values = []

    if 'name' in updates:
        update_parts.append("name = ?")
        values.append(updates['name'])
    if 'path' in updates:
        update_parts.append("path = ?")
        values.append(updates['path'])
    if 'content' in updates:
        update_parts.append("content = ?")
        values.append(updates['content'])
    if 'language' in updates:
        update_parts.append("language = ?")
        values.append(updates['language'])

    update_parts.append("updated_at = CURRENT_TIMESTAMP")
    values.append(file_id)

    conn.execute(f"""
        UPDATE code_editor_files
        SET {', '.join(update_parts)}
        WHERE id = ?
    """, values)

    conn.commit()


def get_file_current_state(file_id: str) -> Optional[Any]:
    """Get current file state for optimistic concurrency check"""
    conn = memory.memory.conn

    current = conn.execute("""
        SELECT workspace_id, name, path, content, language, updated_at
        FROM code_editor_files
        WHERE id = ?
    """, (file_id,)).fetchone()

    return current


def delete_file(file_id: str) -> None:
    """Delete file from database"""
    conn = memory.memory.conn

    conn.execute("DELETE FROM code_editor_files WHERE id = ?", (file_id,))
    conn.commit()


def delete_files_by_workspace(workspace_id: str) -> None:
    """Delete all files for a workspace"""
    conn = memory.memory.conn

    conn.execute("DELETE FROM code_editor_files WHERE workspace_id = ?", (workspace_id,))
    conn.commit()
