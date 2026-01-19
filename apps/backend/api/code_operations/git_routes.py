"""
Code Operations - Git Routes

Git log and workspace root operations.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from pathlib import Path
import subprocess
import logging

from api.auth_middleware import get_current_user
from api.errors import http_400, http_500
from api.utils import get_user_id
from api.config_paths import PATHS
from api.code_operations.models import WorkspaceRootRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/workspace/set")
async def set_workspace_root(request: WorkspaceRootRequest) -> Dict[str, Any]:
    """
    Set the current workspace root path
    Frontend calls this when user opens a folder
    """
    try:
        workspace_path = Path(request.workspace_root)

        if not workspace_path.exists():
            raise http_400("Workspace path does not exist")

        if not workspace_path.is_dir():
            raise http_400("Workspace path must be a directory")

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
        raise http_500("Failed to set workspace root")


@router.get("/git/log")
async def get_git_log(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get git commit history from the currently opened project folder
    Returns commits from the workspace root stored in localStorage
    """
    try:
        user_id = get_user_id(current_user)

        workspace_root = None
        marker_file = PATHS.data_dir / "current_workspace.txt"
        if marker_file.exists():
            workspace_root = marker_file.read_text().strip()

        if not workspace_root:
            return {
                'commits': [],
                'branch': None,
                'error': 'No workspace opened'
            }

        workspace_path = Path(workspace_root)

        git_dir = workspace_path / '.git'
        if not git_dir.exists():
            return {
                'commits': [],
                'branch': None,
                'error': 'Not a git repository'
            }

        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=str(workspace_path),
            capture_output=True,
            text=True,
            timeout=5
        )
        current_branch = branch_result.stdout.strip() or 'main'

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
        raise http_500("Git operation timed out")
    except Exception as e:
        logger.error(f"Error getting git log: {e}")
        return {
            'commits': [],
            'branch': None,
            'error': str(e)
        }
