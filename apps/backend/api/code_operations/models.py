"""
Code Operations - Pydantic Models

Request/response models for code operations API.
"""

from typing import List, Optional
from pydantic import BaseModel


class ProjectLibraryDocument(BaseModel):
    """Document in the project library"""
    name: str
    content: str
    tags: List[str] = []
    file_type: str = "markdown"


class UpdateDocumentRequest(BaseModel):
    """Request to update a library document"""
    name: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class WorkspaceRootRequest(BaseModel):
    """Request to set workspace root path"""
    workspace_root: str
