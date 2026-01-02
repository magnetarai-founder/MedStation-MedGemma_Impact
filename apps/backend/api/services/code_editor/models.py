"""
Code Editor Models
All Pydantic models for code editor service
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================================
# WORKSPACE MODELS (from code_editor_service.py)
# ============================================================================

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


class WorkspacesListResponse(BaseModel):
    """Response model for workspaces list"""
    workspaces: List[WorkspaceResponse]


# ============================================================================
# FILE MODELS (from code_editor_service.py)
# ============================================================================

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
    base_updated_at: Optional[str] = Field(None, description="Base timestamp for optimistic concurrency")


class FileResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    path: str
    content: str
    language: str
    created_at: datetime
    updated_at: datetime


# ============================================================================
# DIFF MODELS (from code_editor_service.py)
# ============================================================================

class FileDiffRequest(BaseModel):
    new_content: str
    base_updated_at: Optional[str] = Field(None, description="Base timestamp to check for conflicts")


class FileDiffResponse(BaseModel):
    diff: str
    current_hash: str
    current_updated_at: str
    conflict: bool = False
    truncated: bool = False
    max_lines: Optional[int] = None
    shown_head: Optional[int] = None
    shown_tail: Optional[int] = None
    message: Optional[str] = None


# ============================================================================
# FILE TREE MODELS (from code_editor_service.py)
# ============================================================================

class FileTreeNode(BaseModel):
    id: str
    name: str
    path: str
    is_directory: bool
    children: Optional[List['FileTreeNode']] = None


class FilesListResponse(BaseModel):
    """Response model for workspace files list"""
    files: List[FileTreeNode]


# ============================================================================
# OPERATIONS MODELS (from code_operations.py)
# ============================================================================

class WriteFileRequest(BaseModel):
    path: str
    content: str
    create_if_missing: bool = False


class DiffPreviewRequest(BaseModel):
    path: str
    new_content: str
