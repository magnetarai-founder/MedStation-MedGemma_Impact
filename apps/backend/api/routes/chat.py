"""
Chat routes - Legacy shim, imports from new modular package

This file has been modularized into:
- api/routes/chat/sessions.py - Session CRUD
- api/routes/chat/messages.py - Message operations
- api/routes/chat/files.py - File attachments
- api/routes/chat/models.py - Model management

All endpoints are now aggregated in api/routes/chat/__init__.py
"""

from api.routes.chat import router, public_router

__all__ = ['router', 'public_router']
