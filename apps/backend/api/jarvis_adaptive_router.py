"""Backward Compatibility Shim - use api.jarvis instead."""

from api.jarvis.adaptive_router import AdaptiveRouter, AdaptiveRouteResult

__all__ = ["AdaptiveRouter", "AdaptiveRouteResult"]
