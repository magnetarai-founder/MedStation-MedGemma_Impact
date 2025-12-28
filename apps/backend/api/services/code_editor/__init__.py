"""
Code Editor Service Package
Modularized code editor functionality

This package provides:
- Database operations for workspaces and files
- File tree building and disk scanning
- Diff generation with truncation
- Filesystem operations with security
- Risk assessment and rate limiting
"""

# ============================================================================
# MODELS
# ============================================================================

from .models import (
    # Workspace models
    WorkspaceCreate,
    WorkspaceResponse,
    # File models
    FileCreate,
    FileUpdate,
    FileResponse,
    FilesListResponse,
    # Diff models
    FileDiffRequest,
    FileDiffResponse,
    # Tree models
    FileTreeNode,
    # Operations models
    WriteFileRequest,
    DiffPreviewRequest,
)

# ============================================================================
# SECURITY
# ============================================================================

from .security import (
    ensure_under_root,
    is_safe_path,
    should_ignore,
)

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

from .db_workspaces import (
    # Initialization
    init_code_editor_db,
    # Workspace CRUD
    create_workspace,
    get_workspace,
    list_workspaces,
    update_workspace_timestamp,
    delete_workspace,
    # File CRUD
    create_file,
    get_file,
    get_file_for_diff,
    get_files_by_workspace,
    get_file_info_before_delete,
    get_file_current_state,
    update_file,
    delete_file,
    delete_files_by_workspace,
)

# ============================================================================
# FILE TREE
# ============================================================================

from .file_tree import (
    build_file_tree,
)

# ============================================================================
# DISK SCANNING
# ============================================================================

from .disk_scan import (
    scan_disk_directory,
)

# ============================================================================
# DIFF SERVICE
# ============================================================================

from .diff_service import (
    # Constants
    MAX_DIFF_FILE_SIZE,
    MAX_DIFF_LINES,
    TRUNCATE_HEAD_LINES,
    TRUNCATE_TAIL_LINES,
    # Functions
    generate_file_diff,
)

# ============================================================================
# FILESYSTEM WORKSPACE
# ============================================================================

from .fs_workspace import (
    get_code_workspace_base,
    get_user_workspace,
    walk_directory,
)

# ============================================================================
# FILESYSTEM DIFF
# ============================================================================

from .fs_diff import (
    generate_unified_diff,
)

# ============================================================================
# FILESYSTEM WRITE
# ============================================================================

from .fs_write import (
    # Write operations
    write_file_to_disk,
    delete_file_from_disk,
    # Risk assessment
    assess_write_risk,
    assess_delete_risk,
    # Rate limiting
    check_write_rate_limit,
    check_delete_rate_limit,
)


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    # Models
    'WorkspaceCreate',
    'WorkspaceResponse',
    'FileCreate',
    'FileUpdate',
    'FileResponse',
    'FilesListResponse',
    'FileDiffRequest',
    'FileDiffResponse',
    'FileTreeNode',
    'WriteFileRequest',
    'DiffPreviewRequest',
    # Security
    'ensure_under_root',
    'is_safe_path',
    'should_ignore',
    # Database
    'init_code_editor_db',
    'create_workspace',
    'get_workspace',
    'list_workspaces',
    'update_workspace_timestamp',
    'delete_workspace',
    'create_file',
    'get_file',
    'get_file_for_diff',
    'get_files_by_workspace',
    'get_file_info_before_delete',
    'get_file_current_state',
    'update_file',
    'delete_file',
    'delete_files_by_workspace',
    # File tree
    'build_file_tree',
    # Disk scan
    'scan_disk_directory',
    # Diff service
    'MAX_DIFF_FILE_SIZE',
    'MAX_DIFF_LINES',
    'TRUNCATE_HEAD_LINES',
    'TRUNCATE_TAIL_LINES',
    'generate_file_diff',
    # Filesystem
    'get_code_workspace_base',
    'get_user_workspace',
    'walk_directory',
    'generate_unified_diff',
    'write_file_to_disk',
    'delete_file_from_disk',
    'assess_write_risk',
    'assess_delete_risk',
    'check_write_rate_limit',
    'check_delete_rate_limit',
]
