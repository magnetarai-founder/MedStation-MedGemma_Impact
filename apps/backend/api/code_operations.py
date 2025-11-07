"""
Code Operations API - File browsing and operations for Code Tab
Uses patterns from Continue's proven file operations
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from pathlib import Path
import os
import logging

from config_paths import PATHS

# Import auth middleware
try:
    from auth_middleware import get_current_user
except ImportError:
    from .auth_middleware import get_current_user

try:
    from permission_engine import require_perm
except ImportError:
    from .permission_engine import require_perm

try:
    from audit_logger import log_action
except ImportError:
    # Fallback: no-op audit logging
    async def log_action(**kwargs):
        pass

from permission_layer import PermissionLayer, RiskLevel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/code", tags=["code"])


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "code_operations",
        "workspace_base": str(get_code_workspace_base())
    }


# Initialize permission layer for file operations
permission_layer = PermissionLayer(
    config_path=str(PATHS.data_dir / "code_permissions.json"),
    non_interactive=True,
    non_interactive_policy="conservative"
)

# Code workspace base path (under .neutron_data)
def get_code_workspace_base() -> Path:
    """Get the base path for code workspaces"""
    workspace_path = PATHS.data_dir / "code_workspaces"
    workspace_path.mkdir(exist_ok=True, parents=True)
    return workspace_path


def get_user_workspace(user_id: str) -> Path:
    """Get user's code workspace directory"""
    user_workspace = get_code_workspace_base() / user_id
    user_workspace.mkdir(exist_ok=True, parents=True)
    return user_workspace


def is_safe_path(path: Path, base: Path) -> bool:
    """
    Prevent directory traversal attacks
    From Continue's security patterns
    """
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def should_ignore(path: Path) -> bool:
    """
    Check if path should be ignored (adapted from Continue's shouldIgnore)
    """
    ignore_patterns = [
        'node_modules',
        '.git',
        '__pycache__',
        '.venv',
        'venv',
        '.env',
        'dist',
        'build',
        '.next',
        '.cache',
        'coverage',
        '.DS_Store',
        '*.pyc',
        '*.pyo',
        '*.so',
        '*.dylib',
        '.egg-info'
    ]

    path_str = str(path)
    for pattern in ignore_patterns:
        if pattern in path_str:
            return True

    return False


def walk_directory(
    directory: Path,
    recursive: bool = True,
    include_files: bool = True,
    include_dirs: bool = False,
    base_path: Path = None
) -> List[Dict[str, Any]]:
    """
    Walk directory and return file tree (adapted from Continue's walkDir)
    """
    items = []

    # Use provided base_path or default to workspace base
    if base_path is None:
        base_path = directory

    try:
        for entry in directory.iterdir():
            # Skip ignored paths
            if should_ignore(entry):
                continue

            is_dir = entry.is_dir()

            # Skip symlinks (security)
            if entry.is_symlink():
                continue

            item = {
                'name': entry.name,
                'type': 'directory' if is_dir else 'file',
                'path': str(entry.relative_to(base_path)),
            }

            if is_dir:
                # Recursively get children if recursive mode
                if recursive:
                    item['children'] = walk_directory(
                        entry,
                        recursive=True,
                        include_files=include_files,
                        include_dirs=True,  # Always include dirs in children
                        base_path=base_path
                    )
                # Always add directories to items
                items.append(item)
            else:
                if include_files:
                    # Add file metadata
                    try:
                        stat = entry.stat()
                        item['size'] = stat.st_size
                        item['modified'] = stat.st_mtime
                    except Exception:
                        pass
                    items.append(item)

    except PermissionError:
        logger.warning(f"Permission denied accessing {directory}")
    except Exception as e:
        logger.error(f"Error walking directory {directory}: {e}")

    # Sort: directories first, then files, both alphabetically
    items.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))

    return items


