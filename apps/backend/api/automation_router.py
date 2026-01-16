"""Backward Compatibility Shim - use api.automation instead."""

from api.automation.router import router, logger
from api.automation.storage import get_automation_storage

__all__ = ["router", "logger", "get_automation_storage"]
