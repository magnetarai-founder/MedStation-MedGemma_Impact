"""
Adaptive Router Package

Intelligent task routing for ElohimOS:
- Pattern matching for task classification
- Learning-based route optimization
- Context-aware recommendations
"""

from api.adaptive_router.patterns import (
    TaskType,
    ToolType,
    RoutePattern,
    RouteResult,
    DEFAULT_ROUTE_PATTERNS,
)
from api.adaptive_router.router import (
    EnhancedRouter,
    AdaptiveRouter,
    AdaptiveRouteResult,
)

__all__ = [
    # Enums
    "TaskType",
    "ToolType",
    # Dataclasses
    "RoutePattern",
    "RouteResult",
    "AdaptiveRouteResult",
    # Constants
    "DEFAULT_ROUTE_PATTERNS",
    # Classes
    "EnhancedRouter",
    "AdaptiveRouter",
]
