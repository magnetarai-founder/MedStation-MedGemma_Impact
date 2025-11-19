"""
Vault routes - Legacy shim, imports from new modular package

This file has been modularized into:
- api/routes/vault/documents.py - Document CRUD
- api/routes/vault/files.py - File upload/download/management
- api/routes/vault/folders.py - Folder management
- api/routes/vault/sharing.py - File sharing and collaboration
- api/routes/vault/ws.py - WebSocket real-time collaboration
- api/routes/vault/automation.py - Organization rules and automation

All endpoints are now aggregated in api/routes/vault/__init__.py
"""

try:
    from api.routes import vault as _vault_routes
except ImportError:
    from routes import vault as _vault_routes

router = _vault_routes.router

__all__ = ['router']
