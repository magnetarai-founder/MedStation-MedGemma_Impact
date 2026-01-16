"""Backward Compatibility Shim - use api.trust instead."""

try:
    from api.trust.router import router, logger
except ImportError as e:
    # nacl package may not be installed - router requires Ed25519 signing
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Trust router unavailable: {e}")
    router = None

__all__ = [
    "router",
    "logger",
]
