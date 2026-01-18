"""
Tests for Undo/Redo Action Service

Tests the reversible action management with timeout cleanup.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, patch

from api.undo.service import UndoService
from api.undo.types import UndoAction, UndoResult, ActionType


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def undo_service(temp_db):
    """Create an UndoService with temporary database"""
    return UndoService(db_path=temp_db, default_timeout=5)


class TestActionTypeEnum:
    """Tests for ActionType enum"""

    def test_action_type_values(self):
        """Test action type values"""
        assert ActionType.MESSAGE_SENT == "message_sent"
        assert ActionType.WORKFLOW_CREATED == "workflow_created"
        assert ActionType.FILE_UPLOADED == "file_uploaded"
        assert ActionType.SETTINGS_CHANGED == "settings_changed"

    def test_all_action_types(self):
        """Test all action types exist"""
        values = [e.value for e in ActionType]
        assert "message_sent" in values
        assert "workflow_created" in values
        assert "file_uploaded" in values
        assert "vault_item_created" in values


class TestUndoActionModel:
    """Tests for UndoAction model"""

    def test_create_undo_action(self):
        """Test creating an UndoAction"""
        action = UndoAction(
            id=1,
            action_type=ActionType.MESSAGE_SENT,
            user_id="user_001",
            resource_type="message",
            resource_id="msg_001",
            state_before={"content": "Hello"},
            state_after=None,
            created_at="2025-01-01T00:00:00+00:00",
            expires_at="2025-01-01T00:00:05+00:00",
            is_undone=False,
            timeout_seconds=5
        )

        assert action.id == 1
        assert action.action_type == ActionType.MESSAGE_SENT
        assert action.user_id == "user_001"
        assert action.state_before == {"content": "Hello"}

    def test_undo_action_defaults(self):
        """Test UndoAction default values"""
        action = UndoAction(
            action_type=ActionType.MESSAGE_SENT,
            user_id="user_001",
            resource_type="message",
            resource_id="msg_001",
            state_before={},
            created_at="2025-01-01T00:00:00",
            expires_at="2025-01-01T00:00:05"
        )

        assert action.id is None
        assert action.state_after is None
        assert action.is_undone is False
        assert action.undone_at is None
        assert action.timeout_seconds == 5


class TestUndoResultModel:
    """Tests for UndoResult model"""

    def test_create_undo_result(self):
        """Test creating an UndoResult"""
        result = UndoResult(
            success=True,
            action_id=1,
            action_type=ActionType.MESSAGE_SENT,
            resource_type="message",
            resource_id="msg_001",
            message="Message unsent successfully"
        )

        assert result.success is True
        assert result.action_id == 1
        assert result.message == "Message unsent successfully"


class TestUndoServiceInit:
    """Tests for UndoService initialization"""

    def test_service_initialization(self, temp_db):
        """Test service initializes correctly"""
        service = UndoService(db_path=temp_db, default_timeout=10)

        assert service.db_path == temp_db
        assert service.default_timeout == 10

    def test_service_creates_table(self, temp_db):
        """Test service creates undo_actions table"""
        import sqlite3

        service = UndoService(db_path=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='undo_actions'"
            )
            result = cursor.fetchone()

        assert result is not None
        assert result[0] == "undo_actions"


class TestRegisterHandler:
    """Tests for register_undo_handler"""

    def test_register_handler(self, undo_service):
        """Test registering an undo handler"""
        async def mock_handler(action):
            return True

        undo_service.register_undo_handler(ActionType.MESSAGE_SENT, mock_handler)

        assert ActionType.MESSAGE_SENT in undo_service._undo_handlers
        assert undo_service._undo_handlers[ActionType.MESSAGE_SENT] == mock_handler

    def test_register_multiple_handlers(self, undo_service):
        """Test registering multiple handlers"""
        async def handler1(action):
            return True

        async def handler2(action):
            return True

        undo_service.register_undo_handler(ActionType.MESSAGE_SENT, handler1)
        undo_service.register_undo_handler(ActionType.FILE_UPLOADED, handler2)

        assert len(undo_service._undo_handlers) == 2


class TestCreateAction:
    """Tests for create_action"""

    def test_create_basic_action(self, undo_service):
        """Test creating a basic undo action"""
        action = undo_service.create_action(
            action_type=ActionType.MESSAGE_SENT,
            user_id="user_001",
            resource_type="message",
            resource_id="msg_001",
            state_before={"content": "Hello World"}
        )

        assert action.id is not None
        assert action.action_type == ActionType.MESSAGE_SENT
        assert action.user_id == "user_001"
        assert action.state_before == {"content": "Hello World"}

    def test_create_action_with_state_after(self, undo_service):
        """Test creating action with state_after"""
        action = undo_service.create_action(
            action_type=ActionType.SETTINGS_CHANGED,
            user_id="user_001",
            resource_type="settings",
            resource_id="user_settings",
            state_before={"theme": "light"},
            state_after={"theme": "dark"}
        )

        assert action.state_before == {"theme": "light"}
        assert action.state_after == {"theme": "dark"}

    def test_create_action_custom_timeout(self, undo_service):
        """Test creating action with custom timeout"""
        action = undo_service.create_action(
            action_type=ActionType.MESSAGE_SENT,
            user_id="user_001",
            resource_type="message",
            resource_id="msg_001",
            state_before={},
            timeout_seconds=30
        )

        assert action.timeout_seconds == 30

    def test_create_action_sets_expiry(self, undo_service):
        """Test action expiry is set correctly"""
        action = undo_service.create_action(
            action_type=ActionType.MESSAGE_SENT,
            user_id="user_001",
            resource_type="message",
            resource_id="msg_001",
            state_before={},
            timeout_seconds=10
        )

        created = datetime.fromisoformat(action.created_at)
        expires = datetime.fromisoformat(action.expires_at)

        delta = expires - created
        assert delta.total_seconds() == 10

    def test_create_multiple_actions(self, undo_service):
        """Test creating multiple actions"""
        action1 = undo_service.create_action(
            action_type=ActionType.MESSAGE_SENT,
            user_id="user_001",
            resource_type="message",
            resource_id="msg_001",
            state_before={}
        )

        action2 = undo_service.create_action(
            action_type=ActionType.FILE_UPLOADED,
            user_id="user_001",
            resource_type="file",
            resource_id="file_001",
            state_before={}
        )

        assert action1.id != action2.id


class TestGetAction:
    """Tests for get_action"""

    def test_get_existing_action(self, undo_service):
        """Test getting an existing action"""
        created = undo_service.create_action(
            action_type=ActionType.MESSAGE_SENT,
            user_id="user_001",
            resource_type="message",
            resource_id="msg_001",
            state_before={"content": "Hello"}
        )

        retrieved = undo_service.get_action(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.action_type == ActionType.MESSAGE_SENT
        assert retrieved.state_before == {"content": "Hello"}

    def test_get_nonexistent_action(self, undo_service):
        """Test getting a nonexistent action"""
        result = undo_service.get_action(99999)

        assert result is None


class TestGetPendingActions:
    """Tests for get_pending_actions"""

    def test_get_pending_empty(self, undo_service):
        """Test getting pending actions when empty"""
        actions = undo_service.get_pending_actions("user_001")

        assert actions == []

    def test_get_pending_with_actions(self, undo_service):
        """Test getting pending actions"""
        undo_service.create_action(
            action_type=ActionType.MESSAGE_SENT,
            user_id="user_001",
            resource_type="message",
            resource_id="msg_001",
            state_before={},
            timeout_seconds=3600  # Long timeout so it doesn't expire
        )

        actions = undo_service.get_pending_actions("user_001")

        assert len(actions) == 1
        assert actions[0].action_type == ActionType.MESSAGE_SENT

    def test_get_pending_filters_by_user(self, undo_service):
        """Test pending actions are filtered by user"""
        undo_service.create_action(
            action_type=ActionType.MESSAGE_SENT,
            user_id="user_001",
            resource_type="message",
            resource_id="msg_001",
            state_before={},
            timeout_seconds=3600
        )

        undo_service.create_action(
            action_type=ActionType.MESSAGE_SENT,
            user_id="user_002",
            resource_type="message",
            resource_id="msg_002",
            state_before={},
            timeout_seconds=3600
        )

        user1_actions = undo_service.get_pending_actions("user_001")
        user2_actions = undo_service.get_pending_actions("user_002")

        assert len(user1_actions) == 1
        assert len(user2_actions) == 1
        assert user1_actions[0].user_id == "user_001"


class TestUndoServiceActionTypes:
    """Tests for various action types"""

    @pytest.mark.parametrize("action_type", list(ActionType))
    def test_create_all_action_types(self, undo_service, action_type):
        """Test creating actions for all action types"""
        action = undo_service.create_action(
            action_type=action_type,
            user_id="user_001",
            resource_type="test",
            resource_id="test_001",
            state_before={"test": True}
        )

        assert action.action_type == action_type
        assert action.id is not None
