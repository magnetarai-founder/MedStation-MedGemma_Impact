"""
Tests for Agent Sessions (Phase C)

Tests stateful agent workspace sessions:
- Session creation and retrieval
- Session listing and user scoping
- Session plan updates
- Session activity tracking
- Session lifecycle management
"""

import os
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

# Ensure development mode
os.environ.setdefault('ELOHIM_ENV', 'development')

# Skip if agent sessions not available
try:
    from api.agent.orchestration.sessions import (
        create_agent_session,
        get_agent_session,
        list_agent_sessions_for_user,
        update_session_plan,
        touch_session,
        close_session,
        reactivate_session,
    )
    from api.agent.orchestration import session_storage
    SESSIONS_AVAILABLE = True
except ImportError:
    SESSIONS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not SESSIONS_AVAILABLE, reason="Agent sessions not available")


@pytest.fixture(autouse=True)
def use_temp_db(monkeypatch, tmp_path):
    """Use temporary database for tests"""
    test_db = tmp_path / "test_agent_sessions.db"

    def mock_get_db_path():
        return test_db

    monkeypatch.setattr(session_storage, "get_db_path", mock_get_db_path)
    # Reset initialization flag to force schema creation with new path
    session_storage._db_initialized = False
    session_storage.init_db()

    yield test_db


class TestAgentSessionCreation:
    """Test agent session creation"""

    def test_create_session_basic(self):
        """Test creating a basic session"""
        user_id = "user_123"
        repo_root = str(Path(tempfile.gettempdir()) / "test_repo")

        session = create_agent_session(user_id, repo_root)

        assert session.user_id == user_id
        assert session.repo_root == repo_root
        assert session.status == "active"
        assert session.current_plan is None
        assert session.attached_work_item_id is None
        assert session.id.startswith("session_")
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_activity_at, datetime)

    def test_create_session_with_work_item(self):
        """Test creating session with attached work item"""
        user_id = "user_456"
        repo_root = "/path/to/repo"
        work_item_id = "work_item_xyz"

        session = create_agent_session(user_id, repo_root, attached_work_item_id=work_item_id)

        assert session.attached_work_item_id == work_item_id

    def test_session_id_is_unique(self):
        """Test that each session gets a unique ID"""
        user_id = "user_789"
        repo_root = "/path/to/repo"

        session1 = create_agent_session(user_id, repo_root)
        session2 = create_agent_session(user_id, repo_root)

        assert session1.id != session2.id


