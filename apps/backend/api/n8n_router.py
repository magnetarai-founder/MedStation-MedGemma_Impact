"""Backward Compatibility Shim - use api.automation.n8n instead."""

from api.automation.n8n.router import router, require_n8n_enabled, logger

__all__ = ["router", "require_n8n_enabled", "logger"]
