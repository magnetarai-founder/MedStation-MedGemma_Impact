"""
Code Editor Service - Thin Router Layer
Delegates to services/code_editor for all business logic
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Depends

from api.routes.schemas.responses import SuccessResponse

logger = logging.getLogger(__name__)

# Import service layer with fallback
try:
    from api.services import code_editor as code_service
except ImportError:
    from services import code_editor as code_service

# Import auth and permissions
from fastapi import Depends
from api.auth_middleware import get_current_user
from api.permission_engine import require_perm
from api.audit_logger import get_audit_logger, AuditAction

# Initialize router
router = APIRouter(
    prefix="/api/v1/code-editor",
    tags=["code-editor"],
    dependencies=[Depends(get_current_user)]  # Require auth
)

# Initialize code editor database tables
code_service.init_code_editor_db()


# ============================================================================
# WORKSPACE ENDPOINTS
# ============================================================================

@router.post("/workspaces", response_model=SuccessResponse[code_service.WorkspaceResponse])
@require_perm("code.edit")
async def create_workspace(
    request: Request,
    workspace: code_service.WorkspaceCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new database workspace"""
    try:
        if workspace.source_type != 'database':
            raise HTTPException(status_code=400, detail="Only database workspaces can be created this way")

        # Delegate to service
        result = code_service.create_workspace(workspace.name, workspace.source_type)

        # Audit log
        try:
            audit_logger = get_audit_logger()
            audit_logger.log(
                user_id=current_user.get("user_id"),
                action=AuditAction.CODE_WORKSPACE_CREATED,
                resource="code_workspace",
                resource_id=result.id,
                details={"name": workspace.name, "source_type": "database"}
            )
        except Exception as audit_error:
            logger.warning(f"Audit logging failed: {audit_error}")

        return SuccessResponse(data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/open-disk", response_model=SuccessResponse[code_service.WorkspaceResponse])
@require_perm("code.edit")
async def open_disk_workspace(
    request: Request,
    name: str = Form(...),
    disk_path: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Open folder from disk and create workspace"""
    try:
        from pathlib import Path

        # Validate path exists
        path = Path(disk_path)
        if not path.exists() or not path.is_dir():
            raise HTTPException(status_code=400, detail="Invalid directory path")

        # Scan and import files
        files = code_service.scan_disk_directory(str(path))
        logger.info(f"Found {len(files)} files in {disk_path}")

        # Create workspace with files
        result = code_service.create_workspace(
            name=name,
            source_type='disk',
            disk_path=str(path.absolute()),
            files=files
        )

        # Audit log
        try:
            audit_logger = get_audit_logger()
            audit_logger.log(
                user_id=current_user.get("user_id"),
                action=AuditAction.CODE_WORKSPACE_CREATED,
                resource="code_workspace",
                resource_id=result.id,
                details={
                    "name": name,
                    "source_type": "disk",
                    "disk_path": str(path.absolute()),
                    "files_imported": len(files)
                }
            )
        except Exception as audit_error:
            logger.warning(f"Audit logging failed: {audit_error}")

        return SuccessResponse(data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to open disk workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/open-database", response_model=SuccessResponse[code_service.WorkspaceResponse])
@require_perm("code.use")
async def open_database_workspace(
    request: Request,
    workspace_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Open existing workspace from database"""
    try:
        # Delegate to service
        workspace = code_service.get_workspace(workspace_id)

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        return SuccessResponse(data=workspace)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces", response_model=SuccessResponse[code_service.WorkspacesListResponse])
@require_perm("code.use")
async def list_workspaces(current_user: dict = Depends(get_current_user)):
    """Get all workspaces"""
    try:
        # Delegate to service (already returns List[WorkspaceResponse])
        workspaces = code_service.list_workspaces()

        return SuccessResponse(
            data=code_service.WorkspacesListResponse(workspaces=workspaces)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/files", response_model=SuccessResponse[code_service.FilesListResponse])
@require_perm("code.use")
async def get_workspace_files(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """Get file tree for workspace"""
    try:
        # Delegate to service
        tree = code_service.build_file_tree(workspace_id)
        return SuccessResponse(
            data=code_service.FilesListResponse(files=tree)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/sync")
@require_perm("code.edit")
async def sync_workspace(
    request: Request,
    workspace_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Sync disk workspace with filesystem"""
    try:
        # Get workspace
        workspace = code_service.get_workspace(workspace_id)

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        if workspace.source_type != 'disk':
            raise HTTPException(status_code=400, detail="Only disk workspaces can be synced")

        if not workspace.disk_path:
            raise HTTPException(status_code=400, detail="No disk path configured")

        # Rescan directory
        files = code_service.scan_disk_directory(workspace.disk_path)

        # Clear and re-import files
        code_service.delete_files_by_workspace(workspace_id)

        for file_data in files:
            code_service.create_file(
                workspace_id=workspace_id,
                name=file_data['name'],
                path=file_data['path'],
                content=file_data['content'],
                language=file_data['language']
            )

        # Update workspace timestamp
        code_service.update_workspace_timestamp(workspace_id)

        # Audit log
        try:
            audit_logger = get_audit_logger()
            audit_logger.log(
                user_id=current_user.get("user_id"),
                action=AuditAction.CODE_WORKSPACE_SYNCED,
                resource="code_workspace",
                resource_id=workspace_id,
                details={"files_synced": len(files), "disk_path": workspace.disk_path}
            )
        except Exception as audit_error:
            logger.warning(f"Audit logging failed: {audit_error}")

        return {"success": True, "files_synced": len(files)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FILE ENDPOINTS
# ============================================================================

@router.get("/files/{file_id}", response_model=SuccessResponse[code_service.FileResponse])
@require_perm("code.use")
async def get_file(file_id: str, current_user: dict = Depends(get_current_user)):
    """Get file content"""
    try:
        # Delegate to service
        file = code_service.get_file(file_id)

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        return SuccessResponse(data=file)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/{file_id}/diff", response_model=SuccessResponse[code_service.FileDiffResponse])
@require_perm("code.use")
async def get_file_diff(
    file_id: str,
    diff_request: code_service.FileDiffRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate unified diff between current file content and proposed new content.
    Optionally detects conflicts if base_updated_at is provided.
    Truncates large diffs with flags.
    """
    try:
        # Delegate to service
        result = code_service.generate_file_diff(
            file_id=file_id,
            new_content=diff_request.new_content,
            base_updated_at=diff_request.base_updated_at
        )

        return SuccessResponse(data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate diff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files", response_model=SuccessResponse[code_service.FileResponse])
@require_perm("code.edit")
async def create_file(
    request: Request,
    file: code_service.FileCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create new file in workspace"""
    try:
        from pathlib import Path

        # Create file in database
        result = code_service.create_file(
            workspace_id=file.workspace_id,
            name=file.name,
            path=file.path,
            content=file.content,
            language=file.language
        )

        # Update workspace timestamp
        code_service.update_workspace_timestamp(file.workspace_id)

        # If disk workspace, also write to disk
        workspace = code_service.get_workspace(file.workspace_id)
        if workspace and workspace.source_type == 'disk' and workspace.disk_path:
            workspace_root = Path(workspace.disk_path)
            disk_file_path = workspace_root / file.path

            # Path guard: ensure file is under workspace root
            code_service.ensure_under_root(workspace_root, disk_file_path)

            disk_file_path.parent.mkdir(parents=True, exist_ok=True)
            disk_file_path.write_text(file.content, encoding='utf-8')

        # Audit log
        try:
            audit_logger = get_audit_logger()
            audit_logger.log(
                user_id=current_user.get("user_id"),
                action=AuditAction.CODE_FILE_CREATED,
                resource="code_file",
                resource_id=result.id,
                details={"workspace_id": file.workspace_id, "path": file.path, "name": file.name}
            )
        except Exception as audit_error:
            logger.warning(f"Audit logging failed: {audit_error}")

        return SuccessResponse(data=result)

    except Exception as e:
        logger.error(f"Failed to create file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/files/{file_id}", response_model=SuccessResponse[code_service.FileResponse])
@require_perm("code.edit")
async def update_file(
    request: Request,
    file_id: str,
    file_update: code_service.FileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update file"""
    try:
        from pathlib import Path

        # Get current file state for optimistic concurrency
        current = code_service.get_file_current_state(file_id)

        if not current:
            raise HTTPException(status_code=404, detail="File not found")

        # Optimistic concurrency check
        if file_update.base_updated_at and file_update.base_updated_at != current['updated_at']:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "Conflict: File has been modified by another user",
                    "current_updated_at": current['updated_at'],
                    "your_base_updated_at": file_update.base_updated_at
                }
            )

        # Update file
        result = code_service.update_file(
            file_id=file_id,
            name=file_update.name,
            path=file_update.path,
            content=file_update.content,
            language=file_update.language
        )

        # Update workspace timestamp
        code_service.update_workspace_timestamp(current['workspace_id'])

        # If disk workspace, also write to disk
        workspace = code_service.get_workspace(current['workspace_id'])
        if workspace and workspace.source_type == 'disk' and workspace.disk_path:
            workspace_root = Path(workspace.disk_path)
            new_path = file_update.path if file_update.path is not None else current['path']
            new_content = file_update.content if file_update.content is not None else current['content']

            disk_file_path = workspace_root / new_path

            # Path guard: ensure file is under workspace root
            code_service.ensure_under_root(workspace_root, disk_file_path)

            disk_file_path.parent.mkdir(parents=True, exist_ok=True)
            disk_file_path.write_text(new_content, encoding='utf-8')

            # If path changed, delete old file
            if file_update.path is not None and file_update.path != current['path']:
                old_path = workspace_root / current['path']
                code_service.ensure_under_root(workspace_root, old_path)
                if old_path.exists():
                    old_path.unlink()

        # Audit log
        try:
            audit_logger = get_audit_logger()
            audit_logger.log(
                user_id=current_user.get("user_id"),
                action=AuditAction.CODE_FILE_UPDATED,
                resource="code_file",
                resource_id=file_id,
                details={"workspace_id": current['workspace_id'], "path": new_path if file_update.path else current['path']}
            )
        except Exception as audit_error:
            logger.warning(f"Audit logging failed: {audit_error}")

        return SuccessResponse(data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}")
@require_perm("code.edit")
async def delete_file(
    request: Request,
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete file"""
    try:
        from pathlib import Path

        # Get file info before deletion
        file_info = code_service.get_file_info_before_delete(file_id)

        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")

        workspace_id, file_path = file_info

        # Delete from database
        code_service.delete_file(file_id)

        # Update workspace timestamp
        code_service.update_workspace_timestamp(workspace_id)

        # If disk workspace, also delete from disk
        workspace = code_service.get_workspace(workspace_id)
        if workspace and workspace.source_type == 'disk' and workspace.disk_path:
            workspace_root = Path(workspace.disk_path)
            disk_file_path = workspace_root / file_path

            # Path guard
            code_service.ensure_under_root(workspace_root, disk_file_path)

            if disk_file_path.exists():
                disk_file_path.unlink()

        # Audit log
        try:
            audit_logger = get_audit_logger()
            audit_logger.log(
                user_id=current_user.get("user_id"),
                action=AuditAction.CODE_FILE_DELETED,
                resource="code_file",
                resource_id=file_id,
                details={"workspace_id": workspace_id, "path": file_path}
            )
        except Exception as audit_error:
            logger.warning(f"Audit logging failed: {audit_error}")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/import")
@require_perm("code.edit")
async def import_file(
    request: Request,
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Import file into workspace"""
    try:
        from pathlib import Path
        from utils import sanitize_filename

        # Sanitize filename to prevent path traversal
        safe_filename = sanitize_filename(file.filename or "untitled")

        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')

        # Detect language
        ext = Path(safe_filename).suffix.lower()
        lang_map = {
            '.js': 'javascript', '.ts': 'typescript', '.py': 'python',
            '.java': 'java', '.cpp': 'cpp', '.go': 'go', '.rs': 'rust',
            '.html': 'html', '.css': 'css', '.json': 'json',
            '.md': 'markdown', '.yaml': 'yaml', '.yml': 'yaml',
        }
        language = lang_map.get(ext, 'plaintext')

        # Create file
        file_create = code_service.FileCreate(
            workspace_id=workspace_id,
            name=safe_filename,
            path=safe_filename,
            content=content_str,
            language=language
        )

        result = await create_file(request, file_create, current_user)

        # Audit log for import action
        try:
            audit_logger = get_audit_logger()
            audit_logger.log(
                user_id=current_user.get("user_id"),
                action=AuditAction.CODE_FILE_IMPORTED,
                resource="code_file",
                resource_id=result.id,
                details={"workspace_id": workspace_id, "filename": safe_filename}
            )
        except Exception as audit_error:
            logger.warning(f"Audit logging failed: {audit_error}")

        return result

    except Exception as e:
        logger.error(f"Failed to import file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
