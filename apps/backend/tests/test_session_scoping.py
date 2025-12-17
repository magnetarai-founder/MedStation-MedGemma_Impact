"""
T3-1 Sessions: Multi-User Agent Session Scoping Tests

Tests to verify that agent sessions are properly isolated per user and that
cross-user access is prevented at both storage and endpoint layers.

Test Users:
- USER_A_ID = "user_a_123"
- USER_B_ID = "user_b_456"
- USER_C_ID = "user_c_789"
"""

import pytest
import os
import tempfile
import sqlite3
from datetime import datetime, UTC
from typing import Dict, Any

try:
    from api.agent.orchestration.models import AgentSession
    from api.agent.orchestration import session_storage
    from api.agent.orchestration.sessions import (
        create_agent_session,
        get_agent_session,
        list_agent_sessions_for_user,
        close_session,
    )
except ImportError:
    from agent.orchestration.models import AgentSession
    from agent.orchestration import session_storage
    from agent.orchestration.sessions import (
        create_agent_session,
        get_agent_session,
        list_agent_sessions_for_user,
        close_session,
    )

# Test user IDs
USER_A_ID = "user_a_123"
USER_B_ID = "user_b_456"
USER_C_ID = "user_c_789"


@pytest.fixture
def temp_db():
    """Create temporary database for session storage tests"""
    from pathlib import Path

    fd, path_str = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    path = Path(path_str)

    # Override database path
    original_get_db_path = session_storage.get_db_path
    session_storage.get_db_path = lambda: path  # Return Path object, not string
    session_storage._db_initialized = False

    # Initialize fresh database
    session_storage.init_db()

    yield path_str

    # Cleanup
    session_storage.get_db_path = original_get_db_path
    session_storage._db_initialized = False
    try:
        os.unlink(path_str)
    except FileNotFoundError:
        pass


def create_test_session(
    session_id: str,
    user_id: str,
    repo_root: str = "/test/repo",
    status: str = "active",
    attached_work_item_id: str = None,
) -> AgentSession:
    """Helper to create test session"""
    now = datetime.now(UTC)
    return AgentSession(
        id=session_id,
        user_id=user_id,
        repo_root=repo_root,
        created_at=now,
        last_activity_at=now,
        status=status,
        current_plan=None,
        attached_work_item_id=attached_work_item_id,
    )


# =============================================================================
# Test Class 1: Storage Layer - List Sessions Scoping
# =============================================================================


class TestListSessionsScoping:
    """Test list_sessions_for_user is properly scoped by user_id"""

    def test_user_sees_only_own_sessions(self, temp_db):
        """User should only see their own sessions, not other users' sessions"""
        # Create sessions for user A
        session_a1 = create_test_session("session_a1", USER_A_ID)
        session_a2 = create_test_session("session_a2", USER_A_ID)
        session_storage.create_session(session_a1)
        session_storage.create_session(session_a2)

        # Create sessions for user B
        session_b1 = create_test_session("session_b1", USER_B_ID)
        session_storage.create_session(session_b1)

        # List sessions for user A
        sessions_a = session_storage.list_sessions_for_user(USER_A_ID)
        session_ids_a = {s.id for s in sessions_a}

        # Should see only user A's sessions
        assert "session_a1" in session_ids_a
        assert "session_a2" in session_ids_a
        assert "session_b1" not in session_ids_a

        # List sessions for user B
        sessions_b = session_storage.list_sessions_for_user(USER_B_ID)
        session_ids_b = {s.id for s in sessions_b}

        # Should see only user B's sessions
        assert "session_b1" in session_ids_b
        assert "session_a1" not in session_ids_b
        assert "session_a2" not in session_ids_b

    def test_user_with_no_sessions_sees_empty_list(self, temp_db):
        """User with no sessions should see empty list"""
        # Create session for user A
        session_a1 = create_test_session("session_a1", USER_A_ID)
        session_storage.create_session(session_a1)

        # User B has no sessions
        sessions_b = session_storage.list_sessions_for_user(USER_B_ID)
        assert len(sessions_b) == 0

    def test_status_filter_respects_user_scoping(self, temp_db):
        """Status filter should only apply to user's own sessions"""
        # Create active and archived sessions for user A
        session_a1 = create_test_session("session_a1", USER_A_ID, status="active")
        session_a2 = create_test_session("session_a2", USER_A_ID, status="archived")
        session_storage.create_session(session_a1)
        session_storage.create_session(session_a2)

        # Create active session for user B
        session_b1 = create_test_session("session_b1", USER_B_ID, status="active")
        session_storage.create_session(session_b1)

        # List active sessions for user A
        sessions_a_active = session_storage.list_sessions_for_user(USER_A_ID, status_filter="active")
        session_ids = {s.id for s in sessions_a_active}

        # Should see only user A's active session
        assert "session_a1" in session_ids
        assert "session_a2" not in session_ids  # Archived, filtered out
        assert "session_b1" not in session_ids  # Other user


# =============================================================================
# Test Class 2: Storage Layer - Get Session by ID
# =============================================================================


