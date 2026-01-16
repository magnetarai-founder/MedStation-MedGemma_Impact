"""
Compatibility Shim for Adaptive Router Patterns

The implementation now lives in the `api.adaptive_router` package:
- api.adaptive_router.patterns: Enums and route patterns

This shim maintains backward compatibility.
"""

from api.adaptive_router.patterns import (
    TaskType,
    ToolType,
    RoutePattern,
    RouteResult,
    DEFAULT_ROUTE_PATTERNS,
)

__all__ = [
    # Enums
    "TaskType",
    "ToolType",
    # Dataclasses
    "RoutePattern",
    "RouteResult",
    # Constants
    "DEFAULT_ROUTE_PATTERNS",
]