@router.get("/files")
async def get_file_tree(
    path: str = ".",
    recursive: bool = True,
    absolute_path: str = None,  # Allow absolute path only within allowed roots
    current_user: Dict = Depends(get_current_user)
):
    """
    Get file tree for user's code workspace or validated absolute path

    Security: absolute_path is restricted to code_workspaces and home directory
    """
    try:
        user_id = current_user["user_id"]
        logger.info(f"[CODE] GET /files - user_id={user_id}, path={path}, absolute_path={absolute_path}, recursive={recursive}")

        # Get user workspace for validation
        user_workspace = get_user_workspace(user_id)

        # If absolute_path provided, validate it's within allowed roots
        if absolute_path:
            target_path = Path(absolute_path).resolve()

            # Security: Validate absolute_path is within allowed roots
            try:
                from .config_paths import get_config_paths
            except ImportError:
                from config_paths import get_config_paths

            PATHS = get_config_paths()
            user_workspace_root = PATHS.data_dir / "code_workspaces" / user_id
            allowed_roots = [user_workspace_root, Path.home()]

            is_allowed = False
            for allowed_root in allowed_roots:
                try:
                    target_path.relative_to(allowed_root)
                    is_allowed = True
                    break
                except ValueError:
                    continue

            if not is_allowed:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: absolute_path must be within workspace ({user_workspace_root}) or home directory"
                )

            if not target_path.exists():
                raise HTTPException(404, "Path not found")
            if not target_path.is_dir():
                raise HTTPException(400, "Path is not a directory")
        else:
            # Use workspace-relative path
            target_path = user_workspace if path == "." else user_workspace / path

            # Security: validate path within workspace
            if not is_safe_path(target_path, user_workspace):
                raise HTTPException(400, "Invalid path")

        if not target_path.exists():
            raise HTTPException(404, "Path not found")

        # Walk directory
        tree = walk_directory(
            target_path,
            recursive=recursive,
            include_files=True,
            include_dirs=True,
            base_path=target_path  # Use target as base for relative paths
        )

        # Audit log
        await log_action(
            user_id=user_id,
            action="code.files.list",
            resource=str(target_path),
            details={'count': len(tree), 'recursive': recursive}
        )

        return {
            'path': path,
            'items': tree
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file tree: {e}")
        raise HTTPException(500, f"Failed to get file tree: {str(e)}")


@router.get("/read")
async def read_file(
    path: str,
    offset: int = 1,
    limit: int = 2000,
    absolute_path: bool = False,  # Allow absolute path only within allowed roots
    current_user: Dict = Depends(get_current_user)
):
    """
    Read file content (adapted from Codex's read_file with line numbers)
    Supports offset and limit for large files

    Security: absolute_path is restricted to code_workspaces and home directory
    """
    try:
        user_id = current_user["user_id"]
        user_workspace = get_user_workspace(user_id)

        # Resolve file path
        if absolute_path or path.startswith('/'):
            file_path = Path(path).resolve()

            # Security: Validate absolute path is within allowed roots
            try:
                from .config_paths import get_config_paths
            except ImportError:
                from config_paths import get_config_paths

            PATHS = get_config_paths()
            user_workspace_root = PATHS.data_dir / "code_workspaces" / user_id
            allowed_roots = [user_workspace_root, Path.home()]

            is_allowed = False
            for allowed_root in allowed_roots:
                try:
                    file_path.relative_to(allowed_root)
                    is_allowed = True
                    break
                except ValueError:
                    continue

            if not is_allowed:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: file must be within workspace ({user_workspace_root}) or home directory"
                )
        else:
            # Use workspace-relative path
            file_path = user_workspace / path

            # Security: validate path within workspace
            if not is_safe_path(file_path, user_workspace):
                raise HTTPException(400, "Invalid path")

        if not file_path.exists():
            raise HTTPException(404, "File not found")

        if not file_path.is_file():
            raise HTTPException(400, "Not a file")

        # Check permissions using Jarvis permission layer
        risk_level, risk_reason = permission_layer.assess_risk(
            f"read {file_path}",
            "file_read"
        )

        if risk_level == RiskLevel.CRITICAL:
            raise HTTPException(403, f"File access denied: {risk_reason}")

        # Read file with line numbers (Codex pattern)
        lines = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    # Skip lines before offset
                    if line_num < offset:
                        continue

                    # Stop at limit
                    if len(lines) >= limit:
                        break

                    # Add line with number (Codex format: "L123: content")
                    lines.append(f"L{line_num}: {line.rstrip()}")

        except UnicodeDecodeError:
            # Binary file
            raise HTTPException(400, "Cannot read binary file")

        # Audit log
        await log_action(
            user_id=user_id,
            action="code.file.read",
            resource=str(file_path),
            details={
                'size': file_path.stat().st_size,
                'lines_read': len(lines),
                'offset': offset,
                'limit': limit
            }
        )

        return {
            'path': path,
            'content': '\n'.join(lines),
            'lines': lines,
            'total_lines': len(lines),
            'offset': offset,
            'has_more': len(lines) == limit
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(500, f"Failed to read file: {str(e)}")


@router.get("/workspace/info")
async def get_workspace_info(current_user: Dict = Depends(get_current_user)):
    """
    Get information about user's code workspace
    """
    try:
        user_id = current_user["user_id"]
        user_workspace = get_user_workspace(user_id)

        # Count files and directories
        file_count = 0
        dir_count = 0
        total_size = 0

        for root, dirs, files in os.walk(user_workspace):
            # Filter ignored paths
            dirs[:] = [d for d in dirs if not should_ignore(Path(root) / d)]
            files = [f for f in files if not should_ignore(Path(root) / f)]

            dir_count += len(dirs)
            file_count += len(files)

            for file in files:
                try:
                    total_size += (Path(root) / file).stat().st_size
                except Exception:
                    pass

        return {
            'workspace_path': str(user_workspace),
            'file_count': file_count,
            'directory_count': dir_count,
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }

    except Exception as e:
        logger.error(f"Error getting workspace info: {e}")
        raise HTTPException(500, f"Failed to get workspace info: {str(e)}")


# ============================================================================
# PHASE 3: WRITE OPERATIONS (with Diff Preview)
# ============================================================================

from pydantic import BaseModel
import difflib


class WriteFileRequest(BaseModel):
    path: str
    content: str
    create_if_missing: bool = False


class DiffPreviewRequest(BaseModel):
    path: str
    new_content: str


def generate_unified_diff(original: str, modified: str, filepath: str) -> str:
    """
    Generate unified diff (Continue's streamDiff pattern)
    """
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
        lineterm=''
    )

    return ''.join(diff)


