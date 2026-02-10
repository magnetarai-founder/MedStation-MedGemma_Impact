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

    # System API
    try:
        from api.routes import system as _system_routes
        app.include_router(_system_routes.router)
        services_loaded.append("System API")
    except Exception as e:
        services_failed.append("System API")
        logger.error("Failed to load system router", exc_info=True)

    # Settings API
    try:
        from api.routes import settings as _settings_routes
        app.include_router(_settings_routes.router, prefix="/api/settings")
        services_loaded.append("Settings API")
    except Exception as e:
        services_failed.append("Settings API")
        logger.error("Failed to load settings router", exc_info=True)

    # Model Downloads API
    try:
        from api.routes import model_downloads as _model_downloads_routes
        app.include_router(_model_downloads_routes.router)
        services_loaded.append("Model Downloads API")
    except Exception as e:
        services_failed.append("Model Downloads API")
        logger.error("Failed to load model downloads router", exc_info=True)

    # Hardware-Based Model Recommendations API
    try:
        from api.routes.model_recommendations import router as model_recommendations_router
        app.include_router(model_recommendations_router)
        services_loaded.append("Hardware Model Recommendations API")
    except Exception as e:
        services_failed.append("Hardware Model Recommendations API")
        logger.error("Failed to load hardware recommendations router", exc_info=True)

    # User Models
    try:
        from api.routes import user_models as _user_models_routes
        app.include_router(_user_models_routes.router)
        services_loaded.append("User Models")
    except Exception as e:
        services_failed.append("User Models")
        logger.error("Failed to load user models router", exc_info=True)

    # Setup Wizard
    try:
        from api.routes import setup_wizard_routes as _setup_wizard_routes
        app.include_router(_setup_wizard_routes.router)
        services_loaded.append("Setup Wizard")
    except Exception as e:
        services_failed.append("Setup Wizard")
        logger.error("Failed to load setup wizard router", exc_info=True)

    # Hot Slots API (Model management)
    try:
        from api.hot_slots_router import router as hot_slots_router
        app.include_router(hot_slots_router)
        services_loaded.append("Hot Slots API")
    except Exception as e:
        services_failed.append("Hot Slots API")
        logger.error("Failed to load hot slots router", exc_info=True)

    return services_loaded, services_failed
