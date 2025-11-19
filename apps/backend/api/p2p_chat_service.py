"""
DEPRECATED: Monolithic P2P Chat Service Implementation

The P2P chat logic now lives in api.services.p2p_chat.*:
- api.services.p2p_chat.service: Main orchestrator (P2PChatService class)
- api.services.p2p_chat.storage: SQLite database operations
- api.services.p2p_chat.encryption: E2E encryption integration
- api.services.p2p_chat.network: libp2p networking layer
- api.services.p2p_chat.channels: Channel operations
- api.services.p2p_chat.messages: Message operations
- api.services.p2p_chat.files: File transfer operations

This module remains as a backwards-compatible shim that re-exports:
- P2PChatService
- get_p2p_chat_service
- init_p2p_chat_service

External API consumers (p2p_chat_router.py) can continue importing from this module.

Original implementation: Phase 1/2 (P2P mesh networking + E2E encryption)
Refactored: Phase 6.3 (modular services package)
"""

try:
    from api.services.p2p_chat import (
        P2PChatService,
        get_p2p_chat_service,
        init_p2p_chat_service,
    )
except ImportError:
    from services.p2p_chat import (
        P2PChatService,
        get_p2p_chat_service,
        init_p2p_chat_service,
    )

__all__ = [
    "P2PChatService",
    "get_p2p_chat_service",
    "init_p2p_chat_service",
]
