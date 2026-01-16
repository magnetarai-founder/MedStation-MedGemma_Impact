"""
Compatibility Shim for Interactive Permission Layer

The implementation now lives in the `api.permission_layer` package:
- api.permission_layer.layer: Main PermissionLayer class
- api.permission_layer.risk: Risk assessment functions and constants

This shim maintains backward compatibility.
"""

# Re-export everything from the new package location
from api.permission_layer.layer import (
    PermissionResponse,
    RiskLevel,
    PermissionRequest,
    PermissionRule,
    PermissionLayer,
    PermissionSystem,
    test_permission_layer,
    # ANSI colors
    RED,
    GREEN,
    YELLOW,
    BLUE,
    CYAN,
    BOLD,
    DIM,
    RESET,
)

__all__ = [
    "PermissionResponse",
    "RiskLevel",
    "PermissionRequest",
    "PermissionRule",
    "PermissionLayer",
    "PermissionSystem",
    "test_permission_layer",
    "RED",
    "GREEN",
    "YELLOW",
    "BLUE",
    "CYAN",
    "BOLD",
    "DIM",
    "RESET",
]
