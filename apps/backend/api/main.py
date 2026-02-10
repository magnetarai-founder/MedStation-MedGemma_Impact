"""
MedStation API
FastAPI backend for medical AI workflows.

This is the main entry point that creates the FastAPI app and registers routes.
"""

import logging
import sys
from pathlib import Path

# Insert at the beginning of sys.path to prioritize local modules
sys.path.insert(0, str(Path(__file__).parent))  # /apps/backend/api
sys.path.insert(0, str(Path(__file__).parent.parent))  # /apps/backend

logger = logging.getLogger(__name__)

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

from api.core.logging_config import configure_logging

configure_logging()

# ============================================================================
# GLOBAL STATE AND CONFIGURATION
# ============================================================================

from api.core.app_settings import (
    AppSettings,
    load_app_settings,
    save_app_settings,
    set_medstationos_memory,
)

from api.core.state import (
    sessions,
    query_results,
    get_progress_stream,
    update_progress_stream,
    delete_progress_stream,
    list_progress_streams,
)

try:
    from .config import get_settings
except ImportError:
    from config import get_settings

try:
    from .medstationos_memory import MedStationMemory
except ImportError:
    from medstationos_memory import MedStationMemory

# Initialize configuration
settings = get_settings()

# Initialize memory system
medstationos_memory = MedStationMemory()
set_medstationos_memory(medstationos_memory)

# Load app settings
app_settings = load_app_settings()

# ============================================================================
# CREATE FASTAPI APP
# ============================================================================

from api.app_factory import create_app

app = create_app()

# ============================================================================
# REGISTER ADDITIONAL ROUTES
# ============================================================================

# Register websocket routes
try:
    from api.routes.websocket import router as websocket_router
    app.include_router(websocket_router)
except ImportError:
    logger.warning("WebSocket routes not available")

# Register progress streaming routes
try:
    from api.routes.progress import router as progress_router
    app.include_router(progress_router)
except ImportError:
    logger.warning("Progress routes not available")

# ============================================================================
# EXPORT PUBLIC API
# ============================================================================

__all__ = [
    "app",
    "settings",
    "medstationos_memory",
    "app_settings",
    "load_app_settings",
    "save_app_settings",
    "AppSettings",
    "sessions",
    "query_results",
    "get_progress_stream",
    "update_progress_stream",
    "delete_progress_stream",
    "list_progress_streams",
]

# ============================================================================
# DEVELOPMENT SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        ws_ping_interval=20,
        ws_ping_timeout=20,
        ws_max_size=16777216,
        ws="websockets",
    )
