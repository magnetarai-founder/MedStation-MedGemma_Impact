"""
SQL/JSON Router - Session-based data processing endpoints.

Handles upload, query, validation, export, and JSON conversion operations.

Follows MagnetarStudio API standards (see API_STANDARDS.md).

NOTE: This module has been refactored into focused sub-modules in api/routes/sql_json/
This file re-exports the router for backwards compatibility.

Sub-modules:
- utils.py - Shared utilities (rate limiting, logging, sanitization, caching)
- sql_processor.py - SQL query processing logic
- query.py - SQL query execution routes
- history.py - Query history management routes
- upload.py - File upload routes (Excel, JSON)
- export.py - Results export routes
- json_convert.py - JSON conversion routes
- validation.py - SQL validation routes
"""

# Re-export router from refactored module directory for backwards compatibility
from .sql_json import router

__all__ = ["router"]
