"""
SQL/JSON Router - Session-based data processing endpoints.

Handles upload, query, validation, export, and JSON conversion operations.

Follows MagnetarStudio API standards (see API_STANDARDS.md).

This module combines focused sub-routers for better code organization:
- utils: Shared utilities and getter functions
- sql_processor: SQL query processing and validation
- validation: SQL syntax validation endpoints
- query: SQL query execution endpoints
- history: Query history management endpoints
- upload: File upload endpoints (Excel, CSV, JSON)
- export: Results export endpoints
- json_convert: JSON conversion endpoints
"""

from fastapi import APIRouter
from . import validation, query, history, upload, export, json_convert


# Create main router
router = APIRouter(tags=["sessions"])

# Include all sub-routers
router.include_router(validation.router)
router.include_router(query.router)
router.include_router(history.router)
router.include_router(upload.router)
router.include_router(export.router)
router.include_router(json_convert.router)


__all__ = ["router"]
