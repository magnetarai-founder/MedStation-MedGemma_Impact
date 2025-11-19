"""
Code Editor Database Operations
All workspace and file CRUD operations
"""

import logging
from elohimos_memory import ElohimOSMemory

logger = logging.getLogger(__name__)

# Initialize memory system
memory = ElohimOSMemory()


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_code_editor_db():
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

def create_workspace(workspace_id: str, name: str, source_type: str, disk_path: str = None):
    """Create new workspace in database"""
    conn = memory.memory.conn

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


def get_workspace(workspace_id: str):
    """Get workspace by ID"""
    conn = memory.memory.conn

    workspace = conn.execute("""
        SELECT id, name, source_type, disk_path, created_at, updated_at
        FROM code_editor_workspaces
        WHERE id = ?
    """, (workspace_id,)).fetchone()

    return workspace


def list_workspaces():
    """List all workspaces"""
    conn = memory.memory.conn

    workspaces = conn.execute("""
        SELECT id, name, source_type, disk_path, created_at, updated_at
        FROM code_editor_workspaces
        ORDER BY updated_at DESC
    """).fetchall()

    return workspaces


def update_workspace_timestamp(workspace_id: str):
    """Update workspace updated_at timestamp"""
    conn = memory.memory.conn

    conn.execute("""
        UPDATE code_editor_workspaces
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (workspace_id,))

    conn.commit()


def delete_workspace(workspace_id: str):
    """Delete workspace (CASCADE will delete files)"""
    conn = memory.memory.conn

    conn.execute("DELETE FROM code_editor_workspaces WHERE id = ?", (workspace_id,))
    conn.commit()


# ============================================================================
# FILE CRUD OPERATIONS
# ============================================================================

def create_file(file_id: str, workspace_id: str, name: str, path: str, content: str, language: str):
    """Create new file in database"""
    conn = memory.memory.conn

    conn.execute("""
        INSERT INTO code_editor_files (id, workspace_id, name, path, content, language)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (file_id, workspace_id, name, path, content, language))

    conn.commit()


def get_file(file_id: str):
    """Get file by ID"""
    conn = memory.memory.conn

    file = conn.execute("""
        SELECT id, workspace_id, name, path, content, language, created_at, updated_at
        FROM code_editor_files
        WHERE id = ?
    """, (file_id,)).fetchone()

    return file


def get_file_for_diff(file_id: str):
    """Get file content and updated_at for diff operations"""
    conn = memory.memory.conn

    file = conn.execute("""
        SELECT content, updated_at
        FROM code_editor_files
        WHERE id = ?
    """, (file_id,)).fetchone()

    return file


def get_files_by_workspace(workspace_id: str):
    """Get all files for a workspace"""
    conn = memory.memory.conn

    files = conn.execute("""
        SELECT id, name, path, content
        FROM code_editor_files
        WHERE workspace_id = ?
        ORDER BY path
    """, (workspace_id,)).fetchall()

    return files


def get_file_info_before_delete(file_id: str):
    """Get file info before deletion"""
    conn = memory.memory.conn

    file_info = conn.execute("""
        SELECT workspace_id, path
        FROM code_editor_files
        WHERE id = ?
    """, (file_id,)).fetchone()

    return file_info


def update_file(file_id: str, updates: dict):
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


def get_file_current_state(file_id: str):
    """Get current file state for optimistic concurrency check"""
    conn = memory.memory.conn

    current = conn.execute("""
        SELECT workspace_id, name, path, content, language, updated_at
        FROM code_editor_files
        WHERE id = ?
    """, (file_id,)).fetchone()

    return current


def delete_file(file_id: str):
    """Delete file from database"""
    conn = memory.memory.conn

    conn.execute("DELETE FROM code_editor_files WHERE id = ?", (file_id,))
    conn.commit()


def delete_files_by_workspace(workspace_id: str):
    """Delete all files for a workspace"""
    conn = memory.memory.conn

    conn.execute("DELETE FROM code_editor_files WHERE workspace_id = ?", (workspace_id,))
    conn.commit()
