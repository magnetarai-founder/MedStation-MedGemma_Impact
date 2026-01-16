"""Backward Compatibility Shim - use api.automation.n8n instead."""

from api.automation.n8n.cache import N8NOfflineCache, get_n8n_cache, logger

__all__ = ["N8NOfflineCache", "get_n8n_cache", "logger"]
