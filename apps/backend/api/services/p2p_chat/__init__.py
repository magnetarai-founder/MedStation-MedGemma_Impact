"""
P2P Chat Service Package

Modular P2P chat system with:
- libp2p mesh networking
- E2E encryption (Signal-style)
- Peer discovery (mDNS)
- Channel management
- Message operations
- File transfers

Public API:
- P2PChatService: Main service orchestrator
- get_p2p_chat_service: Get singleton instance
- init_p2p_chat_service: Initialize singleton

Internal modules:
- types: Protocol constants and config
- storage: SQLite database operations
- encryption: E2E encryption integration
- network: libp2p networking layer
- channels: Channel operations
- messages: Message operations
- files: File transfer operations
- service: Main orchestrator
"""

from .service import (
    P2PChatService,
    get_p2p_chat_service,
    init_p2p_chat_service,
)

__all__ = [
    "P2PChatService",
    "get_p2p_chat_service",
    "init_p2p_chat_service",
]
