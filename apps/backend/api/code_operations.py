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
from permissions import require_permission
from audit_logger import log_action
from permission_layer import PermissionLayer, RiskLevel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/code", tags=["code"])

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
    include_dirs: bool = False
) -> List[Dict[str, Any]]:
    """
    Walk directory and return file tree (adapted from Continue's walkDir)
    """
    items = []

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
                'path': str(entry.relative_to(get_code_workspace_base())),
            }

            if is_dir:
                if include_dirs:
                    # Recursively get children
                    if recursive:
                        item['children'] = walk_directory(
                            entry,
                            recursive=True,
                            include_files=include_files,
                            include_dirs=include_dirs
                        )
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
    user_id: str = Depends(require_permission("code.use"))
):
    """
    Get file tree for user's code workspace
    Implements Continue's walkDir pattern with security
    """
    try:
        # Get user workspace
        user_workspace = get_user_workspace(user_id)

        # Resolve requested path
        if path == ".":
            target_path = user_workspace
        else:
            target_path = user_workspace / path

        # Security: validate path
        if not is_safe_path(target_path, user_workspace):
            raise HTTPException(400, "Invalid path")

        if not target_path.exists():
            raise HTTPException(404, "Path not found")

        # Walk directory
        tree = walk_directory(
            target_path,
            recursive=recursive,
            include_files=True,
            include_dirs=True
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
    user_id: str = Depends(require_permission("code.use"))
):
    """
    Read file content (adapted from Codex's read_file with line numbers)
    Supports offset and limit for large files
    """
    try:
        # Get user workspace
        user_workspace = get_user_workspace(user_id)

        # Resolve file path
        file_path = user_workspace / path

        # Security: validate path
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
async def get_workspace_info(
    user_id: str = Depends(require_permission("code.use"))
):
    """
    Get information about user's code workspace
    """
    try:
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
