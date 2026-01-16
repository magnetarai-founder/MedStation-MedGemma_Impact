"""Backward Compatibility Shim - use api.automation instead."""

from api.automation.storage import AutomationStorage, get_automation_storage, logger

__all__ = ["AutomationStorage", "get_automation_storage", "logger"]
