"""
Code Operations API - Thin Router Layer
File browsing and operations for Code Tab
Delegates to services/code_editor for business logic
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from api.config_paths import PATHS

logger = logging.getLogger(__name__)

# Import auth middleware
from api.auth_middleware import get_current_user
from api.permission_engine import require_perm

try:
    from api.audit_logger import log_action
except ImportError:
    # Fallback: no-op audit logging
    async def log_action(**kwargs: Any) -> None:
        pass

# Import service layer
try:
    from api.services import code_editor as code_service
except ImportError:
    from services import code_editor as code_service

# Import permission layer and rate limiter
from api.permission_layer import PermissionLayer, RiskLevel
from api.rate_limiter import rate_limiter

# Initialize router
router = APIRouter(prefix="/api/v1/code", tags=["code"])

# Initialize permission layer for file operations
permission_layer = PermissionLayer(
    config_path=str(PATHS.data_dir / "code_permissions.json"),
    non_interactive=True,
    non_interactive_policy="conservative"
)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "code_operations",
        "workspace_base": str(code_service.get_code_workspace_base())
    }


# ============================================================================
# FILE TREE OPERATIONS
# ============================================================================

@router.get("/files")
async def get_file_tree(
    path: str = ".",
    recursive: bool = True,
    absolute_path: str = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get file tree for user's code workspace or validated absolute path
    Security: absolute_path is restricted to code_workspaces
    """
    try:
        user_id = current_user["user_id"]
        logger.info(f"[CODE] GET /files - user_id={user_id}, path={path}, absolute_path={absolute_path}, recursive={recursive}")

        # Get user workspace for validation
        user_workspace = code_service.get_user_workspace(user_id)

        # Determine target path
        if absolute_path:
            target_path = Path(absolute_path).resolve()

            # Security: Validate absolute_path is within workspace
            try:
                from .config_paths import get_config_paths
            except ImportError:
                from config_paths import get_config_paths

            PATHS = get_config_paths()
            user_workspace_root = PATHS.data_dir / "code_workspaces" / user_id

            try:
                target_path.relative_to(user_workspace_root)
            except ValueError:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: absolute_path must be within workspace ({user_workspace_root})"
                )

            if not target_path.exists():
                raise HTTPException(404, "Path not found")
            if not target_path.is_dir():
                raise HTTPException(400, "Path is not a directory")
        else:
            # Use workspace-relative path
            target_path = user_workspace if path == "." else user_workspace / path

            # Security: validate path within workspace
            if not code_service.is_safe_path(target_path, user_workspace):
                raise HTTPException(400, "Invalid path")

        if not target_path.exists():
            raise HTTPException(404, "Path not found")

        # Delegate to service
        tree = code_service.walk_directory(
            target_path,
            recursive=recursive,
            include_files=True,
            include_dirs=True,
            base_path=target_path
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


# ============================================================================
# FILE READ OPERATIONS
# ============================================================================

@router.get("/read")
async def read_file(
    path: str,
    offset: int = 1,
    limit: int = 2000,
    absolute_path: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Read file content with line numbers
    Supports offset and limit for large files
    Security: absolute_path is restricted to code_workspaces
    """
    try:
        user_id = current_user["user_id"]
        user_workspace = code_service.get_user_workspace(user_id)

        # Resolve file path
        if absolute_path or path.startswith('/'):
            file_path = Path(path).resolve()

            # Security: Validate absolute path is within workspace
            try:
                from .config_paths import get_config_paths
            except ImportError:
                from config_paths import get_config_paths

            PATHS = get_config_paths()
            user_workspace_root = PATHS.data_dir / "code_workspaces" / user_id

            try:
                file_path.relative_to(user_workspace_root)
            except ValueError:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: file must be within workspace ({user_workspace_root})"
                )
        else:
            # Use workspace-relative path
            file_path = user_workspace / path

            # Security: validate path within workspace
            if not code_service.is_safe_path(file_path, user_workspace):
                raise HTTPException(400, "Invalid path")

        if not file_path.exists():
            raise HTTPException(404, "File not found")

        if not file_path.is_file():
            raise HTTPException(400, "Not a file")

        # Risk assessment (orchestration layer)
        risk_level, risk_reason = permission_layer.assess_risk(
            f"read {file_path}",
            "file_read"
        )

        if risk_level == RiskLevel.CRITICAL:
            raise HTTPException(403, f"File access denied: {risk_reason}")

        # Read file with line numbers
        lines = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    if line_num < offset:
                        continue

                    if len(lines) >= limit:
                        break

                    lines.append(f"L{line_num}: {line.rstrip()}")

        except UnicodeDecodeError:
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


# ============================================================================
# WORKSPACE INFO
# ============================================================================

@router.get("/workspace/info")
async def get_workspace_info(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get information about user's code workspace"""
    try:
        user_id = current_user["user_id"]
        user_workspace = code_service.get_user_workspace(user_id)

        # Count files and directories
        import os
        file_count = 0
        dir_count = 0
        total_size = 0

        for root, dirs, files in os.walk(user_workspace):
            # Filter ignored paths
            dirs[:] = [d for d in dirs if not code_service.should_ignore(Path(root) / d)]
            files = [f for f in files if not code_service.should_ignore(Path(root) / f)]

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
# DIFF OPERATIONS
# ============================================================================

@router.post("/diff/preview")
async def preview_diff(
    request: code_service.DiffPreviewRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Preview changes before saving
    Shows unified diff of changes
    """
    try:
        user_id = current_user["user_id"]
        user_workspace = code_service.get_user_workspace(user_id)
        file_path = user_workspace / request.path

        # Security check
        if not code_service.is_safe_path(file_path, user_workspace):
            raise HTTPException(400, "Invalid path")

        # Read original content
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        else:
            original_content = ""

        # Delegate diff generation to service
        diff_text = code_service.generate_unified_diff(
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


# ============================================================================
# WRITE OPERATIONS
# ============================================================================

@router.post("/write")
async def write_file(
    request: code_service.WriteFileRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Write file with permission checking and rate limiting
    Rate limited: 30 writes/min per user
    """
    user_id = current_user["user_id"]

    # Rate limiting (orchestration layer)
    if not rate_limiter.check_rate_limit(
        f"code:write:{user_id}",
        max_requests=30,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many write requests. Please slow down.")

    try:
        user_workspace = code_service.get_user_workspace(user_id)
        file_path = user_workspace / request.path

        # Security check
        if not code_service.is_safe_path(file_path, user_workspace):
            raise HTTPException(400, "Invalid path")

        # Check if creating new file
        is_new_file = not file_path.exists()

        if is_new_file and not request.create_if_missing:
            raise HTTPException(404, "File does not exist. Set create_if_missing=true to create.")

        # Risk assessment (orchestration layer)
        operation = "create file" if is_new_file else "modify file"
        risk_level, risk_reason = permission_layer.assess_risk(
            f"{operation} {file_path}",
            "file_write"
        )

        if risk_level == RiskLevel.CRITICAL:
            raise HTTPException(403, f"Write operation denied: {risk_reason}")

        if risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM]:
            logger.warning(f"High/medium risk write operation: {file_path} - {risk_reason}")

        # Delegate to service
        code_service.write_file_to_disk(file_path, request.content)

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


# ============================================================================
# DELETE OPERATIONS
# ============================================================================

@router.delete("/delete")
async def delete_file(
    path: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Delete file with permission checking and rate limiting
    Rate limited: 20 deletes/min per user
    """
    user_id = current_user["user_id"]

    # Rate limiting (orchestration layer)
    if not rate_limiter.check_rate_limit(
        f"code:delete:{user_id}",
        max_requests=20,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many delete requests. Please slow down.")

    try:
        user_workspace = code_service.get_user_workspace(user_id)
        file_path = user_workspace / path

        # Security check
        if not code_service.is_safe_path(file_path, user_workspace):
            raise HTTPException(400, "Invalid path")

        if not file_path.exists():
            raise HTTPException(404, "File not found")

        # Risk assessment (orchestration layer)
        risk_level, risk_reason = permission_layer.assess_risk(
            f"rm {file_path}",
            "file_delete"
        )

        if risk_level == RiskLevel.CRITICAL:
            raise HTTPException(403, f"Delete operation denied: {risk_reason}")

        # Delegate to service
        if file_path.is_file():
            code_service.delete_file_from_disk(file_path)
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
# PROJECT LIBRARY
# ============================================================================

import sqlite3
from datetime import datetime
from pydantic import BaseModel

class ProjectLibraryDocument(BaseModel):
    name: str
    content: str
    tags: List[str] = []
    file_type: str = "markdown"


class UpdateDocumentRequest(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


def get_library_db_path() -> Path:
    """Get path to project library database"""
    db_path = PATHS.data_dir / "project_library.db"
    return db_path


def init_library_db() -> None:
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
            tags TEXT NOT NULL,
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
async def get_library_documents(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Get all project library documents"""
    try:
        import json
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
async def create_library_document(doc: ProjectLibraryDocument, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Create new project library document"""
    try:
        import json
        user_id = current_user["user_id"]
        db_path = get_library_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

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
async def update_library_document(doc_id: int, update: UpdateDocumentRequest, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, bool]:
    """Update project library document"""
    try:
        import json
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
async def delete_library_document(doc_id: int, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, bool]:
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
# GIT OPERATIONS
# ============================================================================

import subprocess
from datetime import datetime as dt


class WorkspaceRootRequest(BaseModel):
    workspace_root: str


@router.post("/workspace/set")
async def set_workspace_root(request: WorkspaceRootRequest) -> Dict[str, Any]:
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
async def get_git_log(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get git commit history from the currently opened project folder
    Returns commits from the workspace root stored in localStorage
    """
    try:
        user_id = current_user["user_id"]

        # Get workspace root from marker file
        workspace_root = None

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
                    'date': parts[5],
                    'timestamp': int(parts[6]),
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
