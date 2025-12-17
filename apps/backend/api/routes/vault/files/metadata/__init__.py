"""
Vault Files Metadata Module

Combines all metadata-related routers into a single router.
This module aggregates focused sub-modules for better organization:
- tags: Tag management operations
- favorites: Favorites and pinned files
- activity: Access logging, recent files, storage stats, audit logs
- versions: File versioning operations
- trash: Trash/recycle bin and secure deletion
- comments: File comments CRUD
- metadata_ops: Custom metadata operations
- export: Vault data export

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from fastapi import APIRouter
from . import tags, favorites, activity, versions, trash, comments, metadata_ops, export

# Create the combined router
router = APIRouter()

# Include all sub-routers
router.include_router(tags.router, tags=["Vault Files - Tags"])
router.include_router(favorites.router, tags=["Vault Files - Favorites"])
router.include_router(activity.router, tags=["Vault Files - Activity"])
router.include_router(versions.router, tags=["Vault Files - Versions"])
router.include_router(trash.router, tags=["Vault Files - Trash"])
router.include_router(comments.router, tags=["Vault Files - Comments"])
router.include_router(metadata_ops.router, tags=["Vault Files - Metadata"])
router.include_router(export.router, tags=["Vault Files - Export"])

__all__ = ["router"]
