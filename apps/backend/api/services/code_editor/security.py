"""
Code Editor Security Helpers
Path validation and security functions
"""

import logging
from pathlib import Path
from fastapi import HTTPException

logger = logging.getLogger(__name__)


# ============================================================================
# PATH SECURITY (from code_editor_service.py)
# ============================================================================

def ensure_under_root(root: Path, candidate: Path) -> None:
    """
    Ensure candidate path is under root directory.
    Prevents path traversal attacks.

    Raises HTTPException(400) if validation fails.
    """
    try:
        root_resolved = root.resolve()
        candidate_resolved = candidate.resolve()

        # Check if candidate is relative to root
        if not candidate_resolved.is_relative_to(root_resolved):
            logger.warning(f"Path traversal attempt: {candidate} not under {root}")
            raise HTTPException(
                status_code=400,
                detail=f"Path must be under workspace root"
            )
    except (ValueError, OSError) as e:
        logger.error(f"Path validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid path"
        )


# ============================================================================
# PATH SECURITY (from code_operations.py)
# ============================================================================

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
