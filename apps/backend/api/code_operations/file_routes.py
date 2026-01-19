"""
Code Operations - File Routes

File tree, read, write, delete, and diff operations.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from pathlib import Path
import logging

from api.errors import http_400, http_403, http_404, http_429
from api.auth_middleware import get_current_user
from api.utils import get_user_id
from api.permission_layer import PermissionLayer, RiskLevel
from api.rate_limiter import rate_limiter
from api.config_paths import PATHS
from api.core.exceptions import handle_exceptions

try:
    from api.audit_logger import log_action
except ImportError:
    async def log_action(**kwargs: Any) -> None:
        pass

from api.services import code_editor as code_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize permission layer for file operations
permission_layer = PermissionLayer(
    config_path=str(PATHS.data_dir / "code_permissions.json"),
    non_interactive=True,
    non_interactive_policy="conservative"
)


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "code_operations",
        "workspace_base": str(code_service.get_code_workspace_base())
    }


@router.get("/files")
@handle_exceptions("get file tree", resource_type="File")
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
    user_id = get_user_id(current_user)
    logger.info(f"[CODE] GET /files - user_id={user_id}, path={path}, absolute_path={absolute_path}, recursive={recursive}")

    user_workspace = code_service.get_user_workspace(user_id)

    if absolute_path:
        target_path = Path(absolute_path).resolve()

        from api.config_paths import get_config_paths

        PATHS_LOCAL = get_config_paths()
        user_workspace_root = PATHS_LOCAL.data_dir / "code_workspaces" / user_id

        try:
            target_path.relative_to(user_workspace_root)
        except ValueError:
            raise http_403(f"Access denied: absolute_path must be within workspace ({user_workspace_root})")

        if not target_path.exists():
            raise http_404("Path not found", resource="path")
        if not target_path.is_dir():
            raise http_400("Path is not a directory")
    else:
        target_path = user_workspace if path == "." else user_workspace / path

        if not code_service.is_safe_path(target_path, user_workspace):
            raise http_400("Invalid path")

    if not target_path.exists():
        raise http_404("Path not found", resource="path")

    tree = code_service.walk_directory(
        target_path,
        recursive=recursive,
        include_files=True,
        include_dirs=True,
        base_path=target_path
    )

    await log_action(
        user_id=user_id,
        action="code.files.list",
        resource=str(target_path),
        details={'count': len(tree), 'recursive': recursive}
    )

    return {'path': path, 'items': tree}


@router.get("/read")
@handle_exceptions("read file", resource_type="File")
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
    """
    user_id = get_user_id(current_user)
    user_workspace = code_service.get_user_workspace(user_id)

    if absolute_path or path.startswith('/'):
        file_path = Path(path).resolve()

        from api.config_paths import get_config_paths

        PATHS_LOCAL = get_config_paths()
        user_workspace_root = PATHS_LOCAL.data_dir / "code_workspaces" / user_id

        try:
            file_path.relative_to(user_workspace_root)
        except ValueError:
            raise http_403(f"Access denied: file must be within workspace ({user_workspace_root})")
    else:
        file_path = user_workspace / path

        if not code_service.is_safe_path(file_path, user_workspace):
            raise http_400("Invalid path")

    if not file_path.exists():
        raise http_404("File not found", resource="file")

    if not file_path.is_file():
        raise http_400("Not a file")

    risk_level, risk_reason = permission_layer.assess_risk(
        f"read {file_path}",
        "file_read"
    )

    if risk_level == RiskLevel.CRITICAL:
        raise http_403(f"File access denied: {risk_reason}")

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
        raise http_400("Cannot read binary file")

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


@router.get("/workspace/info")
@handle_exceptions("get workspace info", resource_type="Workspace")
async def get_workspace_info(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get information about user's code workspace"""
    import os
    user_id = get_user_id(current_user)
    user_workspace = code_service.get_user_workspace(user_id)

    file_count = 0
    dir_count = 0
    total_size = 0

    for root, dirs, files in os.walk(user_workspace):
        dirs[:] = [d for d in dirs if not code_service.should_ignore(Path(root) / d)]
        files = [f for f in files if not code_service.should_ignore(Path(root) / f)]

        dir_count += len(dirs)
        file_count += len(files)

        for file in files:
            try:
                total_size += (Path(root) / file).stat().st_size
            except (OSError, IOError):
                pass  # Skip files that can't be stat'd

    return {
        'workspace_path': str(user_workspace),
        'file_count': file_count,
        'directory_count': dir_count,
        'total_size': total_size,
        'total_size_mb': round(total_size / (1024 * 1024), 2)
    }


@router.post("/diff/preview")
@handle_exceptions("preview diff", resource_type="File")
async def preview_diff(
    request: code_service.DiffPreviewRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Preview changes before saving"""
    user_id = get_user_id(current_user)
    user_workspace = code_service.get_user_workspace(user_id)
    file_path = user_workspace / request.path

    if not code_service.is_safe_path(file_path, user_workspace):
        raise http_400("Invalid path")

    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    else:
        original_content = ""

    diff_text = code_service.generate_unified_diff(
        original_content,
        request.new_content,
        request.path
    )

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


@router.post("/write")
@handle_exceptions("write file", resource_type="File")
async def write_file(
    request: code_service.WriteFileRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Write file with permission checking and rate limiting"""
    user_id = get_user_id(current_user)

    if not rate_limiter.check_rate_limit(
        f"code:write:{user_id}",
        max_requests=30,
        window_seconds=60
    ):
        raise http_429("Too many write requests. Please slow down.")

    user_workspace = code_service.get_user_workspace(user_id)
    file_path = user_workspace / request.path

    if not code_service.is_safe_path(file_path, user_workspace):
        raise http_400("Invalid path")

    is_new_file = not file_path.exists()

    if is_new_file and not request.create_if_missing:
        raise http_404("File does not exist. Set create_if_missing=true to create.", resource="file")

    operation = "create file" if is_new_file else "modify file"
    risk_level, risk_reason = permission_layer.assess_risk(
        f"{operation} {file_path}",
        "file_write"
    )

    if risk_level == RiskLevel.CRITICAL:
        raise http_403(f"Write operation denied: {risk_reason}")

    if risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM]:
        logger.warning(f"High/medium risk write operation: {file_path} - {risk_reason}")

    code_service.write_file_to_disk(file_path, request.content)

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


@router.delete("/delete")
@handle_exceptions("delete file", resource_type="File")
async def delete_file(
    path: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete file with permission checking and rate limiting"""
    user_id = get_user_id(current_user)

    if not rate_limiter.check_rate_limit(
        f"code:delete:{user_id}",
        max_requests=20,
        window_seconds=60
    ):
        raise http_429("Too many delete requests. Please slow down.")

    user_workspace = code_service.get_user_workspace(user_id)
    file_path = user_workspace / path

    if not code_service.is_safe_path(file_path, user_workspace):
        raise http_400("Invalid path")

    if not file_path.exists():
        raise http_404("File not found", resource="file")

    risk_level, risk_reason = permission_layer.assess_risk(
        f"rm {file_path}",
        "file_delete"
    )

    if risk_level == RiskLevel.CRITICAL:
        raise http_403(f"Delete operation denied: {risk_reason}")

    if file_path.is_file():
        code_service.delete_file_from_disk(file_path)
    else:
        raise http_400("Path is not a file")

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