class TestAgentSessionRetrieval:
    """Test session retrieval operations"""

    def test_get_session_by_id(self):
        """Test retrieving session by ID"""
        user_id = "user_abc"
        repo_root = "/path"

        created = create_agent_session(user_id, repo_root)
        retrieved = get_agent_session(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.user_id == user_id
        assert retrieved.repo_root == repo_root

    def test_get_nonexistent_session(self):
        """Test retrieving non-existent session returns None"""
        result = get_agent_session("session_does_not_exist")
        assert result is None


class TestAgentSessionListing:
    """Test session listing and filtering"""

    def test_list_sessions_for_user(self):
        """Test listing sessions for a user"""
        user_id = "user_list_test"

        session1 = create_agent_session(user_id, "/repo1")
        session2 = create_agent_session(user_id, "/repo2")

        sessions = list_agent_sessions_for_user(user_id)

        assert len(sessions) == 2
        session_ids = [s.id for s in sessions]
        assert session1.id in session_ids
        assert session2.id in session_ids

    def test_list_sessions_scoped_per_user(self):
        """Test that sessions are properly scoped per user"""
        user_a = "user_a"
        user_b = "user_b"

        # Create 2 sessions for user A, 1 for user B
        create_agent_session(user_a, "/repo_a1")
        create_agent_session(user_a, "/repo_a2")
        create_agent_session(user_b, "/repo_b1")

        sessions_a = list_agent_sessions_for_user(user_a)
        sessions_b = list_agent_sessions_for_user(user_b)

        assert len(sessions_a) == 2
        assert len(sessions_b) == 1
        assert all(s.user_id == user_a for s in sessions_a)
        assert all(s.user_id == user_b for s in sessions_b)

    def test_list_active_sessions_only(self):
        """Test filtering for active sessions only"""
        user_id = "user_active_test"

        active_session = create_agent_session(user_id, "/repo_active")
        closed_session = create_agent_session(user_id, "/repo_closed")

        # Close one session
        close_session(closed_session.id)

        # List all sessions
        all_sessions = list_agent_sessions_for_user(user_id, active_only=False)
        assert len(all_sessions) == 2

        # List only active sessions
        active_sessions = list_agent_sessions_for_user(user_id, active_only=True)
        assert len(active_sessions) == 1
        assert active_sessions[0].id == active_session.id
        assert active_sessions[0].status == "active"


class TestAgentSessionPlanUpdate:
    """Test session plan updates"""

    def test_update_session_plan(self):
        """Test updating session with plan data"""
        user_id = "user_plan_test"
        session = create_agent_session(user_id, "/repo")

        plan_data = {
            "steps": [
                {"description": "Step 1", "risk_level": "low", "estimated_files": 2},
                {"description": "Step 2", "risk_level": "medium", "estimated_files": 5},
            ],
            "risks": ["Breaking change"],
            "requires_confirmation": True,
            "estimated_time_min": 30,
            "model_used": "test-model",
        }

        update_session_plan(session.id, plan_data)

        # Retrieve and verify
        updated = get_agent_session(session.id)
        assert updated.current_plan is not None
        assert updated.current_plan["steps"] == plan_data["steps"]
        assert updated.current_plan["risks"] == plan_data["risks"]
        assert updated.last_activity_at > session.last_activity_at

    def test_update_nonexistent_session_plan(self):
        """Test updating plan for non-existent session doesn't crash"""
        # Should not raise exception (graceful degradation)
        update_session_plan("session_fake", {"test": "data"})


class TestAgentSessionActivityTracking:
    """Test session activity tracking"""

    def test_touch_session_updates_activity(self):
        """Test that touching session updates last_activity_at"""
        user_id = "user_touch_test"
        session = create_agent_session(user_id, "/repo")

        original_activity = session.last_activity_at

        # Wait a tiny bit to ensure timestamp difference
        import time
        time.sleep(0.01)

        touch_session(session.id)

        # Retrieve and verify
        updated = get_agent_session(session.id)
        assert updated.last_activity_at > original_activity

    def test_touch_nonexistent_session(self):
        """Test touching non-existent session doesn't crash"""
        # Should not raise exception (graceful degradation)
        touch_session("session_fake")


class TestAgentSessionLifecycle:
    """Test session lifecycle management"""

    def test_close_session(self):
        """Test closing (archiving) a session"""
        user_id = "user_close_test"
        session = create_agent_session(user_id, "/repo")

        assert session.status == "active"

        close_session(session.id)

        # Retrieve and verify
        closed = get_agent_session(session.id)
        assert closed.status == "archived"

    def test_reactivate_session(self):
        """Test reactivating an archived session"""
        user_id = "user_reactivate_test"
        session = create_agent_session(user_id, "/repo")

        # Close and then reactivate
        close_session(session.id)
        reactivate_session(session.id)

        # Retrieve and verify
        reactivated = get_agent_session(session.id)
        assert reactivated.status == "active"


class TestAgentSessionEdgeCases:
    """Test edge cases and error handling"""

    def test_session_with_empty_repo_root(self):
        """Test creating session with empty repo_root"""
        user_id = "user_empty_repo"
        session = create_agent_session(user_id, "")

        assert session.repo_root == ""
        assert session.user_id == user_id

    def test_session_with_long_repo_path(self):
        """Test creating session with very long repo path"""
        user_id = "user_long_path"
        long_path = "/" + ("a" * 500)

        session = create_agent_session(user_id, long_path)

        assert session.repo_root == long_path

    def test_list_sessions_for_nonexistent_user(self):
        """Test listing sessions for user with no sessions"""
        sessions = list_agent_sessions_for_user("user_no_sessions_xyz")
        assert sessions == []


class TestAgentSessionOrdering:
    """Test session ordering"""

    def test_sessions_ordered_by_activity(self):
        """Test that sessions are ordered by last_activity_at DESC"""
        user_id = "user_order_test"

        # Create 3 sessions
        session1 = create_agent_session(user_id, "/repo1")
        session2 = create_agent_session(user_id, "/repo2")
        session3 = create_agent_session(user_id, "/repo3")

        # Touch session1 to make it most recent
        import time
        time.sleep(0.01)
        touch_session(session1.id)

        # List sessions
        sessions = list_agent_sessions_for_user(user_id)

        # session1 should be first (most recent activity)
        assert sessions[0].id == session1.id
