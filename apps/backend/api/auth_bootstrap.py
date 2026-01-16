"""Backward Compatibility Shim - use api.auth instead."""

from api.auth.bootstrap import (
    _hash_password_pbkdf2,
    ensure_dev_founder_user,
    create_founder_user_explicit,
)

__all__ = [
    "_hash_password_pbkdf2",
    "ensure_dev_founder_user",
    "create_founder_user_explicit",
]
