"""
Code Editor Filesystem Workspace Operations
Workspace path management and directory walking
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# ============================================================================
# WORKSPACE PATH HELPERS
# ============================================================================

def get_code_workspace_base() -> Path:
    """Get the base path for code workspaces"""
    try:
        from config_paths import PATHS
    except ImportError:
        try:
            from ...config_paths import PATHS
        except ImportError:
            # Fallback: try to get from config_paths module
            from config_paths import get_config_paths
            PATHS = get_config_paths()

    workspace_path = PATHS.data_dir / "code_workspaces"
    workspace_path.mkdir(exist_ok=True, parents=True)
    return workspace_path


def get_user_workspace(user_id: str) -> Path:
    """Get user's code workspace directory"""
    user_workspace = get_code_workspace_base() / user_id
    user_workspace.mkdir(exist_ok=True, parents=True)
    return user_workspace


# ============================================================================
# DIRECTORY WALKING
# ============================================================================

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
    from .security import should_ignore

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
