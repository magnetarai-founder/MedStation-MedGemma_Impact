#!/usr/bin/env python3
"""
Chat Service - DEPRECATED FACADE

⚠️  DEPRECATION NOTICE ⚠️

This module is deprecated and will be removed in v2.0.

Please update your imports:

  OLD (deprecated):
    from chat_service import router, public_router
    from chat_service import ollama_client, OllamaClient

  NEW (preferred):
    from api.routes.chat import router, public_router
    # For routers

    from api.services.chat import get_ollama_client, OllamaClient
    # For Ollama client

    from api.services.chat import create_session, send_message_stream, etc.
    # For business logic

This facade maintains backwards compatibility by re-exporting routers
and ollama_client with deprecation warnings.

Migrated as part of R3 Chat Service Split refactoring.
"""

import logging

logger = logging.getLogger(__name__)

# ===== Router Re-export =====

# Import routers from api.routes.chat
from api.routes.chat import router, public_router

# Routers are the same objects; no deprecation warning needed
# since they're the actual implementation, not wrappers

# ===== Ollama Client Re-export (CRITICAL for backwards compatibility) =====

# Many parts of the codebase import ollama_client directly:
#   from chat_service import ollama_client
#
# This is used in:
#   - Frontend model preloading logic
#   - Hot slot management
#   - Server control endpoints
#
# We MUST preserve this export to avoid breaking changes

from api.services.chat import get_ollama_client

# Create module-level ollama_client for backwards compatibility
ollama_client = get_ollama_client()

# Also re-export OllamaClient class for direct instantiation
from api.services.chat import OllamaClient

logger.info("chat_service.py loaded as compatibility facade (DEPRECATED)")
