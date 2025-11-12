"""
Shared dependency injection helpers for FastAPI routes.

These functions re-export authentication dependencies from
auth_middleware to avoid direct coupling in route modules
and help prevent circular imports during refactors.

Mechanical scaffold only — no behavior changes.
"""

from .auth_middleware import get_current_user, get_current_user_optional  # re-export

__all__ = [
    "get_current_user",
    "get_current_user_optional",
]

