"""
Centralized router registration for MedStation API.

Registers only medical-relevant API routers.
"""

import logging
from typing import List, Tuple

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def register_routers(app: FastAPI) -> Tuple[List[str], List[str]]:
    """
    Register API routers to the FastAPI app.

    Returns:
        Tuple of (services_loaded, services_failed) with human-readable names
    """
    services_loaded = []
    services_failed = []

    # Chat API (Ollama integration for medical AI)
    try:
        from api.routes import chat as _chat_routes
        app.include_router(_chat_routes.router)
        app.include_router(_chat_routes.public_router)
        services_loaded.append("Chat API")
    except Exception as e:
        services_failed.append("Chat API")
        logger.error("Failed to load chat router", exc_info=True)

    # Users API
    try:
        from api.routes import users as _users_routes
        app.include_router(_users_routes.router)
        services_loaded.append("Users API")
    except Exception as e:
        services_failed.append("Users API")
        logger.error("Failed to load users router", exc_info=True)

    # Auth
    try:
        from api.auth_routes import router as auth_router
        app.include_router(auth_router)
        services_loaded.append("Auth")
    except Exception as e:
        services_failed.append("Auth")
        logger.error("Failed to load auth router", exc_info=True)

    # Hot Slots API (Model management)
    try:
        from api.hot_slots_router import router as hot_slots_router
        app.include_router(hot_slots_router)
        services_loaded.append("Hot Slots API")
    except Exception as e:
        services_failed.append("Hot Slots API")
        logger.error("Failed to load hot slots router", exc_info=True)

    return services_loaded, services_failed
