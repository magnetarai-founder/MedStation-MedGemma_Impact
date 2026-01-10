"""
Comprehensive tests for api/services/team/storage.py

Tests the team storage layer which handles all database operations
for teams, members, invites, promotions, and founder rights.

Coverage targets:
- Team CRUD: create, get, exists
- Team members: add, check, list, roles, updates
- Invite codes: create, check, get details, mark used, rate limiting
- Delayed promotions: create, check, get pending, mark executed
- Temporary promotions: create, check, get, update status
- Founder Rights: create, get, reactivate, revoke, list
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, UTC, timedelta
from unittest.mock import patch, MagicMock
import uuid


# ========== Fixtures ==========

@pytest.fixture
def temp_db():
    """Create temporary database with required schema"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create teams table
    cursor.execute("""
        CREATE TABLE teams (
            team_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL
        )
    """)

    # Create team_members table
    cursor.execute("""
        CREATE TABLE team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            job_role TEXT,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_seen TEXT,
            UNIQUE(team_id, user_id)
        )
    """)

    # Create invite_codes table
    cursor.execute("""
        CREATE TABLE invite_codes (
            code TEXT PRIMARY KEY,
            team_id TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            used INTEGER DEFAULT 0
        )
    """)

    # Create invite_attempts table
    cursor.execute("""
        CREATE TABLE invite_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invite_code TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            success INTEGER NOT NULL,
            attempt_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create delayed_promotions table
    cursor.execute("""
        CREATE TABLE delayed_promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            from_role TEXT NOT NULL,
            to_role TEXT NOT NULL,
            scheduled_at TEXT NOT NULL,
            execute_at TEXT NOT NULL,
            executed INTEGER DEFAULT 0,
            executed_at TEXT,
            reason TEXT
        )
    """)

    # Create temp_promotions table
    cursor.execute("""
        CREATE TABLE temp_promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            original_super_admin_id TEXT NOT NULL,
            promoted_admin_id TEXT NOT NULL,
            promoted_at TEXT NOT NULL,
            reverted_at TEXT,
            status TEXT DEFAULT 'active',
            reason TEXT,
            approved_by TEXT
        )
    """)

    # Create god_rights_auth table
    cursor.execute("""
        CREATE TABLE god_rights_auth (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            auth_key_hash TEXT,
            delegated_by TEXT,
            created_at TEXT NOT NULL,
            revoked_at TEXT,
            is_active INTEGER DEFAULT 1,
            notes TEXT
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.fixture
def mock_db_connection(temp_db):
    """Mock _get_app_conn to use temp database"""
    def _get_connection():
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        return conn

    # Patch all modules that have _get_app_conn (after P2 extraction)
    with patch('api.services.team.storage._get_app_conn', side_effect=_get_connection), \
         patch('api.services.team.promotions._get_app_conn', side_effect=_get_connection), \
         patch('api.services.team.god_rights._get_app_conn', side_effect=_get_connection):
        yield _get_connection


@pytest.fixture
def sample_team_id():
    """Generate sample team ID"""
    return f"team_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def sample_user_id():
    """Generate sample user ID"""
    return str(uuid.uuid4())


# ========== Team CRUD Tests ==========

class TestTeamCRUD:
    """Tests for team CRUD operations"""

    def test_create_team_record_success(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test creating a team record"""
        from api.services.team.storage import create_team_record

        result = create_team_record(
            team_id=sample_team_id,
            name="Test Team",
            creator_user_id=sample_user_id,
            description="A test team"
        )

        assert result is True

    def test_create_team_record_without_description(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test creating a team without description"""
        from api.services.team.storage import create_team_record

        result = create_team_record(
            team_id=sample_team_id,
            name="Test Team",
            creator_user_id=sample_user_id
        )

        assert result is True

    def test_create_team_record_duplicate_fails(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test creating duplicate team returns False"""
        from api.services.team.storage import create_team_record

        create_team_record(sample_team_id, "Team 1", sample_user_id)
        result = create_team_record(sample_team_id, "Team 2", sample_user_id)

        assert result is False

    def test_get_team_by_id_exists(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test getting an existing team"""
        from api.services.team.storage import create_team_record, get_team_by_id

        create_team_record(sample_team_id, "Test Team", sample_user_id, "Description")
        result = get_team_by_id(sample_team_id)

        assert result is not None
        assert result['team_id'] == sample_team_id
        assert result['name'] == "Test Team"
        assert result['description'] == "Description"
        assert result['created_by'] == sample_user_id

    def test_get_team_by_id_not_found(self, mock_db_connection):
        """Test getting non-existent team returns None"""
        from api.services.team.storage import get_team_by_id

        result = get_team_by_id("nonexistent-team")

        assert result is None

    def test_team_id_exists_true(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test team_id_exists returns True for existing team"""
        from api.services.team.storage import create_team_record, team_id_exists

        create_team_record(sample_team_id, "Test Team", sample_user_id)
        result = team_id_exists(sample_team_id)

        assert result is True

    def test_team_id_exists_false(self, mock_db_connection):
        """Test team_id_exists returns False for non-existent team"""
        from api.services.team.storage import team_id_exists

        result = team_id_exists("nonexistent-team")

        assert result is False


# ========== Team Member Tests ==========

class TestTeamMembers:
    """Tests for team member operations"""

    def test_add_member_record_success(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test adding a member to a team"""
        from api.services.team.storage import add_member_record

        result = add_member_record(sample_team_id, sample_user_id, "member")

        assert result is True

    def test_add_member_record_duplicate_fails(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test adding duplicate member returns False"""
        from api.services.team.storage import add_member_record

        add_member_record(sample_team_id, sample_user_id, "member")
        result = add_member_record(sample_team_id, sample_user_id, "admin")

        assert result is False

    def test_is_team_member_true(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test is_team_member returns True for existing member"""
        from api.services.team.storage import add_member_record, is_team_member

        add_member_record(sample_team_id, sample_user_id, "member")
        result = is_team_member(sample_team_id, sample_user_id)

        assert result is True

    def test_is_team_member_false(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test is_team_member returns False for non-member"""
        from api.services.team.storage import is_team_member

        result = is_team_member(sample_team_id, sample_user_id)

        assert result is False

    def test_get_team_members_list_empty(self, mock_db_connection, sample_team_id):
        """Test getting members when none exist"""
        from api.services.team.storage import get_team_members_list

        result = get_team_members_list(sample_team_id)

        assert result == []

    def test_get_team_members_list_with_members(self, mock_db_connection, sample_team_id):
        """Test getting list of team members"""
        from api.services.team.storage import add_member_record, get_team_members_list

        user1 = str(uuid.uuid4())
        user2 = str(uuid.uuid4())
        add_member_record(sample_team_id, user1, "admin")
        add_member_record(sample_team_id, user2, "member")

        result = get_team_members_list(sample_team_id)

        assert len(result) == 2
        assert all('user_id' in m for m in result)
        assert all('role' in m for m in result)
        assert all('joined_at' in m for m in result)

    def test_get_user_teams_list_empty(self, mock_db_connection, sample_user_id):
        """Test getting teams when user has none"""
        from api.services.team.storage import get_user_teams_list

        result = get_user_teams_list(sample_user_id)

        assert result == []

    def test_get_user_teams_list_with_teams(self, mock_db_connection, sample_user_id):
        """Test getting list of user's teams"""
        from api.services.team.storage import create_team_record, add_member_record, get_user_teams_list

        team1 = f"team_{uuid.uuid4().hex[:12]}"
        team2 = f"team_{uuid.uuid4().hex[:12]}"
        creator = str(uuid.uuid4())

        create_team_record(team1, "Team 1", creator)
        create_team_record(team2, "Team 2", creator)
        add_member_record(team1, sample_user_id, "admin")
        add_member_record(team2, sample_user_id, "member")

        result = get_user_teams_list(sample_user_id)

        assert len(result) == 2

    def test_get_member_role_exists(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test getting member's role"""
        from api.services.team.storage import add_member_record, get_member_role

        add_member_record(sample_team_id, sample_user_id, "admin")
        result = get_member_role(sample_team_id, sample_user_id)

        assert result == "admin"

    def test_get_member_role_not_found(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test getting role for non-member returns None"""
        from api.services.team.storage import get_member_role

        result = get_member_role(sample_team_id, sample_user_id)

        assert result is None

    def test_update_member_role_success(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test updating member's role"""
        from api.services.team.storage import add_member_record, update_member_role_db, get_member_role

        add_member_record(sample_team_id, sample_user_id, "member")
        result = update_member_role_db(sample_team_id, sample_user_id, "admin")

        assert result is True
        assert get_member_role(sample_team_id, sample_user_id) == "admin"

    def test_update_member_role_not_found(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test updating non-existent member returns False"""
        from api.services.team.storage import update_member_role_db

        result = update_member_role_db(sample_team_id, sample_user_id, "admin")

        assert result is False

    def test_update_last_seen_success(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test updating member's last_seen"""
        from api.services.team.storage import add_member_record, update_last_seen_db

        add_member_record(sample_team_id, sample_user_id, "member")
        now = datetime.now(UTC)
        result = update_last_seen_db(sample_team_id, sample_user_id, now)

        assert result is True

    def test_get_member_joined_at(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test getting member's join date"""
        from api.services.team.storage import add_member_record, get_member_joined_at

        add_member_record(sample_team_id, sample_user_id, "member")
        result = get_member_joined_at(sample_team_id, sample_user_id)

        assert result is not None

    def test_update_job_role_success(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test updating member's job role"""
        from api.services.team.storage import add_member_record, update_job_role_db, get_member_job_role_db

        add_member_record(sample_team_id, sample_user_id, "member")
        result = update_job_role_db(sample_team_id, sample_user_id, "Software Engineer")

        assert result is True
        assert get_member_job_role_db(sample_team_id, sample_user_id) == "Software Engineer"

    def test_count_members_by_role(self, mock_db_connection, sample_team_id):
        """Test counting members by role"""
        from api.services.team.storage import add_member_record, count_members_by_role

        add_member_record(sample_team_id, str(uuid.uuid4()), "admin")
        add_member_record(sample_team_id, str(uuid.uuid4()), "admin")
        add_member_record(sample_team_id, str(uuid.uuid4()), "member")

        assert count_members_by_role(sample_team_id, "admin") == 2
        assert count_members_by_role(sample_team_id, "member") == 1
        assert count_members_by_role(sample_team_id, "owner") == 0

    def test_count_team_members(self, mock_db_connection, sample_team_id):
        """Test counting total team members"""
        from api.services.team.storage import add_member_record, count_team_members

        assert count_team_members(sample_team_id) == 0

        add_member_record(sample_team_id, str(uuid.uuid4()), "member")
        add_member_record(sample_team_id, str(uuid.uuid4()), "member")
        add_member_record(sample_team_id, str(uuid.uuid4()), "admin")

        assert count_team_members(sample_team_id) == 3


# ========== Invite Code Tests ==========

class TestInviteCodes:
    """Tests for invite code operations"""

    def test_create_invite_code_success(self, mock_db_connection, sample_team_id):
        """Test creating an invite code"""
        from api.services.team.storage import create_invite_code_record

        code = "TESTCODE123"
        result = create_invite_code_record(code, sample_team_id)

        assert result is True

    def test_create_invite_code_with_expiry(self, mock_db_connection, sample_team_id):
        """Test creating an invite code with expiration"""
        from api.services.team.storage import create_invite_code_record

        code = "TESTCODE456"
        expires_at = datetime.now(UTC) + timedelta(days=7)
        result = create_invite_code_record(code, sample_team_id, expires_at)

        assert result is True

    def test_create_invite_code_duplicate_fails(self, mock_db_connection, sample_team_id):
        """Test creating duplicate invite code returns False"""
        from api.services.team.storage import create_invite_code_record

        code = "DUPLICATECODE"
        create_invite_code_record(code, sample_team_id)
        result = create_invite_code_record(code, sample_team_id)

        assert result is False

    def test_invite_code_exists_true(self, mock_db_connection, sample_team_id):
        """Test invite_code_exists returns True for existing code"""
        from api.services.team.storage import create_invite_code_record, invite_code_exists

        code = "EXISTINGCODE"
        create_invite_code_record(code, sample_team_id)
        result = invite_code_exists(code)

        assert result is True

    def test_invite_code_exists_false(self, mock_db_connection):
        """Test invite_code_exists returns False for non-existent code"""
        from api.services.team.storage import invite_code_exists

        result = invite_code_exists("NONEXISTENT")

        assert result is False

    def test_get_active_invite_code_found(self, mock_db_connection, sample_team_id):
        """Test getting active invite code"""
        from api.services.team.storage import create_invite_code_record, get_active_invite_code_record

        code = "ACTIVECODE"
        create_invite_code_record(code, sample_team_id)
        result = get_active_invite_code_record(sample_team_id)

        assert result == code

    def test_get_active_invite_code_none(self, mock_db_connection, sample_team_id):
        """Test getting active code when none exist"""
        from api.services.team.storage import get_active_invite_code_record

        result = get_active_invite_code_record(sample_team_id)

        assert result is None

    def test_get_invite_code_details(self, mock_db_connection, sample_team_id):
        """Test getting invite code details"""
        from api.services.team.storage import create_invite_code_record, get_invite_code_details

        code = "DETAILSCODE"
        create_invite_code_record(code, sample_team_id)
        result = get_invite_code_details(code)

        assert result is not None
        assert result['team_id'] == sample_team_id
        assert result['used'] == 0

    def test_get_invite_code_details_not_found(self, mock_db_connection):
        """Test getting details for non-existent code"""
        from api.services.team.storage import get_invite_code_details

        result = get_invite_code_details("NONEXISTENT")

        assert result is None

    def test_mark_invite_codes_used(self, mock_db_connection, sample_team_id):
        """Test marking invite codes as used"""
        from api.services.team.storage import create_invite_code_record, mark_invite_codes_used, get_active_invite_code_record

        create_invite_code_record("CODE1", sample_team_id)
        create_invite_code_record("CODE2", sample_team_id)

        result = mark_invite_codes_used(sample_team_id)

        assert result is True
        # No active codes should remain
        assert get_active_invite_code_record(sample_team_id) is None

    def test_record_invite_attempt_success(self, mock_db_connection):
        """Test recording invite attempt"""
        from api.services.team.storage import record_invite_attempt_db

        result = record_invite_attempt_db("TESTCODE", "192.168.1.1", True)

        assert result is True

    def test_record_invite_attempt_failed(self, mock_db_connection):
        """Test recording failed invite attempt"""
        from api.services.team.storage import record_invite_attempt_db

        result = record_invite_attempt_db("TESTCODE", "192.168.1.1", False)

        assert result is True

    def test_count_failed_invite_attempts_none(self, mock_db_connection):
        """Test counting failed attempts when none exist"""
        from api.services.team.storage import count_failed_invite_attempts

        result = count_failed_invite_attempts("TESTCODE", "192.168.1.1")

        assert result == 0

    def test_count_failed_invite_attempts_with_failures(self, mock_db_connection):
        """Test counting failed invite attempts"""
        from api.services.team.storage import record_invite_attempt_db, count_failed_invite_attempts

        record_invite_attempt_db("TESTCODE", "192.168.1.1", False)
        record_invite_attempt_db("TESTCODE", "192.168.1.1", False)
        record_invite_attempt_db("TESTCODE", "192.168.1.1", True)  # Success doesn't count

        result = count_failed_invite_attempts("TESTCODE", "192.168.1.1")

        assert result == 2


# ========== Delayed Promotions Tests ==========

class TestDelayedPromotions:
    """Tests for delayed promotions operations"""

    def test_check_existing_delayed_promotion_none(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test checking for non-existent delayed promotion"""
        from api.services.team.storage import check_existing_delayed_promotion

        result = check_existing_delayed_promotion(sample_team_id, sample_user_id)

        assert result is None

    def test_create_delayed_promotion_success(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test creating a delayed promotion"""
        from api.services.team.storage import create_delayed_promotion_record

        now = datetime.now(UTC).isoformat()
        execute_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()

        result = create_delayed_promotion_record(
            team_id=sample_team_id,
            user_id=sample_user_id,
            from_role="member",
            to_role="admin",
            execute_at=execute_at,
            scheduled_at=now,
            reason="Performance review"
        )

        assert result is True

    def test_check_existing_delayed_promotion_found(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test checking for existing delayed promotion"""
        from api.services.team.storage import create_delayed_promotion_record, check_existing_delayed_promotion

        now = datetime.now(UTC).isoformat()
        execute_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()

        create_delayed_promotion_record(
            sample_team_id, sample_user_id, "member", "admin", execute_at, now, "Reason"
        )

        result = check_existing_delayed_promotion(sample_team_id, sample_user_id)

        assert result is not None
        assert result['user_id'] == sample_user_id
        assert result['from_role'] == "member"
        assert result['to_role'] == "admin"

    def test_get_pending_delayed_promotions_empty(self, mock_db_connection, sample_team_id):
        """Test getting pending promotions when none exist"""
        from api.services.team.storage import get_pending_delayed_promotions

        result = get_pending_delayed_promotions(sample_team_id)

        assert result == []

    def test_mark_delayed_promotion_executed(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test marking delayed promotion as executed"""
        from api.services.team.storage import create_delayed_promotion_record, mark_delayed_promotion_executed

        now = datetime.now(UTC).isoformat()
        # Execute immediately
        execute_at = now

        create_delayed_promotion_record(
            sample_team_id, sample_user_id, "member", "admin", execute_at, now, "Reason"
        )

        result = mark_delayed_promotion_executed(1, now)

        assert result is True


# ========== Temporary Promotions Tests ==========

class TestTemporaryPromotions:
    """Tests for temporary promotions operations"""

    def test_get_most_senior_admin_none(self, mock_db_connection, sample_team_id):
        """Test getting most senior admin when none exist"""
        from api.services.team.storage import get_most_senior_admin

        result = get_most_senior_admin(sample_team_id)

        assert result is None

    def test_get_most_senior_admin_found(self, mock_db_connection, sample_team_id):
        """Test getting most senior admin (earliest joined_at)"""
        from api.services.team.storage import get_most_senior_admin, _get_app_conn

        admin1 = str(uuid.uuid4())
        admin2 = str(uuid.uuid4())

        # Directly insert with explicit timestamps to ensure ordering
        conn = _get_app_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO team_members (team_id, user_id, role, joined_at)
            VALUES (?, ?, 'admin', '2024-01-01T00:00:00')
        """, (sample_team_id, admin1))
        cursor.execute("""
            INSERT INTO team_members (team_id, user_id, role, joined_at)
            VALUES (?, ?, 'admin', '2024-01-02T00:00:00')
        """, (sample_team_id, admin2))
        conn.commit()
        conn.close()

        result = get_most_senior_admin(sample_team_id)

        assert result is not None
        # Should be admin1 (earlier joined_at)
        assert result['user_id'] == admin1

    def test_check_existing_temp_promotion_none(self, mock_db_connection, sample_team_id):
        """Test checking for non-existent temp promotion"""
        from api.services.team.storage import check_existing_temp_promotion

        result = check_existing_temp_promotion(sample_team_id)

        assert result is None

    def test_create_temp_promotion_success(self, mock_db_connection, sample_team_id):
        """Test creating a temporary promotion"""
        from api.services.team.storage import create_temp_promotion_record

        original_super_admin = str(uuid.uuid4())
        promoted_admin = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        result = create_temp_promotion_record(
            team_id=sample_team_id,
            original_super_admin_id=original_super_admin,
            promoted_admin_id=promoted_admin,
            promoted_at=now,
            reason="Vacation coverage"
        )

        assert result is True

    def test_check_existing_temp_promotion_found(self, mock_db_connection, sample_team_id):
        """Test checking for existing temp promotion"""
        from api.services.team.storage import create_temp_promotion_record, check_existing_temp_promotion

        original = str(uuid.uuid4())
        promoted = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        create_temp_promotion_record(sample_team_id, original, promoted, now, "Reason")

        result = check_existing_temp_promotion(sample_team_id)

        assert result is not None
        assert result['promoted_admin_id'] == promoted

    def test_get_active_temp_promotions_empty(self, mock_db_connection, sample_team_id):
        """Test getting active temp promotions when none exist"""
        from api.services.team.storage import get_active_temp_promotions

        result = get_active_temp_promotions(sample_team_id)

        assert result == []

    def test_get_active_temp_promotions_found(self, mock_db_connection, sample_team_id):
        """Test getting active temp promotions"""
        from api.services.team.storage import create_temp_promotion_record, get_active_temp_promotions

        original = str(uuid.uuid4())
        promoted = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        create_temp_promotion_record(sample_team_id, original, promoted, now, "Reason")

        result = get_active_temp_promotions(sample_team_id)

        assert len(result) == 1

    def test_get_temp_promotion_details(self, mock_db_connection, sample_team_id):
        """Test getting temp promotion details"""
        from api.services.team.storage import create_temp_promotion_record, get_temp_promotion_details

        original = str(uuid.uuid4())
        promoted = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        create_temp_promotion_record(sample_team_id, original, promoted, now, "Reason")

        result = get_temp_promotion_details(1)

        assert result is not None
        assert result['promoted_admin_id'] == promoted

    def test_update_temp_promotion_status(self, mock_db_connection, sample_team_id):
        """Test updating temp promotion status"""
        from api.services.team.storage import create_temp_promotion_record, update_temp_promotion_status

        original = str(uuid.uuid4())
        promoted = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        create_temp_promotion_record(sample_team_id, original, promoted, now, "Reason")

        result = update_temp_promotion_status(1, "approved", approved_by=original)

        assert result is True

    def test_update_temp_promotion_status_reverted(self, mock_db_connection, sample_team_id):
        """Test reverting temp promotion"""
        from api.services.team.storage import create_temp_promotion_record, update_temp_promotion_status

        original = str(uuid.uuid4())
        promoted = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        create_temp_promotion_record(sample_team_id, original, promoted, now, "Reason")

        result = update_temp_promotion_status(1, "reverted", reverted_at=now)

        assert result is True


# ========== Founder Rights (God Rights) Tests ==========

class TestFounderRights:
    """Tests for Founder Rights (God Rights) operations"""

    def test_get_god_rights_record_none(self, mock_db_connection, sample_user_id):
        """Test getting god rights record when none exist"""
        from api.services.team.storage import get_god_rights_record

        result = get_god_rights_record(sample_user_id)

        assert result is None

    def test_create_god_rights_success(self, mock_db_connection, sample_user_id):
        """Test creating god rights record"""
        from api.services.team.storage import create_god_rights_record

        now = datetime.now(UTC).isoformat()

        result = create_god_rights_record(
            user_id=sample_user_id,
            auth_key_hash="hash123",
            delegated_by=None,
            created_at=now,
            notes="Initial founder"
        )

        assert result is True

    def test_get_god_rights_record_found(self, mock_db_connection, sample_user_id):
        """Test getting existing god rights record"""
        from api.services.team.storage import create_god_rights_record, get_god_rights_record

        now = datetime.now(UTC).isoformat()
        create_god_rights_record(sample_user_id, "hash", None, now, "Notes")

        result = get_god_rights_record(sample_user_id)

        assert result is not None
        assert result['user_id'] == sample_user_id
        assert result['is_active'] is True

    def test_get_active_god_rights_record(self, mock_db_connection, sample_user_id):
        """Test getting active god rights record"""
        from api.services.team.storage import create_god_rights_record, get_active_god_rights_record

        now = datetime.now(UTC).isoformat()
        create_god_rights_record(sample_user_id, "hash", None, now, "Notes")

        result = get_active_god_rights_record(sample_user_id)

        assert result is not None
        assert result['user_id'] == sample_user_id

    def test_revoke_god_rights_success(self, mock_db_connection, sample_user_id):
        """Test revoking god rights"""
        from api.services.team.storage import create_god_rights_record, revoke_god_rights_record, get_god_rights_record

        now = datetime.now(UTC).isoformat()
        revoker = str(uuid.uuid4())

        create_god_rights_record(sample_user_id, "hash", None, now, "Notes")
        result = revoke_god_rights_record(sample_user_id, now, revoker)

        assert result is True

        record = get_god_rights_record(sample_user_id)
        assert record['is_active'] is False

    def test_reactivate_god_rights_success(self, mock_db_connection, sample_user_id):
        """Test reactivating god rights"""
        from api.services.team.storage import create_god_rights_record, revoke_god_rights_record, reactivate_god_rights_record, get_god_rights_record

        now = datetime.now(UTC).isoformat()
        revoker = str(uuid.uuid4())

        create_god_rights_record(sample_user_id, "hash", None, now, "Notes")
        revoke_god_rights_record(sample_user_id, now, revoker)
        result = reactivate_god_rights_record(sample_user_id, now)

        assert result is True

        record = get_god_rights_record(sample_user_id)
        assert record['is_active'] is True

    def test_get_all_god_rights_users_active_only(self, mock_db_connection):
        """Test getting all active god rights users"""
        from api.services.team.storage import create_god_rights_record, revoke_god_rights_record, get_all_god_rights_users

        user1 = str(uuid.uuid4())
        user2 = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        create_god_rights_record(user1, "hash1", None, now, "User 1")
        create_god_rights_record(user2, "hash2", None, now, "User 2")
        revoke_god_rights_record(user2, now, user1)

        result = get_all_god_rights_users(active_only=True)

        assert len(result) == 1
        assert result[0]['user_id'] == user1

    def test_get_all_god_rights_users_include_revoked(self, mock_db_connection):
        """Test getting all god rights users including revoked"""
        from api.services.team.storage import create_god_rights_record, revoke_god_rights_record, get_all_god_rights_users

        user1 = str(uuid.uuid4())
        user2 = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        create_god_rights_record(user1, "hash1", None, now, "User 1")
        create_god_rights_record(user2, "hash2", None, now, "User 2")
        revoke_god_rights_record(user2, now, user1)

        result = get_all_god_rights_users(active_only=False)

        assert len(result) == 2

    def test_get_revoked_god_rights_users(self, mock_db_connection):
        """Test getting revoked god rights users"""
        from api.services.team.storage import create_god_rights_record, revoke_god_rights_record, get_revoked_god_rights_users

        user1 = str(uuid.uuid4())
        user2 = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        create_god_rights_record(user1, "hash1", None, now, "User 1")
        create_god_rights_record(user2, "hash2", None, now, "User 2")
        revoke_god_rights_record(user2, now, user1)

        result = get_revoked_god_rights_users()

        assert len(result) == 1
        assert result[0]['user_id'] == user2


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    def test_full_team_lifecycle(self, mock_db_connection):
        """Test complete team lifecycle"""
        from api.services.team.storage import (
            create_team_record, get_team_by_id, team_id_exists,
            add_member_record, get_team_members_list, count_team_members
        )

        team_id = f"team_{uuid.uuid4().hex[:12]}"
        creator = str(uuid.uuid4())
        member1 = str(uuid.uuid4())
        member2 = str(uuid.uuid4())

        # Create team
        assert create_team_record(team_id, "Test Team", creator) is True
        assert team_id_exists(team_id) is True

        # Add members
        assert add_member_record(team_id, creator, "super_admin") is True
        assert add_member_record(team_id, member1, "admin") is True
        assert add_member_record(team_id, member2, "member") is True

        # Verify
        assert count_team_members(team_id) == 3
        team = get_team_by_id(team_id)
        assert team['name'] == "Test Team"

    def test_invite_code_flow(self, mock_db_connection, sample_team_id):
        """Test complete invite code flow"""
        from api.services.team.storage import (
            create_invite_code_record, invite_code_exists,
            get_invite_code_details, get_active_invite_code_record,
            record_invite_attempt_db, count_failed_invite_attempts,
            mark_invite_codes_used
        )

        code = "INVITE123"

        # Create code
        assert create_invite_code_record(code, sample_team_id) is True
        assert invite_code_exists(code) is True

        # Check details
        details = get_invite_code_details(code)
        assert details['team_id'] == sample_team_id

        # Active code
        assert get_active_invite_code_record(sample_team_id) == code

        # Record attempts
        assert record_invite_attempt_db(code, "192.168.1.1", False) is True
        assert count_failed_invite_attempts(code, "192.168.1.1") == 1

        # Mark used
        assert mark_invite_codes_used(sample_team_id) is True
        assert get_active_invite_code_record(sample_team_id) is None


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_team_name(self, mock_db_connection, sample_user_id):
        """Test creating team with unicode name"""
        from api.services.team.storage import create_team_record, get_team_by_id

        team_id = f"team_{uuid.uuid4().hex[:12]}"
        result = create_team_record(team_id, "チーム 🚀", sample_user_id, "日本語の説明")

        assert result is True
        team = get_team_by_id(team_id)
        assert team['name'] == "チーム 🚀"

    def test_special_characters_in_notes(self, mock_db_connection, sample_user_id):
        """Test god rights notes with special characters"""
        from api.services.team.storage import create_god_rights_record, get_god_rights_record

        now = datetime.now(UTC).isoformat()
        notes = "Special chars: <script>'\"&\n\t"

        result = create_god_rights_record(sample_user_id, "hash", None, now, notes)

        assert result is True
        record = get_god_rights_record(sample_user_id)
        assert record['notes'] == notes

    def test_long_reason_text(self, mock_db_connection, sample_team_id, sample_user_id):
        """Test delayed promotion with long reason"""
        from api.services.team.storage import create_delayed_promotion_record, check_existing_delayed_promotion

        now = datetime.now(UTC).isoformat()
        execute_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        long_reason = "x" * 10000

        result = create_delayed_promotion_record(
            sample_team_id, sample_user_id, "member", "admin", execute_at, now, long_reason
        )

        assert result is True
        promotion = check_existing_delayed_promotion(sample_team_id, sample_user_id)
        assert len(promotion['reason']) == 10000
