"""
Docs Models - Pydantic models for Documents service

Provides validation models for Documents, Spreadsheets, and Insights Lab.

Extracted from docs_service.py during P2 decomposition.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# Valid document types and security levels
VALID_DOC_TYPES = {"doc", "sheet", "insight"}
VALID_SECURITY_LEVELS = {"public", "private", "team", "sensitive", "top-secret"}


class DocumentCreate(BaseModel):
    """Request model for creating a document"""
    type: str = Field(..., description="doc, sheet, or insight")
    title: str = Field(..., min_length=1, max_length=500)
    content: Any
    is_private: bool = False
    security_level: Optional[str] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_DOC_TYPES:
            raise ValueError(f"type must be one of: {', '.join(VALID_DOC_TYPES)}")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title cannot be empty or whitespace")
        return v

    @field_validator("security_level")
    @classmethod
    def validate_security_level(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_SECURITY_LEVELS:
            raise ValueError(f"security_level must be one of: {', '.join(VALID_SECURITY_LEVELS)}")
        return v


class DocumentUpdate(BaseModel):
    """Request model for updating a document (partial update)"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[Any] = None
    is_private: Optional[bool] = None
    security_level: Optional[str] = None
    shared_with: Optional[List[str]] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("title cannot be empty or whitespace")
        return v

    @field_validator("security_level")
    @classmethod
    def validate_security_level(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_SECURITY_LEVELS:
            raise ValueError(f"security_level must be one of: {', '.join(VALID_SECURITY_LEVELS)}")
        return v


class Document(BaseModel):
    """Response model for a document"""
    id: str
    type: str
    title: str
    content: Any
    created_at: str
    updated_at: str
    created_by: str
    is_private: bool = False
    security_level: Optional[str] = None
    shared_with: List[str] = Field(default_factory=list)
    team_id: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "id": "doc_123",
                "type": "doc",
                "title": "My Document",
                "content": {},
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00",
                "created_by": "user_123",
                "is_private": False,
                "shared_with": []
            }
        }
    }


class SyncRequest(BaseModel):
    """Batch sync request for multiple documents"""
    documents: List[Dict[str, Any]]
    last_sync: Optional[str] = None


class SyncResponse(BaseModel):
    """Sync response with updated documents and conflicts"""
    updated_documents: List[Document]
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    sync_timestamp: str


__all__ = [
    "VALID_DOC_TYPES",
    "VALID_SECURITY_LEVELS",
    "DocumentCreate",
    "DocumentUpdate",
    "Document",
    "SyncRequest",
    "SyncResponse",
]
