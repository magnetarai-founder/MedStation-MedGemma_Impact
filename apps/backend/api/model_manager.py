"""
Compatibility Shim for Model Manager

The implementation now lives in the `api.models` package:
- api.models.manager: ModelManager class

This shim maintains backward compatibility.
"""

from api.models.manager import (
    ModelManager,
    get_model_manager,
)

__all__ = [
    "ModelManager",
    "get_model_manager",
]
