#!/usr/bin/env python3
"""
Standardized Error Codes for ElohimOS
Provides consistent error codes and user-friendly messages across the platform

Module structure (P2 decomposition):
- error_codes_data.py: ErrorCode enum and ERROR_MESSAGES dict
- error_codes.py: Helper functions for error handling (this file)
"""

from typing import Dict, Any

# Import from extracted module (P2 decomposition)
from api.error_codes_data import ErrorCode, ERROR_MESSAGES


def get_error_message(error_code: ErrorCode, **context) -> Dict[str, str]:
    """
    Get formatted error message for an error code with context substitution

    Args:
        error_code: The error code enum
        **context: Context variables for message formatting (e.g., max_size=10, model="llama2")

    Returns:
        Dict with user_message, suggestion, and technical fields
    """
    if error_code not in ERROR_MESSAGES:
        return {
            "user_message": "An error occurred",
            "suggestion": "Please try again or contact support.",
            "technical": f"Unknown error code: {error_code}"
        }

    error_info = ERROR_MESSAGES[error_code].copy()

    # Format messages with context variables
    if context:
        for key in ["user_message", "suggestion", "technical"]:
            try:
                error_info[key] = error_info[key].format(**context)
            except KeyError:
                # Context variable not in template - leave as is
                pass

    return error_info


# Re-exports for backwards compatibility (P2 decomposition)
__all__ = [
    # Re-exported from error_codes_data
    "ErrorCode",
    "ERROR_MESSAGES",
    # Functions
    "get_error_message",
]
