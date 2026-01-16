"""Backward Compatibility Shim - use api.errors instead."""

from api.errors.codes_data import ErrorCode, ERROR_MESSAGES

__all__ = ["ErrorCode", "ERROR_MESSAGES"]