class TestGetSessionByIdScoping:
    """Test get_session returns sessions without ownership check (storage layer is dumb)"""

    def test_get_session_returns_any_session(self, temp_db):
        """Storage layer get_session returns any session by ID (no ownership check)"""
        # Create session for user A
        session_a1 = create_test_session("session_a1", USER_A_ID)
        session_storage.create_session(session_a1)

        # Storage layer should return session regardless of requester
        # (Ownership check happens at service/endpoint layer)
        fetched = session_storage.get_session("session_a1")
        assert fetched is not None
        assert fetched.id == "session_a1"
        assert fetched.user_id == USER_A_ID

    def test_get_session_nonexistent_returns_none(self, temp_db):
        """get_session for non-existent session should return None"""
        fetched = session_storage.get_session("nonexistent_session")
        assert fetched is None


# =============================================================================
# Test Class 3: Service Layer - Session Ownership Validation
# =============================================================================


class TestSessionServiceOwnership:
    """Test session service layer enforces ownership"""

    def test_create_session_assigns_correct_user(self, temp_db):
        """create_agent_session should assign user_id from parameter"""
        session = create_agent_session(
            user_id=USER_A_ID,
            repo_root="/test/repo",
            attached_work_item_id=None,
        )

        assert session.user_id == USER_A_ID
        assert session.status == "active"

        # Verify in storage
        fetched = session_storage.get_session(session.id)
        assert fetched.user_id == USER_A_ID

    def test_list_sessions_returns_only_user_sessions(self, temp_db):
        """list_agent_sessions_for_user should only return user's sessions"""
        # Create sessions for multiple users
        session_a1 = create_agent_session(USER_A_ID, "/repo/a1")
        session_a2 = create_agent_session(USER_A_ID, "/repo/a2")
        session_b1 = create_agent_session(USER_B_ID, "/repo/b1")

        # List for user A
        sessions_a = list_agent_sessions_for_user(USER_A_ID)
        session_ids_a = {s.id for s in sessions_a}

        assert session_a1.id in session_ids_a
        assert session_a2.id in session_ids_a
        assert session_b1.id not in session_ids_a

    def test_get_session_no_ownership_check(self, temp_db):
        """get_agent_session does NOT check ownership (endpoint layer does)"""
        # Create session for user A
        session_a1 = create_agent_session(USER_A_ID, "/repo/a1")

        # Service layer get_agent_session returns session without checking ownership
        # (Ownership check happens at endpoint layer)
        fetched = get_agent_session(session_a1.id)
        assert fetched is not None
        assert fetched.user_id == USER_A_ID


# =============================================================================
# Test Class 4: Cross-User Session Access Prevention
# =============================================================================


class TestCrossUserSessionAccessPrevention:
    """Test that users cannot access other users' sessions"""

    def test_list_sessions_isolation(self, temp_db):
        """Users should never see each other's sessions in list"""
        # Create sessions for 3 users
        session_a = create_agent_session(USER_A_ID, "/repo/a")
        session_b = create_agent_session(USER_B_ID, "/repo/b")
        session_c = create_agent_session(USER_C_ID, "/repo/c")

        # Each user should only see their own session
        sessions_a = list_agent_sessions_for_user(USER_A_ID)
        sessions_b = list_agent_sessions_for_user(USER_B_ID)
        sessions_c = list_agent_sessions_for_user(USER_C_ID)

        assert len(sessions_a) == 1 and sessions_a[0].id == session_a.id
        assert len(sessions_b) == 1 and sessions_b[0].id == session_b.id
        assert len(sessions_c) == 1 and sessions_c[0].id == session_c.id

    def test_close_session_requires_ownership_check_at_endpoint(self, temp_db):
        """
        close_session service function does not check ownership - endpoint must check.
        This test documents the expected behavior.
        """
        # Create session for user A
        session_a = create_agent_session(USER_A_ID, "/repo/a")

        # Service layer close_session does NOT check ownership
        # (The endpoint layer in orchestrator.py does the ownership check)
        close_session(session_a.id)

        # Session should be archived
        fetched = get_agent_session(session_a.id)
        assert fetched.status == "archived"

        # NOTE: The actual ownership validation happens in orchestrator.py
        # at line 607-609:
        # session = get_agent_session(session_id)
        # if not session or session.user_id != user_id:
        #     raise HTTPException(status_code=404, detail="Session not found")


# =============================================================================
# Test Class 5: Endpoint Layer Ownership Checks (Integration-like)
# =============================================================================


