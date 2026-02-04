"""
MagnetarChatMemory - Facade Class

This is now a thin facade that delegates to specialized components:
- DatabaseManager: Connection and schema management
- SessionStore: Session CRUD operations
- MessageStore: Message storage and retrieval
- SummaryManager: Conversation summaries
- PreferenceStore: Model preferences
- DocumentStore: RAG document operations
- AnalyticsEngine: Analytics queries

The public API remains identical for backward compatibility.
"""
import logging
from pathlib import Path
from typing import Any

from .analytics_engine import AnalyticsEngine
from .db_manager import DatabaseManager
from .document_store import DocumentStore
from .message_store import MessageStore
from .models import ConversationEvent
from .preference_store import PreferenceStore
from .session_store import SessionStore
from .summary_manager import SummaryManager

logger = logging.getLogger(__name__)


class MagnetarChatMemory:
    """
    Advanced chat memory system for MagnetarCode.

    This facade class maintains backward compatibility while
    delegating to specialized single-responsibility components.

    Features:
    - Stores full message history
    - Creates rolling summaries
    - Tracks model switches
    - Preserves context across sessions
    - Thread-safe with connection-per-thread pattern
    """

    def __init__(self, db_path: Path | None = None):
        """
        Initialize chat memory with all component stores.

        Args:
            db_path: Optional custom database path
        """
        # Initialize shared database manager
        self._db_manager = DatabaseManager(db_path)

        # Initialize component stores
        self._sessions = SessionStore(self._db_manager)
        self._messages = MessageStore(self._db_manager)
        self._summaries = SummaryManager(self._db_manager)
        self._preferences = PreferenceStore(self._db_manager)
        self._documents = DocumentStore(self._db_manager)
        self._analytics = AnalyticsEngine(self._db_manager, self._sessions)

    # =========================================================================
    # Session Operations (delegated to SessionStore)
    # =========================================================================

    def create_session(
        self,
        session_id: str,
        title: str,
        model: str,
        user_id: str,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new chat session for user."""
        return self._sessions.create(session_id, title, model, user_id, team_id)

    def get_session(
        self,
        session_id: str,
        user_id: str | None = None,
        role: str | None = None,
        team_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Get session metadata (user-filtered or team-filtered)."""
        return self._sessions.get(session_id, user_id, role, team_id)

    def list_sessions(
        self,
        user_id: str | None = None,
        role: str | None = None,
        team_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List chat sessions (user-filtered for ALL users)."""
        return self._sessions.list(user_id, role, team_id)

    def list_all_sessions_admin(self) -> list[dict[str, Any]]:
        """List ALL chat sessions across all users (Founder Rights admin access only)."""
        return self._sessions.list_all_admin()

    def list_user_sessions_admin(self, target_user_id: str) -> list[dict[str, Any]]:
        """List specific user's chat sessions (Founder Rights admin access only)."""
        return self._sessions.list_user_sessions_admin(target_user_id)

    def delete_session(
        self,
        session_id: str,
        user_id: str | None = None,
        role: str | None = None,
    ) -> bool:
        """Delete a chat session (user-filtered unless Founder Rights)."""
        return self._sessions.delete(session_id, user_id, role)

    # =========================================================================
    # Message Operations (delegated to MessageStore)
    # =========================================================================

    def add_message(self, session_id: str, event: ConversationEvent):
        """Add a message to the session."""
        # Get session owner and team_id
        owner_id, team_id = self._sessions.get_owner_and_team(session_id)

        # Add message
        self._messages.add(session_id, event, owner_id, team_id)

        # Update session metadata
        self._sessions.increment_message_count(session_id)

        # Track model usage
        if event.model:
            session = self.get_session(session_id)
            if session:
                models_used = set(session.get("models_used", []))
                models_used.add(event.model)
                self._sessions.update_models_used(session_id, models_used)

    def get_messages(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[ConversationEvent]:
        """Get messages for a session."""
        return self._messages.get_all(session_id, limit)

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[ConversationEvent]:
        """Get recent messages for context window."""
        return self._messages.get_recent(session_id, limit)

    def get_messages_for_sessions(
        self,
        session_ids: list[str],
    ) -> dict[str, list[ConversationEvent]]:
        """Batch fetch messages for multiple sessions (prevents N+1 queries)."""
        return self._messages.get_for_sessions(session_ids)

    def search_messages_semantic(
        self,
        query: str,
        limit: int = 10,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search across messages using semantic similarity."""
        return self._messages.search_semantic(query, limit, user_id, team_id)

    # =========================================================================
    # Summary Operations (delegated to SummaryManager)
    # =========================================================================

    def update_summary(
        self,
        session_id: str,
        events: list[ConversationEvent] | None = None,
        max_events: int = 30,
        max_summary_chars: int = 1200,
    ):
        """Create or update a rolling summary of the conversation."""
        # Get recent events if not provided
        if events is None:
            events = self.get_recent_messages(session_id, limit=max_events)

        self._summaries.update(session_id, events, max_events, max_summary_chars)

    def get_summary(self, session_id: str) -> dict[str, Any] | None:
        """Get conversation summary."""
        return self._summaries.get(session_id)

    def update_session_title(
        self,
        session_id: str,
        title: str,
        auto_titled: bool = False,
    ):
        """Update session title."""
        self._summaries.update_session_title(session_id, title, auto_titled)

    # =========================================================================
    # Preference Operations (delegated to PreferenceStore)
    # =========================================================================

    def update_session_model(self, session_id: str, model: str) -> None:
        """Update the model for a chat session."""
        self._preferences.update_session_model(session_id, model)

    def update_model_preferences(
        self,
        session_id: str,
        selected_mode: str,
        selected_model_id: str | None = None,
    ) -> None:
        """Update model selection preferences for a chat session."""
        self._preferences.update_model_preferences(
            session_id, selected_mode, selected_model_id
        )

    def get_model_preferences(self, session_id: str) -> dict[str, Any]:
        """Get model selection preferences for a chat session."""
        return self._preferences.get_model_preferences(session_id)

    def set_session_archived(self, session_id: str, archived: bool) -> None:
        """Archive or unarchive a chat session."""
        self._preferences.set_session_archived(session_id, archived)

    # =========================================================================
    # Document Operations (delegated to DocumentStore)
    # =========================================================================

    def store_document_chunks(self, session_id: str, chunks: list[dict[str, Any]]):
        """Store document chunks for RAG."""
        self._documents.store_chunks(session_id, chunks)

    def has_documents(self, session_id: str) -> bool:
        """Check if a session has any uploaded documents."""
        return self._documents.has_documents(session_id)

    def search_document_chunks(
        self,
        session_id: str,
        query_embedding: list[float],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Search for relevant document chunks using semantic similarity."""
        return self._documents.search_chunks(session_id, query_embedding, top_k)

    # =========================================================================
    # Analytics Operations (delegated to AnalyticsEngine)
    # =========================================================================

    def get_analytics(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        """Get analytics for a session or scoped analytics."""
        return self._analytics.get_analytics(session_id, user_id, team_id)

    # Expose internal methods for backward compatibility with tests
    def _get_session_analytics(
        self,
        conn,
        session_id: str,
        user_id: str | None,
        team_id: str | None,
    ) -> dict[str, Any]:
        """Internal method for session analytics (backward compat)."""
        return self._analytics.get_session_analytics(session_id, user_id, team_id)

    def _get_team_analytics(self, conn, team_id: str) -> dict[str, Any]:
        """Internal method for team analytics (backward compat)."""
        return self._analytics.get_team_analytics(team_id)

    def _get_user_analytics(self, conn, user_id: str) -> dict[str, Any]:
        """Internal method for user analytics (backward compat)."""
        return self._analytics.get_user_analytics(user_id)
