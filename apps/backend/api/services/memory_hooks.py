"""
Memory Hooks for Automatic Embedding Generation

Automatically generates embeddings when new messages are added to chat memory.
This ensures semantic search is always up-to-date without manual backfilling.
"""

from pathlib import Path

from ..utils.structured_logging import get_logger

logger = get_logger(__name__)


class MemoryHooks:
    """
    Hooks for automatic embedding generation on message creation

    Usage:
        hooks = MemoryHooks(db_path)
        await hooks.on_message_added(message_id, session_id, content, team_id)
    """

    def __init__(self, db_path: Path):
        """
        Initialize memory hooks

        Args:
            db_path: Path to chat memory database
        """
        self.db_path = db_path
        self._semantic_search = None

    def _get_semantic_search(self):
        """Lazy-load semantic search engine"""
        if self._semantic_search is None:
            from .semantic_search import get_semantic_search

            self._semantic_search = get_semantic_search(self.db_path)
        return self._semantic_search

    async def on_message_added(
        self, message_id: int, session_id: str, content: str, team_id: str | None = None
    ) -> None:
        """
        Hook called when a new message is added

        Automatically generates and stores embedding for the message.

        Args:
            message_id: Message ID
            session_id: Session ID
            content: Message content
            team_id: Team ID (for team isolation)
        """
        try:
            # Skip short messages
            if len(content.strip()) < 10:
                logger.debug(f"Skipping embedding for short message {message_id}")
                return

            # Generate and store embedding
            search_engine = self._get_semantic_search()
            await search_engine.store_message_embedding(
                message_id=message_id, session_id=session_id, content=content, team_id=team_id
            )

            logger.info(f"Generated embedding for message {message_id}")

        except Exception as e:
            # Log error but don't fail the message creation
            logger.error(
                "Failed to generate embedding for message",
                error=e,
                message_id=message_id,
                session_id=session_id,
            )


# Global hooks instance
_hooks_instance: MemoryHooks | None = None


def get_memory_hooks(db_path: Path) -> MemoryHooks:
    """
    Get or create global MemoryHooks instance

    Args:
        db_path: Path to chat memory database

    Returns:
        MemoryHooks instance
    """
    global _hooks_instance
    if _hooks_instance is None:
        _hooks_instance = MemoryHooks(db_path)
    return _hooks_instance


async def trigger_message_hook(
    message_id: int,
    session_id: str,
    content: str,
    team_id: str | None = None,
    db_path: Path | None = None,
) -> None:
    """
    Trigger message added hook

    Convenience function to trigger embedding generation.

    Args:
        message_id: Message ID
        session_id: Session ID
        content: Message content
        team_id: Team ID
        db_path: Database path (uses default if not provided)
    """
    if db_path is None:
        import os

        data_dir = Path(os.path.expanduser("~/.magnetarcode/data"))
        db_path = data_dir / "chat_memory.db"

    hooks = get_memory_hooks(db_path)
    await hooks.on_message_added(message_id, session_id, content, team_id)
