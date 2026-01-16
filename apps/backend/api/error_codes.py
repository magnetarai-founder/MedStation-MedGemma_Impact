"""Backward Compatibility Shim - use api.errors instead."""

from api.errors.codes import get_error_message
from api.errors.codes_data import ErrorCode, ERROR_MESSAGES

__all__ = ["ErrorCode", "ERROR_MESSAGES", "get_error_message"]
