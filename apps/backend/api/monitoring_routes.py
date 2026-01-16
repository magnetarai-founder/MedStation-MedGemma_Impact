"""
Compatibility Shim for Monitoring Routes

The implementation now lives in the `api.monitoring` package:
- api.monitoring.routes: Health check and monitoring endpoints

This shim maintains backward compatibility.
"""

from api.monitoring.routes import router

__all__ = [
    "router",
]
