"""
Insights Lab Routes Package

Exports all route modules for the Insights Lab API.
"""

from .recordings import router as recordings_router
from .templates import router as templates_router
from .outputs import router as outputs_router
from .legacy import router as legacy_router

__all__ = [
    "recordings_router",
    "templates_router",
    "outputs_router",
    "legacy_router",
]
