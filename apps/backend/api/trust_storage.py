"""Backward Compatibility Shim - use api.trust instead."""

from api.trust.storage import TrustStorage, get_trust_storage, logger

__all__ = [
    "TrustStorage",
    "get_trust_storage",
    "logger",
]
