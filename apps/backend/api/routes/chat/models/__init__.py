"""
Chat Models Routes Package - Model management, Ollama config, hot slots, library

Refactored from monolithic models.py (886 lines) into focused submodules:
- list.py: Model listing, status, tags, and caching (~230 lines)
- preload.py: Preload/unload operations (~100 lines)
- hot_slots.py: Hot slot management (~170 lines)
- server.py: Ollama server management (~130 lines)
- library.py: Pull, remove, version, library browsing (~200 lines)
"""

from fastapi import APIRouter

from . import list as list_module
from . import preload
from . import hot_slots
from . import server
from . import library

# Combined router for all model-related endpoints
router = APIRouter()

# Include all sub-routers
router.include_router(list_module.router)
router.include_router(preload.router)
router.include_router(hot_slots.router)
router.include_router(server.router)
router.include_router(library.router)

# Re-export ModelListCache for external use (e.g., tests)
from .list import ModelListCache, _model_cache

__all__ = ["router", "ModelListCache", "_model_cache"]
