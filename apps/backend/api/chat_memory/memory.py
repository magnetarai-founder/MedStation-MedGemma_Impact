"""
Neutron Chat Memory

Main memory class combining all mixins.
"""

import logging
from pathlib import Path

from .base import ChatMemoryBase
from .sessions import SessionMixin
from .messages import MessageMixin
from .summaries import SummaryMixin
from .documents import DocumentMixin
from .search import SearchMixin
from .analytics import AnalyticsMixin

logger = logging.getLogger(__name__)


class NeutronChatMemory(
    ChatMemoryBase,
    SessionMixin,
    MessageMixin,
    SummaryMixin,
    DocumentMixin,
    SearchMixin,
    AnalyticsMixin,
):
    """
    Advanced chat memory system for Neutron
    - Stores full message history
    - Creates rolling summaries
    - Tracks model switches
    - Preserves context across sessions
    - Thread-safe with connection-per-thread pattern
    """

    def __init__(self, db_path: Path = None):
        # Get memory directory from config
        try:
            from api.config_paths import get_memory_dir
        except ImportError:
            from config_paths import get_memory_dir

        MEMORY_DIR = get_memory_dir()

        if db_path is None:
            db_path = MEMORY_DIR / "chat_memory.db"

        # Initialize base class (sets up connection management)
        ChatMemoryBase.__init__(self, db_path)


# Singleton instance
_memory_instance = None


def get_memory() -> NeutronChatMemory:
    """Get singleton memory instance"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = NeutronChatMemory()
    return _memory_instance


__all__ = ["NeutronChatMemory", "get_memory"]
