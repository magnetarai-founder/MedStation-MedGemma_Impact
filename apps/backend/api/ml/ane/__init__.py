"""
Apple Neural Engine (ANE) integration for NeutronStar.

Provides:
- ANEContextEngine: Context processing with ANE acceleration
- ANERouter: Intelligent routing to ANE/GPU/CPU
- CoreMLRouter: CoreML model routing
"""

from api.ml.ane.context_engine import (
    ANEContextEngine,
    get_ane_engine,
    _embed_with_ane,
)
from api.ml.ane.router import (
    ANERouter,
    get_ane_router,
    ANERouteResult,
    RouteTarget,
    CoreMLRouter,
    get_coreml_router,
)

__all__ = [
    "ANEContextEngine",
    "get_ane_engine",
    "_embed_with_ane",
    "ANERouter",
    "get_ane_router",
    "ANERouteResult",
    "RouteTarget",
    "CoreMLRouter",
    "get_coreml_router",
]