@router.post("/diff/preview")
async def preview_diff(
    request: DiffPreviewRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Preview changes before saving (Continue's diff pattern)
    Shows unified diff of changes
    """
    try:
        user_id = current_user["user_id"]
        user_workspace = get_user_workspace(user_id)
        file_path = user_workspace / request.path

        # Security check
        if not is_safe_path(file_path, user_workspace):
            raise HTTPException(400, "Invalid path")

        # Read original content
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        else:
            original_content = ""

        # Generate diff
        diff_text = generate_unified_diff(
            original_content,
            request.new_content,
            request.path
        )

        # Count changes
        lines = diff_text.split('\n')
        additions = sum(1 for line in lines if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in lines if line.startswith('-') and not line.startswith('---'))

        return {
            'path': request.path,
            'diff': diff_text,
            'stats': {
                'additions': additions,
                'deletions': deletions,
                'total_changes': additions + deletions
            },
            'exists': file_path.exists()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating diff: {e}")
        raise HTTPException(500, f"Failed to generate diff: {str(e)}")


@router.post("/write")
async def write_file(
    request: WriteFileRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Write file with permission checking (Jarvis pattern)
    Phase 3: Full write operations
    """
    try:
        user_id = current_user["user_id"]
        user_workspace = get_user_workspace(user_id)
        file_path = user_workspace / request.path

        # Security check
        if not is_safe_path(file_path, user_workspace):
            raise HTTPException(400, "Invalid path")

        # Check if creating new file
        is_new_file = not file_path.exists()

        if is_new_file and not request.create_if_missing:
            raise HTTPException(404, "File does not exist. Set create_if_missing=true to create.")

        # Jarvis permission check with risk assessment
        operation = "create file" if is_new_file else "modify file"
        risk_level, risk_reason = permission_layer.assess_risk(
            f"{operation} {file_path}",
            "file_write"
        )

        if risk_level == RiskLevel.CRITICAL:
            raise HTTPException(403, f"Write operation denied: {risk_reason}")

        # High risk operations require explicit approval
        if risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM]:
            logger.warning(f"High/medium risk write operation: {file_path} - {risk_reason}")

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(request.content)

        # Audit log
        await log_action(
            user_id=user_id,
            action="code.file.write",
            resource=str(file_path),
            details={
                'operation': operation,
                'size': len(request.content),
                'risk_level': risk_level.label,
                'risk_reason': risk_reason
            }
        )

        return {
            'success': True,
            'path': request.path,
            'operation': operation,
            'size': len(request.content),
            'risk_assessment': {
                'level': risk_level.label,
                'reason': risk_reason
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error writing file: {e}")
        raise HTTPException(500, f"Failed to write file: {str(e)}")


@router.delete("/delete")
async def delete_file(
    path: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Delete file with Jarvis permission checking
    Phase 3: Destructive operations
    """
    try:
        user_id = current_user["user_id"]
        user_workspace = get_user_workspace(user_id)
        file_path = user_workspace / path

        # Security check
        if not is_safe_path(file_path, user_workspace):
            raise HTTPException(400, "Invalid path")

        if not file_path.exists():
            raise HTTPException(404, "File not found")

        # Jarvis permission check - DELETE is HIGH risk
        risk_level, risk_reason = permission_layer.assess_risk(
            f"rm {file_path}",
            "file_delete"
        )

        if risk_level == RiskLevel.CRITICAL:
            raise HTTPException(403, f"Delete operation denied: {risk_reason}")

        # Delete file
        if file_path.is_file():
            file_path.unlink()
        else:
            raise HTTPException(400, "Path is not a file")

        # Audit log
        await log_action(
            user_id=user_id,
            action="code.file.delete",
            resource=str(file_path),
            details={
                'risk_level': risk_level.label,
                'risk_reason': risk_reason
            }
        )

        return {
            'success': True,
            'path': path,
            'operation': 'delete',
            'risk_assessment': {
                'level': risk_level.label,
                'reason': risk_reason
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(500, f"Failed to delete file: {str(e)}")


# ============================================================================
# PROJECT LIBRARY: Knowledge Base for Code Projects
# ============================================================================

import sqlite3
from datetime import datetime

class ProjectLibraryDocument(BaseModel):
    name: str
    content: str
    tags: List[str] = []
    file_type: str = "markdown"  # "markdown" or "text"


class UpdateDocumentRequest(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


def get_library_db_path() -> Path:
    """Get path to project library database"""
    db_path = PATHS.data_dir / "project_library.db"
    return db_path


def init_library_db():
    """Initialize project library database"""
    db_path = get_library_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT NOT NULL,  -- JSON array
            file_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# Initialize on module load
init_library_db()


@router.get("/library")
async def get_library_documents(current_user: Dict = Depends(get_current_user)):
    """Get all project library documents"""
    try:
        user_id = current_user["user_id"]
        db_path = get_library_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, content, tags, file_type, created_at, updated_at
            FROM documents
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """, (user_id,))

        documents = []
        for row in cursor.fetchall():
            import json
            documents.append({
                'id': row[0],
                'name': row[1],
                'content': row[2],
                'tags': json.loads(row[3]),
                'file_type': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            })

        conn.close()
        return documents

    except Exception as e:
        logger.error(f"Error getting library documents: {e}")
        raise HTTPException(500, f"Failed to get library documents: {str(e)}")


@router.post("/library")
async def create_library_document(doc: ProjectLibraryDocument, current_user: Dict = Depends(get_current_user)):
    """Create new project library document"""
    try:
        user_id = current_user["user_id"]
        db_path = get_library_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        import json
        cursor.execute("""
            INSERT INTO documents (user_id, name, content, tags, file_type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            doc.name,
            doc.content,
            json.dumps(doc.tags),
            doc.file_type,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        doc_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Audit log
        await log_action(
            user_id=user_id,
            action="code.library.create",
            resource=doc.name,
            details={'id': doc_id, 'tags': doc.tags}
        )

        return {'id': doc_id, 'success': True}

    except Exception as e:
        logger.error(f"Error creating library document: {e}")
        raise HTTPException(500, f"Failed to create library document: {str(e)}")


@router.patch("/library/{doc_id}")
async def update_library_document(doc_id: int, update: UpdateDocumentRequest, current_user: Dict = Depends(get_current_user)):
    """Update project library document"""
    try:
        user_id = current_user["user_id"]
        db_path = get_library_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Build update query
        updates = []
        params = []

        if update.name is not None:
            updates.append("name = ?")
            params.append(update.name)

        if update.content is not None:
            updates.append("content = ?")
            params.append(update.content)

        if update.tags is not None:
            import json
            updates.append("tags = ?")
            params.append(json.dumps(update.tags))

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())

        params.extend([user_id, doc_id])

        cursor.execute(f"""
            UPDATE documents
            SET {', '.join(updates)}
            WHERE user_id = ? AND id = ?
        """, params)

        conn.commit()
        conn.close()

        # Audit log
        await log_action(
            user_id=user_id,
            action="code.library.update",
            resource=str(doc_id),
            details=update.dict(exclude_none=True)
        )

        return {'success': True}

    except Exception as e:
        logger.error(f"Error updating library document: {e}")
        raise HTTPException(500, f"Failed to update library document: {str(e)}")


@router.delete("/library/{doc_id}")
async def delete_library_document(doc_id: int, current_user: Dict = Depends(get_current_user)):
    """Delete project library document"""
    try:
        user_id = current_user["user_id"]
        db_path = get_library_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM documents
            WHERE user_id = ? AND id = ?
        """, (user_id, doc_id))

        conn.commit()
        conn.close()

        # Audit log
        await log_action(
            user_id=user_id,
            action="code.library.delete",
            resource=str(doc_id)
        )

        return {'success': True}

    except Exception as e:
        logger.error(f"Error deleting library document: {e}")
        raise HTTPException(500, f"Failed to delete library document: {str(e)}")


# ============================================================================
# GIT OPERATIONS: Repository info for opened project folders
# ============================================================================

import subprocess
from datetime import datetime as dt


class WorkspaceRootRequest(BaseModel):
    workspace_root: str


@router.post("/workspace/set")
async def set_workspace_root(request: WorkspaceRootRequest):
    """
    Set the current workspace root path
    Frontend calls this when user opens a folder
    """
    try:
        workspace_path = Path(request.workspace_root)

        # Validate path exists
        if not workspace_path.exists():
            raise HTTPException(400, "Workspace path does not exist")

        if not workspace_path.is_dir():
            raise HTTPException(400, "Workspace path must be a directory")

        # Write to marker file
        marker_file = PATHS.data_dir / "current_workspace.txt"
        marker_file.write_text(str(workspace_path.resolve()))

        return {
            'success': True,
            'workspace_root': str(workspace_path.resolve())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting workspace root: {e}")
        raise HTTPException(500, f"Failed to set workspace root: {str(e)}")


@router.get("/git/log")
async def get_git_log(current_user: Dict = Depends(get_current_user)):
    """
    Get git commit history from the currently opened project folder
    Returns commits from the workspace root stored in localStorage
    """
    try:
        user_id = current_user["user_id"]

        # Try to get workspace root from environment or use default
        # The frontend stores this in localStorage as 'ns.code.workspaceRoot'
        # For backend, we'll look for a git repo in the user's workspace

        # Try common locations or use a marker file
        workspace_root = None

        # Option 1: Check for a marker file that frontend writes
        marker_file = PATHS.data_dir / "current_workspace.txt"
        if marker_file.exists():
            workspace_root = marker_file.read_text().strip()

        if not workspace_root:
            # No workspace opened yet
            return {
                'commits': [],
                'branch': None,
                'error': 'No workspace opened'
            }

        workspace_path = Path(workspace_root)

        # Check if it's a git repository
        git_dir = workspace_path / '.git'
        if not git_dir.exists():
            return {
                'commits': [],
                'branch': None,
                'error': 'Not a git repository'
            }

        # Get current branch
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=str(workspace_path),
            capture_output=True,
            text=True,
            timeout=5
        )
        current_branch = branch_result.stdout.strip() or 'main'

        # Get git log (last 50 commits)
        log_result = subprocess.run(
            [
                'git', 'log',
                '--pretty=format:%H|%h|%s|%an|%ae|%ar|%at',
                '-n', '50'
            ],
            cwd=str(workspace_path),
            capture_output=True,
            text=True,
            timeout=10
        )

        if log_result.returncode != 0:
            raise Exception(f"Git log failed: {log_result.stderr}")

        # Parse commits
        commits = []
        for line in log_result.stdout.strip().split('\n'):
            if not line:
                continue

            parts = line.split('|')
            if len(parts) >= 7:
                commits.append({
                    'hash': parts[0],
                    'short_hash': parts[1],
                    'message': parts[2],
                    'author': parts[3],
                    'author_email': parts[4],
                    'date': parts[5],  # relative (e.g., "2 hours ago")
                    'timestamp': int(parts[6]),  # unix timestamp
                    'branch': current_branch
                })

        return {
            'commits': commits,
            'branch': current_branch,
            'workspace_root': str(workspace_path)
        }

    except subprocess.TimeoutExpired:
        logger.error("Git command timed out")
        raise HTTPException(500, "Git operation timed out")
    except Exception as e:
        logger.error(f"Error getting git log: {e}")
        return {
            'commits': [],
            'branch': None,
            'error': str(e)
        }
