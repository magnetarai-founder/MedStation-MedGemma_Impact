"""
Chat routes - Legacy shim, imports from new modular package

This file has been modularized into:
- api/routes/chat/sessions.py - Session CRUD
- api/routes/chat/messages.py - Message operations
- api/routes/chat/files.py - File attachments
- api/routes/chat/models.py - Model management

All endpoints are now aggregated in api/routes/chat/__init__.py
"""

try:
    from api.routes import chat as _chat_routes
except ImportError:
    from routes import chat as _chat_routes

router = _chat_routes.router
public_router = _chat_routes.public_router

__all__ = ['router', 'public_router']
