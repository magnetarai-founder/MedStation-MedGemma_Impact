"""
SQL/JSON Router - Session-based data processing endpoints (Compatibility Wrapper)

This module maintains backwards compatibility by re-exporting the combined
router from the refactored sql_json submodule.

The original 1,421-line sql_json.py has been refactored into focused modules
organized under api/routes/sql_json/:
- utils.py - Shared utilities (rate limiting, logging, sanitization, caching)
- sql_processor.py - SQL query processing and validation logic
- validation.py - SQL syntax validation endpoints
- query.py - SQL query execution and table listing
- history.py - Query history management
- upload.py - File upload handling (Excel, CSV, JSON)
- export.py - Results export in multiple formats
- json_convert.py - JSON to Excel conversion

All functionality is preserved exactly as before. This wrapper ensures
that existing imports continue to work without modification.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

# Import all sub-routers and combine them
from fastapi import APIRouter
from api.routes.sql_json import (
    validation, query, history, upload, export, json_convert
)

# Create the combined router (replicate the __init__.py logic)
router = APIRouter(tags=["sessions"])

# Include all sub-routers
router.include_router(validation.router)
router.include_router(query.router)
router.include_router(history.router)
router.include_router(upload.router)
router.include_router(export.router)
router.include_router(json_convert.router)

__all__ = ["router"]
