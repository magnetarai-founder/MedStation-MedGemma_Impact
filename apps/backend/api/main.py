"""
Neutron Star Web API
FastAPI backend wrapper for the existing SQL engine

This is the main entry point that creates the FastAPI app and registers routes.
Configuration logic has been extracted to focused modules in api/main/.
Endpoint logic has been extracted to route modules in api/routes/.
"""

import logging
import sys
from pathlib import Path

# Insert at the beginning of sys.path to prioritize local modules
sys.path.insert(0, str(Path(__file__).parent))  # /apps/backend/api - for api module imports
sys.path.insert(0, str(Path(__file__).parent.parent))  # /apps/backend
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "packages"))  # /packages

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
    set_elohimos_memory,
)

# Import state management (needed early for other modules to import from api.main)
from api.core.state import (
    sessions,
    query_results,
    get_progress_stream,
    update_progress_stream,
    delete_progress_stream,
    list_progress_streams,
)

# Import configuration
try:
    from .config import get_settings
except ImportError:
    from config import get_settings

# Import ElohimOS Memory System
try:
    from .elohimos_memory import ElohimOSMemory
except ImportError:
    from elohimos_memory import ElohimOSMemory

# Import Data Engine
try:
    from .data_engine import get_data_engine
except ImportError:
    from data_engine import get_data_engine

# Initialize configuration
settings = get_settings()

# Initialize ElohimOS Memory System
elohimos_memory = ElohimOSMemory()

# Initialize Data Engine
data_engine = get_data_engine()

# Set the memory instance for app_settings module
set_elohimos_memory(elohimos_memory)

# Load app settings
app_settings = load_app_settings()

# ============================================================================
# CREATE FASTAPI APP
# ============================================================================

from api.app_factory import create_app

app = create_app()

# ============================================================================
# INITIALIZE METAL 4 ENGINE
# ============================================================================

# Initialize Metal 4 engine (silent - already shown in banner)
try:
    from metal4_engine import get_metal4_engine
    metal4_engine = get_metal4_engine()
except Exception as e:
    logger.warning(f"Metal 4 not available: {e}")
    metal4_engine = None

# Set Metal 4 engine in routes that need it
if metal4_engine is not None:
    try:
        from api.routes.metal import set_metal4_engine
        set_metal4_engine(metal4_engine)
    except ImportError:
        pass

# ============================================================================
# INITIALIZE DATA ENGINE IN ROUTES
# ============================================================================

# Set data engine and settings in data_engine routes
try:
    from api.routes.data_engine import set_data_engine, set_settings
    set_data_engine(data_engine)
    set_settings(settings)
except ImportError:
    pass

# ============================================================================
# REGISTER ROUTE MODULES
# ============================================================================

# Register individual route modules that aren't in router_registry
# Note: system_router is registered via router_registry in app_factory.py startup
from api.routes.websocket import router as websocket_router
from api.routes.progress import router as progress_router
from api.routes.data_engine import router as data_engine_router

# Register websocket routes
app.include_router(websocket_router)

# Register progress streaming routes
app.include_router(progress_router)

# Register data engine routes
app.include_router(data_engine_router)

# Note: Other routes (including system) are registered via router_registry in app_factory.py startup

# ============================================================================
# EXPORT APP SETTINGS FUNCTIONS
# ============================================================================

# ============================================================================
# EXPORT PUBLIC API
# ============================================================================

__all__ = [
    "app",
    "settings",
    "elohimos_memory",
    "data_engine",
    "metal4_engine",
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
    # MED-05: Enable WebSocket compression (permessage-deflate)
    # Reduces bandwidth for terminal I/O and chat streaming by ~60-80%
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        ws_ping_interval=20,  # Keep connections alive
        ws_ping_timeout=20,
        ws_max_size=16777216,  # 16MB max message size
        ws="websockets",  # Use websockets library (supports compression)
    )
