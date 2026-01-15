"""Backward Compatibility Shim - use api.ml.ane instead."""

from api.ml.ane.router import (
    ANERouter,
    get_ane_router,
    ANERouteResult,
    RouteTarget,
    CoreMLRouter,
    get_coreml_router,
)

__all__ = [
    "ANERouter",
    "get_ane_router",
    "ANERouteResult",
    "RouteTarget",
    "CoreMLRouter",
    "get_coreml_router",
]
