"""
Code Editor Service
Manages workspaces and files for the code editor
"""

import os
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import json

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel

from elohimos_memory import ElohimOSMemory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/code-editor", tags=["code-editor"])

# Initialize memory system
memory = ElohimOSMemory()

# Ensure code editor tables exist
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

# Initialize on import
init_code_editor_db()


# Models
class WorkspaceCreate(BaseModel):
    name: str
    source_type: str  # 'disk' or 'database'
    disk_path: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    source_type: str
    disk_path: Optional[str]
    created_at: datetime
    updated_at: datetime


class FileCreate(BaseModel):
    workspace_id: str
    name: str
    path: str
    content: str
    language: str


class FileUpdate(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None


class FileResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    path: str
    content: str
    language: str
    created_at: datetime
    updated_at: datetime


class FileTreeNode(BaseModel):
    id: str
    name: str
    path: str
    is_directory: bool
    children: Optional[List['FileTreeNode']] = None


# Helper functions
def build_file_tree(workspace_id: str) -> List[FileTreeNode]:
    """Build hierarchical file tree from flat file list"""
    conn = memory.memory.conn

    files = conn.execute("""
        SELECT id, name, path, content
        FROM code_editor_files
        WHERE workspace_id = ?
        ORDER BY path
    """, (workspace_id,)).fetchall()

    # Build tree structure
    root_nodes = []
    path_map = {}

    for file_row in files:
        file_id, name, path, content = file_row
        parts = path.split('/')

        # Handle root files
        if len(parts) == 1:
            root_nodes.append(FileTreeNode(
                id=file_id,
                name=name,
                path=path,
                is_directory=False
            ))
            continue

        # Build directory structure
        current_path = ""
        for i, part in enumerate(parts[:-1]):
            current_path = f"{current_path}/{part}" if current_path else part

            if current_path not in path_map:
                node = FileTreeNode(
                    id=f"dir_{current_path}",
                    name=part,
                    path=current_path,
                    is_directory=True,
                    children=[]
                )
                path_map[current_path] = node

                # Add to parent or root
                if i == 0:
                    root_nodes.append(node)
                else:
                    parent_path = "/".join(parts[:i])
                    if parent_path in path_map:
                        path_map[parent_path].children.append(node)

        # Add file to parent directory
        file_node = FileTreeNode(
            id=file_id,
            name=name,
            path=path,
            is_directory=False
        )

        parent_path = "/".join(parts[:-1])
        if parent_path in path_map:
            path_map[parent_path].children.append(file_node)

    return root_nodes


def scan_disk_directory(dir_path: str) -> List[Dict[str, Any]]:
    """Recursively scan directory and return file list"""
    files = []
    base_path = Path(dir_path)

    # Ignore patterns
    ignore_patterns = {
        '.git', 'node_modules', '__pycache__', '.venv', 'venv',
        '.DS_Store', '.vscode', '.idea', 'dist', 'build'
    }

    for file_path in base_path.rglob('*'):
        # Skip ignored directories
        if any(ignored in file_path.parts for ignored in ignore_patterns):
            continue

        # Skip directories themselves
        if file_path.is_dir():
            continue

        # Get relative path
        rel_path = file_path.relative_to(base_path)

        # Detect language from extension
        ext = file_path.suffix.lower()
        lang_map = {
            '.js': 'javascript', '.jsx': 'javascript',
            '.ts': 'typescript', '.tsx': 'typescript',
            '.py': 'python',
            '.java': 'java',
            '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.yaml': 'yaml', '.yml': 'yaml',
            '.md': 'markdown',
            '.sql': 'sql',
            '.sh': 'shell',
        }
        language = lang_map.get(ext, 'plaintext')

        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            # Skip binary files or files that can't be read
            continue

        files.append({
            'name': file_path.name,
            'path': str(rel_path).replace('\\', '/'),
            'content': content,
            'language': language
        })

    return files


# Endpoints
@router.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(request: Request, workspace: WorkspaceCreate):
    """Create a new database workspace"""
    try:
        if workspace.source_type != 'database':
            raise HTTPException(status_code=400, detail="Only database workspaces can be created this way")

        workspace_id = str(uuid.uuid4())
        conn = memory.memory.conn

        conn.execute("""
            INSERT INTO code_editor_workspaces (id, name, source_type)
            VALUES (?, ?, 'database')
        """, (workspace_id, workspace.name))

        conn.commit()

        # Return workspace info
        created_workspace = conn.execute("""
            SELECT id, name, source_type, disk_path, created_at, updated_at
            FROM code_editor_workspaces
            WHERE id = ?
        """, (workspace_id,)).fetchone()

        return WorkspaceResponse(
            id=created_workspace[0],
            name=created_workspace[1],
            source_type=created_workspace[2],
            disk_path=created_workspace[3],
            created_at=created_workspace[4],
            updated_at=created_workspace[5]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/open-disk", response_model=WorkspaceResponse)
async def open_disk_workspace(request: Request, name: str = Form(...), disk_path: str = Form(...)):
    """Open folder from disk and create workspace"""
    try:
        # Validate path exists
        path = Path(disk_path)
        if not path.exists() or not path.is_dir():
            raise HTTPException(status_code=400, detail="Invalid directory path")

        # Create workspace
        workspace_id = str(uuid.uuid4())
        conn = memory.memory.conn

        conn.execute("""
            INSERT INTO code_editor_workspaces (id, name, source_type, disk_path)
            VALUES (?, ?, 'disk', ?)
        """, (workspace_id, name, str(path.absolute())))

        # Scan and import files
        files = scan_disk_directory(str(path))
        logger.info(f"Found {len(files)} files in {disk_path}")

        for file_data in files:
            file_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO code_editor_files (id, workspace_id, name, path, content, language)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                workspace_id,
                file_data['name'],
                file_data['path'],
                file_data['content'],
                file_data['language']
            ))

        conn.commit()

        # Return workspace info
        workspace = conn.execute("""
            SELECT id, name, source_type, disk_path, created_at, updated_at
            FROM code_editor_workspaces
            WHERE id = ?
        """, (workspace_id,)).fetchone()

        return WorkspaceResponse(
            id=workspace[0],
            name=workspace[1],
            source_type=workspace[2],
            disk_path=workspace[3],
            created_at=workspace[4],
            updated_at=workspace[5]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to open disk workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/open-database", response_model=WorkspaceResponse)
async def open_database_workspace(request: Request, workspace_id: str = Form(...)):
    """Open existing workspace from database"""
    try:
        conn = memory.memory.conn

        workspace = conn.execute("""
            SELECT id, name, source_type, disk_path, created_at, updated_at
            FROM code_editor_workspaces
            WHERE id = ?
        """, (workspace_id,)).fetchone()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        return WorkspaceResponse(
            id=workspace[0],
            name=workspace[1],
            source_type=workspace[2],
            disk_path=workspace[3],
            created_at=workspace[4],
            updated_at=workspace[5]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces")
async def list_workspaces():
    """Get all workspaces"""
    try:
        conn = memory.memory.conn

        workspaces = conn.execute("""
            SELECT id, name, source_type, disk_path, created_at, updated_at
            FROM code_editor_workspaces
            ORDER BY updated_at DESC
        """).fetchall()

        return {
            "workspaces": [
                {
                    "id": w[0],
                    "name": w[1],
                    "source_type": w[2],
                    "disk_path": w[3],
                    "created_at": w[4],
                    "updated_at": w[5]
                }
                for w in workspaces
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/files")
async def get_workspace_files(workspace_id: str):
    """Get file tree for workspace"""
    try:
        tree = build_file_tree(workspace_id)
        return {"files": [node.dict() for node in tree]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file(file_id: str):
    """Get file content"""
    try:
        conn = memory.memory.conn

        file = conn.execute("""
            SELECT id, workspace_id, name, path, content, language, created_at, updated_at
            FROM code_editor_files
            WHERE id = ?
        """, (file_id,)).fetchone()

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(
            id=file[0],
            workspace_id=file[1],
            name=file[2],
            path=file[3],
            content=file[4],
            language=file[5],
            created_at=file[6],
            updated_at=file[7]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files", response_model=FileResponse)
async def create_file(request: Request, file: FileCreate):
    """Create new file in workspace"""
    try:
        file_id = str(uuid.uuid4())
        conn = memory.memory.conn

        conn.execute("""
            INSERT INTO code_editor_files (id, workspace_id, name, path, content, language)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            file_id,
            file.workspace_id,
            file.name,
            file.path,
            file.content,
            file.language
        ))

        # Update workspace timestamp
        conn.execute("""
            UPDATE code_editor_workspaces
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (file.workspace_id,))

        conn.commit()

        # If disk workspace, also write to disk
        workspace = conn.execute("""
            SELECT source_type, disk_path
            FROM code_editor_workspaces
            WHERE id = ?
        """, (file.workspace_id,)).fetchone()

        if workspace and workspace[0] == 'disk' and workspace[1]:
            disk_file_path = Path(workspace[1]) / file.path
            disk_file_path.parent.mkdir(parents=True, exist_ok=True)
            disk_file_path.write_text(file.content, encoding='utf-8')

        # Return created file
        created_file = conn.execute("""
            SELECT id, workspace_id, name, path, content, language, created_at, updated_at
            FROM code_editor_files
            WHERE id = ?
        """, (file_id,)).fetchone()

        return FileResponse(
            id=created_file[0],
            workspace_id=created_file[1],
            name=created_file[2],
            path=created_file[3],
            content=created_file[4],
            language=created_file[5],
            created_at=created_file[6],
            updated_at=created_file[7]
        )

    except Exception as e:
        logger.error(f"Failed to create file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/files/{file_id}", response_model=FileResponse)
async def update_file(request: Request, file_id: str, file_update: FileUpdate):
    """Update file"""
    try:
        conn = memory.memory.conn

        # Get current file
        current = conn.execute("""
            SELECT workspace_id, name, path, content, language
            FROM code_editor_files
            WHERE id = ?
        """, (file_id,)).fetchone()

        if not current:
            raise HTTPException(status_code=404, detail="File not found")

        # Build update
        updates = []
        values = []

        if file_update.name is not None:
            updates.append("name = ?")
            values.append(file_update.name)
        if file_update.path is not None:
            updates.append("path = ?")
            values.append(file_update.path)
        if file_update.content is not None:
            updates.append("content = ?")
            values.append(file_update.content)
        if file_update.language is not None:
            updates.append("language = ?")
            values.append(file_update.language)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(file_id)

        conn.execute(f"""
            UPDATE code_editor_files
            SET {', '.join(updates)}
            WHERE id = ?
        """, values)

        # Update workspace timestamp
        conn.execute("""
            UPDATE code_editor_workspaces
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (current[0],))

        conn.commit()

        # If disk workspace, also write to disk
        workspace = conn.execute("""
            SELECT source_type, disk_path
            FROM code_editor_workspaces
            WHERE id = ?
        """, (current[0],)).fetchone()

        if workspace and workspace[0] == 'disk' and workspace[1]:
            new_path = file_update.path if file_update.path is not None else current[2]
            new_content = file_update.content if file_update.content is not None else current[3]

            disk_file_path = Path(workspace[1]) / new_path
            disk_file_path.parent.mkdir(parents=True, exist_ok=True)
            disk_file_path.write_text(new_content, encoding='utf-8')

            # If path changed, delete old file
            if file_update.path is not None and file_update.path != current[2]:
                old_path = Path(workspace[1]) / current[2]
                if old_path.exists():
                    old_path.unlink()

        # Return updated file
        updated_file = conn.execute("""
            SELECT id, workspace_id, name, path, content, language, created_at, updated_at
            FROM code_editor_files
            WHERE id = ?
        """, (file_id,)).fetchone()

        return FileResponse(
            id=updated_file[0],
            workspace_id=updated_file[1],
            name=updated_file[2],
            path=updated_file[3],
            content=updated_file[4],
            language=updated_file[5],
            created_at=updated_file[6],
            updated_at=updated_file[7]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}")
async def delete_file(request: Request, file_id: str):
    """Delete file"""
    try:
        conn = memory.memory.conn

        # Get file info before deletion
        file_info = conn.execute("""
            SELECT workspace_id, path
            FROM code_editor_files
            WHERE id = ?
        """, (file_id,)).fetchone()

        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")

        workspace_id, file_path = file_info

        # Delete from database
        conn.execute("DELETE FROM code_editor_files WHERE id = ?", (file_id,))

        # Update workspace timestamp
        conn.execute("""
            UPDATE code_editor_workspaces
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (workspace_id,))

        conn.commit()

        # If disk workspace, also delete from disk
        workspace = conn.execute("""
            SELECT source_type, disk_path
            FROM code_editor_workspaces
            WHERE id = ?
        """, (workspace_id,)).fetchone()

        if workspace and workspace[0] == 'disk' and workspace[1]:
            disk_file_path = Path(workspace[1]) / file_path
            if disk_file_path.exists():
                disk_file_path.unlink()

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/import")
async def import_file(
    request: Request,
    workspace_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Import file into workspace"""
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')

        # Detect language
        ext = Path(file.filename).suffix.lower()
        lang_map = {
            '.js': 'javascript', '.ts': 'typescript', '.py': 'python',
            '.java': 'java', '.cpp': 'cpp', '.go': 'go', '.rs': 'rust',
            '.html': 'html', '.css': 'css', '.json': 'json',
            '.md': 'markdown', '.yaml': 'yaml', '.yml': 'yaml',
        }
        language = lang_map.get(ext, 'plaintext')

        # Create file
        file_create = FileCreate(
            workspace_id=workspace_id,
            name=file.filename,
            path=file.filename,
            content=content_str,
            language=language
        )

        return await create_file(file_create)

    except Exception as e:
        logger.error(f"Failed to import file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/sync")
async def sync_workspace(request: Request, workspace_id: str):
    """Sync disk workspace with filesystem"""
    try:
        conn = memory.memory.conn

        workspace = conn.execute("""
            SELECT source_type, disk_path
            FROM code_editor_workspaces
            WHERE id = ?
        """, (workspace_id,)).fetchone()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        if workspace[0] != 'disk':
            raise HTTPException(status_code=400, detail="Only disk workspaces can be synced")

        if not workspace[1]:
            raise HTTPException(status_code=400, detail="No disk path configured")

        # Rescan directory
        files = scan_disk_directory(workspace[1])

        # Clear existing files
        conn.execute("DELETE FROM code_editor_files WHERE workspace_id = ?", (workspace_id,))

        # Re-import files
        for file_data in files:
            file_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO code_editor_files (id, workspace_id, name, path, content, language)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                workspace_id,
                file_data['name'],
                file_data['path'],
                file_data['content'],
                file_data['language']
            ))

        # Update workspace timestamp
        conn.execute("""
            UPDATE code_editor_workspaces
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (workspace_id,))

        conn.commit()

        return {"success": True, "files_synced": len(files)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