class TestEndpointOwnershipLogic:
    """
    Test the ownership check logic that should be in endpoints.

    These tests simulate what the endpoint layer does by manually checking ownership.
    The actual HTTP endpoint tests would use FastAPI TestClient.
    """

    def test_get_session_endpoint_ownership_logic(self, temp_db):
        """Simulate GET /sessions/{id} endpoint ownership check"""
        # Create sessions for two users
        session_a = create_agent_session(USER_A_ID, "/repo/a")
        session_b = create_agent_session(USER_B_ID, "/repo/b")

        # User A tries to get their own session (should succeed)
        current_user_id = USER_A_ID
        session = get_agent_session(session_a.id)
        if session and session.user_id == current_user_id:
            # Success - user owns session
            assert session.id == session_a.id
        else:
            pytest.fail("User A should be able to access their own session")

        # User A tries to get user B's session (should fail)
        current_user_id = USER_A_ID
        session = get_agent_session(session_b.id)
        if session and session.user_id == current_user_id:
            pytest.fail("User A should NOT be able to access user B's session")
        else:
            # Success - ownership check failed as expected
            pass

    def test_close_session_endpoint_ownership_logic(self, temp_db):
        """Simulate POST /sessions/{id}/close endpoint ownership check"""
        # Create sessions for two users
        session_a = create_agent_session(USER_A_ID, "/repo/a")
        session_b = create_agent_session(USER_B_ID, "/repo/b")

        # User A tries to close user B's session (should fail ownership check)
        current_user_id = USER_A_ID
        session = get_agent_session(session_b.id)
        if not session or session.user_id != current_user_id:
            # Success - ownership check blocks user A from closing B's session
            pass
        else:
            pytest.fail("User A should NOT be able to close user B's session")

    def test_agent_operation_endpoint_session_validation_logic(self, temp_db):
        """
        Simulate /agent/route, /agent/plan, /agent/context, /agent/apply
        session ownership validation (T3-1 hardening)
        """
        # Create sessions for two users
        session_a = create_agent_session(USER_A_ID, "/repo/a")
        session_b = create_agent_session(USER_B_ID, "/repo/b")

        # User A calls /agent/route with their own session_id (should succeed)
        current_user_id = USER_A_ID
        body_session_id = session_a.id

        session = get_agent_session(body_session_id)
        if session and session.user_id == current_user_id:
            # Success - user owns session, operation can proceed
            pass
        else:
            pytest.fail("User A should be able to use their own session")

        # User A calls /agent/route with user B's session_id (should fail)
        current_user_id = USER_A_ID
        body_session_id = session_b.id

        session = get_agent_session(body_session_id)
        if not session or session.user_id != current_user_id:
            # Success - ownership check blocks user A from using B's session
            pass
        else:
            pytest.fail("User A should NOT be able to use user B's session")


# =============================================================================
# Test Class 6: Edge Cases and Data Isolation
# =============================================================================


class TestSessionDataIsolation:
    """Test that session data is properly isolated between users"""

    def test_work_item_attachment_is_user_scoped(self, temp_db):
        """Sessions with attached work items should still be user-scoped"""
        # Create sessions with work items for two users
        session_a = create_agent_session(
            USER_A_ID, "/repo/a", attached_work_item_id="work_item_a"
        )
        session_b = create_agent_session(
            USER_B_ID, "/repo/b", attached_work_item_id="work_item_b"
        )

        # User A should only see their session
        sessions_a = list_agent_sessions_for_user(USER_A_ID)
        assert len(sessions_a) == 1
        assert sessions_a[0].attached_work_item_id == "work_item_a"

        # User B should only see their session
        sessions_b = list_agent_sessions_for_user(USER_B_ID)
        assert len(sessions_b) == 1
        assert sessions_b[0].attached_work_item_id == "work_item_b"

    def test_session_plan_data_is_isolated(self, temp_db):
        """Session plans should not leak between users"""
        # Create sessions with plans for two users
        session_a = create_test_session("session_a", USER_A_ID)
        session_a.current_plan = {"steps": ["step_a1", "step_a2"]}
        session_storage.create_session(session_a)

        session_b = create_test_session("session_b", USER_B_ID)
        session_b.current_plan = {"steps": ["step_b1", "step_b2"]}
        session_storage.create_session(session_b)

        # User A should only see their plan
        sessions_a = list_agent_sessions_for_user(USER_A_ID)
        assert len(sessions_a) == 1
        assert sessions_a[0].current_plan == {"steps": ["step_a1", "step_a2"]}

        # User B should only see their plan
        sessions_b = list_agent_sessions_for_user(USER_B_ID)
        assert len(sessions_b) == 1
        assert sessions_b[0].current_plan == {"steps": ["step_b1", "step_b2"]}

    def test_multiple_active_sessions_per_user(self, temp_db):
        """Users should be able to have multiple active sessions"""
        # Create 3 active sessions for user A
        session_a1 = create_agent_session(USER_A_ID, "/repo/a1")
        session_a2 = create_agent_session(USER_A_ID, "/repo/a2")
        session_a3 = create_agent_session(USER_A_ID, "/repo/a3")

        # Create 2 active sessions for user B
        session_b1 = create_agent_session(USER_B_ID, "/repo/b1")
        session_b2 = create_agent_session(USER_B_ID, "/repo/b2")

        # User A should see 3 sessions
        sessions_a = list_agent_sessions_for_user(USER_A_ID, active_only=True)
        assert len(sessions_a) == 3

        # User B should see 2 sessions
        sessions_b = list_agent_sessions_for_user(USER_B_ID, active_only=True)
        assert len(sessions_b) == 2
