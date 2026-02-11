"""
Centralized router registration for MedStation API.

Registers MedGemma inference and Ollama proxy routes.
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

    # Chat API (MedGemma + Ollama proxy)
    try:
        from api.routes.chat import router, public_router
        app.include_router(router)
        app.include_router(public_router)
        services_loaded.append("MedGemma + Ollama API")
    except Exception as e:
        services_failed.append("MedGemma + Ollama API")
        logger.error("Failed to load chat router", exc_info=True)

    return services_loaded, services_failed
