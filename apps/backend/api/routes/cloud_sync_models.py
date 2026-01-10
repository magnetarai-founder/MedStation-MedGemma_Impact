"""
Cloud Sync Models - Enums and Pydantic models for cloud sync service

Provides data models for:
- Sync status, direction, and conflict resolution enums
- Resource type definitions
- Request/response models for sync operations

Extracted from cloud_sync.py during P2 decomposition.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


# ===== Enums =====

class SyncStatus(str, Enum):
    """Sync operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncDirection(str, Enum):
    """Sync direction"""
    UPLOAD = "upload"
    DOWNLOAD = "download"
    BIDIRECTIONAL = "bidirectional"


class ConflictResolution(str, Enum):
    """How to resolve conflicts"""
    LOCAL_WINS = "local_wins"
    REMOTE_WINS = "remote_wins"
    MANUAL = "manual"
    MERGE = "merge"


class ResourceType(str, Enum):
    """Types of resources that can be synced"""
    VAULT_FILE = "vault_file"
    VAULT_FOLDER = "vault_folder"
    WORKFLOW = "workflow"
    WORK_ITEM = "work_item"
    TEAM = "team"
    TEAM_MESSAGE = "team_message"


# ===== Response Models =====

class SyncStatusResponse(BaseModel):
    """Overall sync status"""
    is_syncing: bool
    last_sync_at: Optional[str] = None
    pending_uploads: int
    pending_downloads: int
    conflicts: int
    sync_enabled: bool


class SyncResourceStatus(BaseModel):
    """Status of a specific resource"""
    resource_type: str
    resource_id: str
    local_version: int
    remote_version: int
    sync_status: str
    last_synced_at: Optional[str] = None


class ConflictInfo(BaseModel):
    """Information about a sync conflict"""
    conflict_id: str
    resource_type: str
    resource_id: str
    local_modified_at: str
    remote_modified_at: str
    detected_at: str


class ChangeLogEntry(BaseModel):
    """A change to be synced"""
    resource_type: str
    resource_id: str
    operation: str  # create, update, delete
    data: Optional[Dict[str, Any]] = None
    modified_at: str
    version: int


class SyncExchangeResponse(BaseModel):
    """Response with remote changes"""
    remote_changes: List[ChangeLogEntry]
    new_sync_version: int
    conflicts: List[ConflictInfo]


# ===== Request Models =====

class ResolveConflictRequest(BaseModel):
    """Request to resolve a conflict"""
    resolution: ConflictResolution
    merged_data: Optional[Dict[str, Any]] = None  # For MERGE resolution


class SyncRequest(BaseModel):
    """Request to sync resources"""
    resource_types: List[ResourceType] = Field(default_factory=list)
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    force: bool = False  # Force sync even if no changes detected


class SyncExchangeRequest(BaseModel):
    """Request to exchange changes with cloud"""
    local_changes: List[ChangeLogEntry]
    last_sync_version: int


__all__ = [
    # Enums
    "SyncStatus",
    "SyncDirection",
    "ConflictResolution",
    "ResourceType",
    # Response models
    "SyncStatusResponse",
    "SyncResourceStatus",
    "ConflictInfo",
    "ChangeLogEntry",
    "SyncExchangeResponse",
    # Request models
    "ResolveConflictRequest",
    "SyncRequest",
    "SyncExchangeRequest",
]
