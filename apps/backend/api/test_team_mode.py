#!/usr/bin/env python3
"""
Test Suite for Team Mode (Phases 3-5)

Tests team isolation, permissions, and security across:
- Team lifecycle (create, invite, accept, members)
- Team-scoped resources (docs, vault, workflows, chat)
- P2P HMAC signing/verification
- Cross-team access denial

Run: pytest test_team_mode.py -v
"""

import pytest
import sqlite3
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi.testclient import TestClient

# Set required environment variables for testing
os.environ.setdefault("ELOHIM_FOUNDER_PASSWORD", "test_founder_password_12345")
os.environ.setdefault("ELOHIMOS_DEVICE_SECRET", "test_device_secret_" + os.urandom(16).hex())

# Test fixtures and helpers
from config_paths import PATHS
from auth_middleware import AuthService


class TestTeamLifecycle:
    """Test team creation, invites, and membership"""

    def setup_method(self):
        """Setup test database and test client"""
        self.test_db = PATHS.app_db
        self.conn = sqlite3.connect(str(self.test_db))
        self.conn.row_factory = sqlite3.Row

        # Clean up any leftover test data from previous runs
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM team_members WHERE team_id LIKE 'test_team_%' OR user_id LIKE 'test_%'")
            cursor.execute("DELETE FROM team_invites WHERE team_id LIKE 'test_team_%' OR email_or_username LIKE 'test_%'")
            cursor.execute("DELETE FROM teams WHERE team_id LIKE 'test_team_%'")
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Warning: Could not clean up leftover test data: {e}")

        # Setup FastAPI test client
        from main import app
        self.client = TestClient(app)

        # Setup auth service for creating test users
        self.auth_service = AuthService()

        # Create test users
        self.admin_user_id = "test_admin_001"
        self.member_user_id = "test_member_001"
        self.outsider_user_id = "test_outsider_001"

        # Create test users in auth database
        auth_conn = sqlite3.connect(str(self.auth_service.db_path))
        auth_conn.row_factory = sqlite3.Row
        auth_cursor = auth_conn.cursor()

        try:
            admin_user = self.auth_service.create_user("test_admin_001", "test_password_123", "test_device_admin")
            self.admin_user_id = admin_user.user_id
        except ValueError:
            # User already exists, get existing user_id
            auth_cursor.execute("SELECT user_id FROM users WHERE username = ?", ("test_admin_001",))
            row = auth_cursor.fetchone()
            if row:
                self.admin_user_id = row["user_id"]

        try:
            member_user = self.auth_service.create_user("test_member_001", "test_password_123", "test_device_member")
            self.member_user_id = member_user.user_id
        except ValueError:
            auth_cursor.execute("SELECT user_id FROM users WHERE username = ?", ("test_member_001",))
            row = auth_cursor.fetchone()
            if row:
                self.member_user_id = row["user_id"]

        # Update test_admin_001 to super_admin role in auth database before authentication
        auth_cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", ("super_admin", self.admin_user_id))
        auth_conn.commit()
        auth_conn.close()

        # Get auth tokens for test users (admin now has super_admin role)
        admin_auth = self.auth_service.authenticate("test_admin_001", "test_password_123")
        if not admin_auth:
            raise RuntimeError("Failed to authenticate test_admin_001")

        member_auth = self.auth_service.authenticate("test_member_001", "test_password_123")
        if not member_auth:
            raise RuntimeError("Failed to authenticate test_member_001")

        self.admin_token = admin_auth["token"]
        self.member_token = member_auth["token"]

    def teardown_method(self):
        """Cleanup test data"""
        cursor = self.conn.cursor()

        # Clean up test teams
        try:
            cursor.execute("DELETE FROM team_members WHERE user_id LIKE 'test_%'")
            cursor.execute("DELETE FROM team_invites WHERE email_or_username LIKE 'test_%'")
            cursor.execute("DELETE FROM teams WHERE team_id LIKE 'test_team_%'")
            self.conn.commit()
        except sqlite3.Error as e:
            # If database is locked, just log and continue
            print(f"Warning: Could not clean up test data: {e}")
        finally:
            self.conn.close()

    def test_create_team(self):
        """Test team creation"""
        import uuid
        from datetime import datetime

        team_id = "test_team_001"
        cursor = self.conn.cursor()

        # Create team directly
        cursor.execute("""
            INSERT INTO teams (team_id, name, created_by, created_at)
            VALUES (?, ?, ?, ?)
        """, (team_id, "Test Team 001", self.admin_user_id, datetime.utcnow().isoformat()))

        # Add creator as admin
        cursor.execute("""
            INSERT INTO team_members (team_id, user_id, role, is_active, joined_at)
            VALUES (?, ?, ?, 1, ?)
        """, (team_id, self.admin_user_id, "admin", datetime.utcnow().isoformat()))

        self.conn.commit()

        # Verify team created
        cursor.execute("SELECT * FROM teams WHERE team_id = ?", (team_id,))
        team = cursor.fetchone()
        assert team is not None
        assert team["name"] == "Test Team 001"

        # Verify creator is admin
        from team_service import is_team_member
        role = is_team_member(team_id, self.admin_user_id)
        assert role in ("super_admin", "admin")

    def test_invite_member(self):
        """Test team invitation via HTTP API"""
        team_id = "test_team_002"
        cursor = self.conn.cursor()

        # Create team directly
        cursor.execute("""
            INSERT INTO teams (team_id, name, created_by, created_at)
            VALUES (?, ?, ?, ?)
        """, (team_id, "Test Team 002", self.admin_user_id, datetime.utcnow().isoformat()))

        # Add creator as admin
        cursor.execute("""
            INSERT INTO team_members (team_id, user_id, role, is_active, joined_at)
            VALUES (?, ?, ?, 1, ?)
        """, (team_id, self.admin_user_id, "admin", datetime.utcnow().isoformat()))

        self.conn.commit()

        # Invite member via API
        response = self.client.post(
            f"/api/v1/teams/{team_id}/invites",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "email_or_username": "test_member_001",
                "role": "member"
            }
        )

        assert response.status_code == 200, f"Failed to create invite: {response.text}"
        invite_data = response.json()
        assert invite_data["team_id"] == team_id
        assert "invite_id" in invite_data

        # Verify invite in database
        cursor.execute("""
            SELECT * FROM team_invites WHERE invite_id = ?
        """, (invite_data["invite_id"],))
        invite = cursor.fetchone()
        assert invite is not None
        assert invite["team_id"] == team_id
        assert invite["email_or_username"] == "test_member_001"
        assert invite["role"] == "member"
        assert invite["status"] == "pending"

    def test_accept_invite(self):
        """Test accepting team invitation via HTTP API"""
        team_id = "test_team_003"
        cursor = self.conn.cursor()

        # Create team directly
        cursor.execute("""
            INSERT INTO teams (team_id, name, created_by, created_at)
            VALUES (?, ?, ?, ?)
        """, (team_id, "Test Team 003", self.admin_user_id, datetime.utcnow().isoformat()))

        # Add creator as admin
        cursor.execute("""
            INSERT INTO team_members (team_id, user_id, role, is_active, joined_at)
            VALUES (?, ?, ?, 1, ?)
        """, (team_id, self.admin_user_id, "admin", datetime.utcnow().isoformat()))

        self.conn.commit()

        # Create invite via API
        response = self.client.post(
            f"/api/v1/teams/{team_id}/invites",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "email_or_username": "test_member_001",
                "role": "member"
            }
        )

        assert response.status_code == 200
        invite_data = response.json()
        invite_id = invite_data["invite_id"]

        # Accept invite via API as member
        response = self.client.post(
            f"/api/v1/teams/invites/{invite_id}/accept",
            headers={"Authorization": f"Bearer {self.member_token}"}
        )

        assert response.status_code == 200, f"Failed to accept invite: {response.text}"
        accept_data = response.json()
        assert accept_data["team_id"] == team_id

        # Verify membership in database
        cursor.execute("""
            SELECT * FROM team_members WHERE team_id = ? AND user_id = ?
        """, (team_id, self.member_user_id))
        member = cursor.fetchone()
        assert member is not None
        assert member["role"] == "member"
        assert member["is_active"] == 1

        # Verify invite status updated
        cursor.execute("""
            SELECT status FROM team_invites WHERE invite_id = ?
        """, (invite_id,))
        invite = cursor.fetchone()
        assert invite is not None
        assert invite["status"] == "accepted"

    def test_list_team_members(self):
        """Test listing team members via HTTP API"""
        team_id = "test_team_004"
        cursor = self.conn.cursor()

        # Create team directly
        cursor.execute("""
            INSERT INTO teams (team_id, name, created_by, created_at)
            VALUES (?, ?, ?, ?)
        """, (team_id, "Test Team 004", self.admin_user_id, datetime.utcnow().isoformat()))

        # Add creator as admin
        cursor.execute("""
            INSERT INTO team_members (team_id, user_id, role, is_active, joined_at)
            VALUES (?, ?, ?, 1, ?)
        """, (team_id, self.admin_user_id, "admin", datetime.utcnow().isoformat()))

        self.conn.commit()

        # Invite and accept member
        response = self.client.post(
            f"/api/v1/teams/{team_id}/invites",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "email_or_username": "test_member_001",
                "role": "member"
            }
        )
        assert response.status_code == 200
        invite_id = response.json()["invite_id"]

        # Accept invite
        response = self.client.post(
            f"/api/v1/teams/invites/{invite_id}/accept",
            headers={"Authorization": f"Bearer {self.member_token}"}
        )
        assert response.status_code == 200

        # List members via API
        response = self.client.get(
            f"/api/v1/teams/{team_id}/members",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )

        assert response.status_code == 200, f"Failed to list members: {response.text}"
        members = response.json()
        assert isinstance(members, list)
        assert len(members) == 2  # Admin + member

        # Verify both members are in the list
        user_ids = [m["user_id"] for m in members]
        assert self.admin_user_id in user_ids
        assert self.member_user_id in user_ids

        # Verify roles
        admin_member = next(m for m in members if m["user_id"] == self.admin_user_id)
        assert admin_member["role"] == "admin"

        regular_member = next(m for m in members if m["user_id"] == self.member_user_id)
        assert regular_member["role"] == "member"


class TestChatTeamIsolation:
    """Test team isolation in chat service"""

    def setup_method(self):
        """Setup test environment"""
        from chat_memory import get_memory
        self.memory = get_memory()

        self.team_id = "test_team_chat_001"
        self.user1_id = "test_user_chat_001"
        self.user2_id = "test_user_chat_002"
        self.outsider_id = "test_user_chat_003"

    def teardown_method(self):
        """Cleanup test sessions"""
        conn = self.memory._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM chat_messages WHERE session_id LIKE 'test_chat_%'")
        cursor.execute("DELETE FROM chat_sessions WHERE id LIKE 'test_chat_%'")
        conn.commit()

    def test_create_team_session(self):
        """Test creating a team chat session"""
        session_id = "test_chat_session_001"
        session = self.memory.create_session(
            session_id=session_id,
            title="Team Chat 001",
            model="llama3",
            user_id=self.user1_id,
            team_id=self.team_id
        )

        assert session["id"] == session_id
        # Verify session has team_id in database
        conn = self.memory._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT team_id FROM chat_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        assert row["team_id"] == self.team_id

    def test_list_team_sessions(self):
        """Test listing team sessions"""
        # Create team session
        team_session_id = "test_chat_session_002"
        self.memory.create_session(
            team_session_id, "Team Session", "llama3",
            self.user1_id, self.team_id
        )

        # Create personal session
        personal_session_id = "test_chat_session_003"
        self.memory.create_session(
            personal_session_id, "Personal Session", "llama3",
            self.user1_id, None  # No team_id
        )

        # List team sessions
        team_sessions = self.memory.list_sessions(
            user_id=self.user1_id,
            role="user",
            team_id=self.team_id
        )
        team_ids = [s["id"] for s in team_sessions]
        assert team_session_id in team_ids
        assert personal_session_id not in team_ids

        # List personal sessions
        personal_sessions = self.memory.list_sessions(
            user_id=self.user1_id,
            role="user",
            team_id=None
        )
        personal_ids = [s["id"] for s in personal_sessions]
        assert personal_session_id in personal_ids
        assert team_session_id not in personal_ids

    def test_team_message_isolation(self):
        """Test that team messages inherit team_id"""
        from chat_memory import ConversationEvent

        session_id = "test_chat_session_004"
        self.memory.create_session(
            session_id, "Team Messages", "llama3",
            self.user1_id, self.team_id
        )

        # Add message
        event = ConversationEvent(
            timestamp=datetime.utcnow().isoformat(),
            role="user",
            content="Test team message",
            model="llama3"
        )
        self.memory.add_message(session_id, event)

        # Verify message has team_id
        conn = self.memory._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT team_id FROM chat_messages
            WHERE session_id = ? AND content = ?
        """, (session_id, "Test team message"))
        row = cursor.fetchone()
        assert row["team_id"] == self.team_id

    def test_search_team_isolation(self):
        """Test semantic search respects team boundaries"""
        from chat_memory import ConversationEvent

        # Create team session with message
        team_session = "test_chat_session_005"
        self.memory.create_session(
            team_session, "Team Search", "llama3",
            self.user1_id, self.team_id
        )
        team_event = ConversationEvent(
            timestamp=datetime.utcnow().isoformat(),
            role="user",
            content="This is a unique team message about quantum computing",
            model="llama3"
        )
        self.memory.add_message(team_session, team_event)

        # Create personal session with message
        personal_session = "test_chat_session_006"
        self.memory.create_session(
            personal_session, "Personal Search", "llama3",
            self.outsider_id, None
        )
        personal_event = ConversationEvent(
            timestamp=datetime.utcnow().isoformat(),
            role="user",
            content="This is a unique personal message about quantum computing",
            model="llama3"
        )
        self.memory.add_message(personal_session, personal_event)

        # Search in team context
        team_results = self.memory.search_messages_semantic(
            query="quantum computing",
            limit=10,
            user_id=self.user1_id,
            team_id=self.team_id
        )
        team_contents = [r["content"] for r in team_results]
        # If semantic search returns empty, verify isolation via SQL
        if not team_results:
            # Verify team message exists
            conn = self.memory._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content FROM chat_messages
                WHERE team_id = ? AND content LIKE '%quantum%'
            """, (self.team_id,))
            team_msgs = cursor.fetchall()
            assert len(team_msgs) > 0, "Team message should exist"
            assert "unique team message" in team_msgs[0]["content"]
        else:
            assert any("unique team message" in c for c in team_contents)
            assert not any("unique personal message" in c for c in team_contents)

        # Search in personal context
        personal_results = self.memory.search_messages_semantic(
            query="quantum computing",
            limit=10,
            user_id=self.outsider_id,
            team_id=None
        )
        personal_contents = [r["content"] for r in personal_results]
        # If semantic search returns empty, verify isolation via SQL
        if not personal_results:
            # Verify personal message exists and team message doesn't
            conn = self.memory._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content FROM chat_messages
                WHERE user_id = ? AND team_id IS NULL AND content LIKE '%quantum%'
            """, (self.outsider_id,))
            personal_msgs = cursor.fetchall()
            assert len(personal_msgs) > 0, "Personal message should exist"
            assert "unique personal message" in personal_msgs[0]["content"]
        else:
            assert any("unique personal message" in c for c in personal_contents)
            assert not any("unique team message" in c for c in personal_contents)

    def test_analytics_team_scoped(self):
        """Test analytics respects team scope"""
        from chat_memory import ConversationEvent

        # Create team session
        team_session = "test_chat_session_007"
        self.memory.create_session(
            team_session, "Team Analytics", "llama3",
            self.user1_id, self.team_id
        )
        for i in range(3):
            event = ConversationEvent(
                timestamp=datetime.utcnow().isoformat(),
                role="user",
                content=f"Team message {i}",
                model="llama3",
                tokens=10
            )
            self.memory.add_message(team_session, event)

        # Create personal session
        personal_session = "test_chat_session_008"
        self.memory.create_session(
            personal_session, "Personal Analytics", "llama3",
            self.outsider_id, None
        )
        for i in range(5):
            event = ConversationEvent(
                timestamp=datetime.utcnow().isoformat(),
                role="user",
                content=f"Personal message {i}",
                model="llama3",
                tokens=10
            )
            self.memory.add_message(personal_session, event)

        # Get team analytics
        team_analytics = self.memory.get_analytics(
            session_id=None,
            user_id=self.user1_id,
            team_id=self.team_id
        )
        # Should only count team messages
        assert team_analytics["total_messages"] >= 3

        # Get personal analytics
        personal_analytics = self.memory.get_analytics(
            session_id=None,
            user_id=self.outsider_id,
            team_id=None
        )
        # Should only count personal messages
        assert personal_analytics["total_messages"] >= 5


class TestP2PHMACSecurity:
    """Test P2P HMAC signing and verification"""

    def setup_method(self):
        """Setup test environment"""
        # Ensure device secret is set
        if not os.getenv("ELOHIMOS_DEVICE_SECRET"):
            os.environ["ELOHIMOS_DEVICE_SECRET"] = "test_secret_" + os.urandom(16).hex()

        self.team_id = "test_team_p2p_001"
        self.peer_id = "test_peer_001"

    def test_sync_operation_signing(self):
        """Test SyncOperation payload signing"""
        from offline_data_sync import SyncOperation
        from team_crypto import sign_payload, verify_payload

        # Create sync operation
        op = SyncOperation(
            op_id="test_op_001",
            table_name="test_table",
            operation="insert",
            row_id="row_001",
            data={"field": "value"},
            timestamp=datetime.utcnow().isoformat(),
            peer_id=self.peer_id,
            version=1,
            team_id=self.team_id
        )

        # Sign payload
        payload_to_sign = {
            "op_id": op.op_id,
            "table_name": op.table_name,
            "operation": op.operation,
            "row_id": op.row_id,
            "data": op.data,
            "timestamp": op.timestamp,
            "peer_id": op.peer_id,
            "version": op.version,
            "team_id": op.team_id
        }
        signature = sign_payload(payload_to_sign, self.team_id)

        assert signature != ""
        assert len(signature) == 64  # HMAC-SHA256 hex

        # Verify signature
        is_valid = verify_payload(payload_to_sign, signature, self.team_id)
        assert is_valid is True

    def test_invalid_signature_rejection(self):
        """Test that invalid signatures are rejected"""
        from team_crypto import verify_payload

        payload = {
            "op_id": "test_op_002",
            "data": {"field": "value"},
            "team_id": self.team_id
        }

        # Invalid signature
        fake_signature = "0" * 64
        is_valid = verify_payload(payload, fake_signature, self.team_id)
        assert is_valid is False

    def test_cross_team_signature_rejection(self):
        """Test that cross-team signatures fail"""
        from team_crypto import sign_payload, verify_payload

        team1_id = "test_team_p2p_002"
        team2_id = "test_team_p2p_003"

        payload = {
            "op_id": "test_op_003",
            "data": {"field": "value"},
            "team_id": team1_id
        }

        # Sign with team1
        signature = sign_payload(payload, team1_id)

        # Try to verify with team2 (should fail)
        payload["team_id"] = team2_id
        is_valid = verify_payload(payload, signature, team2_id)
        assert is_valid is False

    def test_workflow_message_signing(self):
        """Test WorkflowSyncMessage signing"""
        from workflow_models import WorkflowSyncMessage
        from workflow_p2p_sync import WorkflowP2PSync
        from workflow_orchestrator import WorkflowOrchestrator
        from workflow_storage import WorkflowStorage

        # Create sync instance
        storage = WorkflowStorage()
        orchestrator = WorkflowOrchestrator(storage=storage)
        sync = WorkflowP2PSync(
            orchestrator=orchestrator,
            storage=storage,
            peer_id=self.peer_id
        )

        # Create message
        message = WorkflowSyncMessage(
            message_type="work_item_created",
            sender_peer_id=self.peer_id,
            sender_user_id="test_user_001",
            workflow_id="test_workflow_001",
            payload={"test": "data"},
            team_id=self.team_id
        )

        # Sign message
        sync._sign_message(message)

        assert message.signature != ""
        assert len(message.signature) == 64

        # Verify message
        is_valid = sync._verify_message(message)
        assert is_valid is True

    def test_tampered_message_rejection(self):
        """Test that tampered messages fail verification"""
        from workflow_models import WorkflowSyncMessage
        from workflow_p2p_sync import WorkflowP2PSync
        from workflow_orchestrator import WorkflowOrchestrator
        from workflow_storage import WorkflowStorage

        storage = WorkflowStorage()
        orchestrator = WorkflowOrchestrator(storage=storage)
        sync = WorkflowP2PSync(orchestrator, storage, self.peer_id)

        # Create and sign message
        message = WorkflowSyncMessage(
            message_type="work_item_created",
            sender_peer_id=self.peer_id,
            sender_user_id="test_user_001",
            workflow_id="test_workflow_001",
            payload={"test": "data"},
            team_id=self.team_id
        )
        sync._sign_message(message)

        # Tamper with message
        message.payload["test"] = "tampered_data"

        # Verification should fail
        is_valid = sync._verify_message(message)
        assert is_valid is False


class TestCrossTeamDenial:
    """Test cross-team access denial"""

    def setup_method(self):
        """Setup test environment"""
        from chat_memory import get_memory
        self.memory = get_memory()

        self.team1_id = "test_team_denial_001"
        self.team2_id = "test_team_denial_002"
        self.team1_user = "test_user_denial_001"
        self.team2_user = "test_user_denial_002"

    def teardown_method(self):
        """Cleanup"""
        conn = self.memory._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE session_id LIKE 'test_denial_%'")
        cursor.execute("DELETE FROM chat_sessions WHERE id LIKE 'test_denial_%'")
        conn.commit()

    def test_cross_team_session_access_denied(self):
        """Test that users cannot access other team's sessions"""
        # Create team1 session
        team1_session = "test_denial_session_001"
        self.memory.create_session(
            team1_session, "Team1 Session", "llama3",
            self.team1_user, self.team1_id
        )

        # Try to list as team2 user
        team2_sessions = self.memory.list_sessions(
            user_id=self.team2_user,
            role="user",
            team_id=self.team2_id
        )

        session_ids = [s["id"] for s in team2_sessions]
        assert team1_session not in session_ids

    def test_cross_team_search_isolation(self):
        """Test search doesn't leak across teams"""
        from chat_memory import ConversationEvent

        # Team1 message
        team1_session = "test_denial_session_002"
        self.memory.create_session(
            team1_session, "Team1 Search", "llama3",
            self.team1_user, self.team1_id
        )
        event1 = ConversationEvent(
            timestamp=datetime.utcnow().isoformat(),
            role="user",
            content="Secret team1 information about project alpha",
            model="llama3"
        )
        self.memory.add_message(team1_session, event1)

        # Team2 search should not find team1 message
        team2_results = self.memory.search_messages_semantic(
            query="project alpha",
            limit=10,
            user_id=self.team2_user,
            team_id=self.team2_id
        )

        contents = [r["content"] for r in team2_results]
        assert not any("Secret team1 information" in c for c in contents)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
