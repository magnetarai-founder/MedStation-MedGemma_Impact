"""
Comprehensive tests for api/permissions/admin.py

Tests permission administration functionality including permission registry,
profiles, permission sets, user assignments, and cache invalidation.

Coverage targets:
- Permission registry: get_all_permissions with category filtering
- Permission profiles: CRUD, grants management, user assignment
- Permission sets: CRUD, grants management, user assignment with expiry
- User assignments: profile and set assignment/unassignment
- Cache invalidation: forced permission cache reload
"""

import pytest
import sqlite3
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock, AsyncMock
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

    # Create permissions table
    cursor.execute("""
        CREATE TABLE permissions (
            permission_id TEXT PRIMARY KEY,
            permission_key TEXT UNIQUE NOT NULL,
            permission_name TEXT NOT NULL,
            permission_description TEXT,
            category TEXT NOT NULL,
            subcategory TEXT,
            permission_type TEXT NOT NULL DEFAULT 'boolean',
            is_system INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # Create permission_profiles table
    cursor.execute("""
        CREATE TABLE permission_profiles (
            profile_id TEXT PRIMARY KEY,
            profile_name TEXT NOT NULL,
            profile_description TEXT,
            team_id TEXT,
            applies_to_role TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """)

    # Create profile_permissions table
    cursor.execute("""
        CREATE TABLE profile_permissions (
            profile_id TEXT NOT NULL,
            permission_id TEXT NOT NULL,
            is_granted INTEGER DEFAULT 1,
            permission_level TEXT,
            permission_scope TEXT,
            PRIMARY KEY (profile_id, permission_id)
        )
    """)

    # Create user_permission_profiles table
    cursor.execute("""
        CREATE TABLE user_permission_profiles (
            user_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            assigned_by TEXT NOT NULL,
            assigned_at TEXT NOT NULL,
            PRIMARY KEY (user_id, profile_id)
        )
    """)

    # Create users table
    cursor.execute("""
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # Create permission_sets table
    cursor.execute("""
        CREATE TABLE permission_sets (
            permission_set_id TEXT PRIMARY KEY,
            set_name TEXT NOT NULL,
            set_description TEXT,
            team_id TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """)

    # Create permission_set_permissions table
    cursor.execute("""
        CREATE TABLE permission_set_permissions (
            permission_set_id TEXT NOT NULL,
            permission_id TEXT NOT NULL,
            is_granted INTEGER DEFAULT 1,
            permission_level TEXT,
            permission_scope TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (permission_set_id, permission_id)
        )
    """)

    # Create user_permission_sets table
    cursor.execute("""
        CREATE TABLE user_permission_sets (
            user_id TEXT NOT NULL,
            permission_set_id TEXT NOT NULL,
            assigned_by TEXT NOT NULL,
            assigned_at TEXT NOT NULL,
            expires_at TEXT,
            PRIMARY KEY (user_id, permission_set_id)
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.fixture
def mock_db_connection(temp_db):
    """Mock get_db_connection to use temp database"""
    def _get_connection():
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        return conn

    with patch('api.permissions.admin.get_db_connection', side_effect=_get_connection):
        yield _get_connection


@pytest.fixture
def mock_audit_log():
    """Mock audit_log_sync function"""
    mock_audit = MagicMock()
    mock_action = MagicMock()

    with patch.dict('sys.modules', {
        'audit_logger': MagicMock(
            audit_log_sync=mock_audit,
            AuditAction=mock_action
        )
    }):
        yield mock_audit


@pytest.fixture
def mock_permission_engine():
    """Mock permission engine"""
    mock_engine = MagicMock()
    mock_engine.invalidate_user_permissions = MagicMock()

    with patch.dict('sys.modules', {
        'permission_engine': MagicMock(
            get_permission_engine=MagicMock(return_value=mock_engine)
        )
    }):
        yield mock_engine


@pytest.fixture
def sample_user_id():
    """Generate sample user ID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_permission_id():
    """Generate sample permission ID"""
    return f"perm_{uuid.uuid4().hex[:12]}"


# ========== Helper Functions ==========

def insert_permission(conn, permission_id, permission_key, category="feature"):
    """Insert a test permission"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO permissions (
            permission_id, permission_key, permission_name,
            permission_description, category, subcategory,
            permission_type, is_system, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        permission_id, permission_key, f"Name for {permission_key}",
        f"Description for {permission_key}", category, "general",
        "boolean", 0, datetime.now(UTC).isoformat()
    ))
    conn.commit()


def insert_user(conn, user_id, username):
    """Insert a test user"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, username, email, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, f"{username}@test.com", datetime.now(UTC).isoformat()))
    conn.commit()


def insert_profile(conn, profile_id, profile_name, created_by):
    """Insert a test profile"""
    cursor = conn.cursor()
    now = datetime.now(UTC).isoformat()
    cursor.execute("""
        INSERT INTO permission_profiles (
            profile_id, profile_name, profile_description, team_id,
            applies_to_role, created_by, created_at, modified_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (profile_id, profile_name, "Test description", None, None, created_by, now, now, 1))
    conn.commit()


def insert_permission_set(conn, set_id, set_name, created_by):
    """Insert a test permission set"""
    cursor = conn.cursor()
    now = datetime.now(UTC).isoformat()
    cursor.execute("""
        INSERT INTO permission_sets (
            permission_set_id, set_name, set_description, team_id,
            created_by, created_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (set_id, set_name, "Test description", None, created_by, now, 1))
    conn.commit()


# ========== Permission Registry Tests ==========

class TestGetAllPermissions:
    """Tests for get_all_permissions function"""

    @pytest.mark.asyncio
    async def test_get_all_permissions_empty(self, mock_db_connection):
        """Test getting permissions when none exist"""
        from api.permissions.admin import get_all_permissions

        result = await get_all_permissions()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_permissions_returns_all(self, mock_db_connection):
        """Test getting all permissions"""
        from api.permissions.admin import get_all_permissions

        conn = mock_db_connection()
        insert_permission(conn, "perm1", "feature.read", "feature")
        insert_permission(conn, "perm2", "feature.write", "feature")
        insert_permission(conn, "perm3", "system.admin", "system")
        conn.close()

        result = await get_all_permissions()

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_all_permissions_filter_by_category(self, mock_db_connection):
        """Test filtering permissions by category"""
        from api.permissions.admin import get_all_permissions

        conn = mock_db_connection()
        insert_permission(conn, "perm1", "feature.read", "feature")
        insert_permission(conn, "perm2", "feature.write", "feature")
        insert_permission(conn, "perm3", "system.admin", "system")
        conn.close()

        result = await get_all_permissions(category="feature")

        assert len(result) == 2
        assert all(p["category"] == "feature" for p in result)

    @pytest.mark.asyncio
    async def test_get_all_permissions_fields(self, mock_db_connection):
        """Test that permissions have all expected fields"""
        from api.permissions.admin import get_all_permissions

        conn = mock_db_connection()
        insert_permission(conn, "perm1", "test.permission", "feature")
        conn.close()

        result = await get_all_permissions()

        assert len(result) == 1
        perm = result[0]
        assert "permission_id" in perm
        assert "permission_key" in perm
        assert "permission_name" in perm
        assert "permission_description" in perm
        assert "category" in perm
        assert "subcategory" in perm
        assert "permission_type" in perm
        assert "is_system" in perm
        assert "created_at" in perm


# ========== Permission Profile Tests ==========

class TestCreateProfile:
    """Tests for create_profile function"""

    @pytest.mark.asyncio
    async def test_create_profile_success(self, mock_db_connection, sample_user_id):
        """Test creating a permission profile"""
        from api.permissions.admin import create_profile

        result = await create_profile(
            profile_name="Test Profile",
            profile_description="A test profile",
            team_id=None,
            applies_to_role=None,
            created_by=sample_user_id
        )

        assert "profile_id" in result
        assert result["profile_name"] == "Test Profile"
        assert result["profile_description"] == "A test profile"
        assert result["created_by"] == sample_user_id
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_profile_with_team(self, mock_db_connection, sample_user_id):
        """Test creating a profile with team ID"""
        from api.permissions.admin import create_profile

        team_id = str(uuid.uuid4())
        result = await create_profile(
            profile_name="Team Profile",
            profile_description="A team profile",
            team_id=team_id,
            applies_to_role="editor",
            created_by=sample_user_id
        )

        assert result["team_id"] == team_id
        assert result["applies_to_role"] == "editor"

    @pytest.mark.asyncio
    async def test_create_profile_generates_unique_id(self, mock_db_connection, sample_user_id):
        """Test that each profile gets a unique ID"""
        from api.permissions.admin import create_profile

        result1 = await create_profile("Profile 1", None, None, None, sample_user_id)
        result2 = await create_profile("Profile 2", None, None, None, sample_user_id)

        assert result1["profile_id"] != result2["profile_id"]
        assert result1["profile_id"].startswith("profile_")


class TestGetProfile:
    """Tests for get_profile function"""

    @pytest.mark.asyncio
    async def test_get_profile_success(self, mock_db_connection, sample_user_id):
        """Test getting an existing profile"""
        from api.permissions.admin import create_profile, get_profile

        created = await create_profile("Test Profile", "Description", None, None, sample_user_id)
        result = await get_profile(created["profile_id"])

        assert result["profile_id"] == created["profile_id"]
        assert result["profile_name"] == "Test Profile"

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, mock_db_connection):
        """Test getting a non-existent profile raises HTTPException"""
        from api.permissions.admin import get_profile
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_profile("nonexistent-profile-id")

        assert exc_info.value.status_code == 404
        assert "Profile not found" in str(exc_info.value.detail)


class TestUpdateProfile:
    """Tests for update_profile function"""

    @pytest.mark.asyncio
    async def test_update_profile_name(self, mock_db_connection, sample_user_id):
        """Test updating profile name"""
        from api.permissions.admin import create_profile, update_profile

        created = await create_profile("Original Name", None, None, None, sample_user_id)
        result = await update_profile(
            created["profile_id"],
            {"profile_name": "Updated Name"},
            sample_user_id
        )

        assert result["profile_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_profile_is_active(self, mock_db_connection, sample_user_id):
        """Test deactivating a profile"""
        from api.permissions.admin import create_profile, update_profile

        created = await create_profile("Test Profile", None, None, None, sample_user_id)
        result = await update_profile(
            created["profile_id"],
            {"is_active": False},
            sample_user_id
        )

        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_profile_not_found(self, mock_db_connection, sample_user_id):
        """Test updating non-existent profile raises HTTPException"""
        from api.permissions.admin import update_profile
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await update_profile("nonexistent", {"profile_name": "New"}, sample_user_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_profile_no_fields(self, mock_db_connection, sample_user_id):
        """Test updating with no fields raises HTTPException"""
        from api.permissions.admin import create_profile, update_profile
        from fastapi import HTTPException

        created = await create_profile("Test", None, None, None, sample_user_id)

        with pytest.raises(HTTPException) as exc_info:
            await update_profile(created["profile_id"], {}, sample_user_id)

        assert exc_info.value.status_code == 400
        assert "No fields to update" in str(exc_info.value.detail)


class TestGetAllProfiles:
    """Tests for get_all_profiles function"""

    @pytest.mark.asyncio
    async def test_get_all_profiles_empty(self, mock_db_connection):
        """Test getting profiles when none exist"""
        from api.permissions.admin import get_all_profiles

        result = await get_all_profiles()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_profiles_returns_all(self, mock_db_connection, sample_user_id):
        """Test getting all profiles"""
        from api.permissions.admin import create_profile, get_all_profiles

        await create_profile("Profile 1", None, None, None, sample_user_id)
        await create_profile("Profile 2", None, None, None, sample_user_id)
        await create_profile("Profile 3", None, None, None, sample_user_id)

        result = await get_all_profiles()

        assert len(result) == 3


class TestProfileGrants:
    """Tests for profile grants functions"""

    @pytest.mark.asyncio
    async def test_update_profile_grants(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test updating profile grants"""
        from api.permissions.admin import create_profile, update_profile_grants

        # Create profile and permission
        created = await create_profile("Test", None, None, None, sample_user_id)

        conn = mock_db_connection()
        insert_permission(conn, "perm1", "test.permission", "feature")
        conn.close()

        grants = [{"permission_id": "perm1", "is_granted": True, "permission_level": "WRITE"}]

        result = await update_profile_grants(created["profile_id"], grants, sample_user_id)

        assert result["status"] == "success"
        assert result["grants_updated"] == 1

    @pytest.mark.asyncio
    async def test_update_profile_grants_not_found(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test updating grants for non-existent profile"""
        from api.permissions.admin import update_profile_grants
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await update_profile_grants("nonexistent", [], sample_user_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_profile_grants_empty(self, mock_db_connection, sample_user_id):
        """Test getting grants when none exist"""
        from api.permissions.admin import create_profile, get_profile_grants

        created = await create_profile("Test", None, None, None, sample_user_id)
        result = await get_profile_grants(created["profile_id"])

        assert result == []

    @pytest.mark.asyncio
    async def test_get_profile_grants_with_data(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test getting grants with data"""
        from api.permissions.admin import create_profile, update_profile_grants, get_profile_grants

        created = await create_profile("Test", None, None, None, sample_user_id)

        conn = mock_db_connection()
        insert_permission(conn, "perm1", "test.permission", "feature")
        conn.close()

        grants = [{"permission_id": "perm1", "is_granted": True}]
        await update_profile_grants(created["profile_id"], grants, sample_user_id)

        result = await get_profile_grants(created["profile_id"])

        assert len(result) == 1
        assert result[0]["permission_id"] == "perm1"
        assert result[0]["is_granted"] is True


# ========== User Assignment Tests ==========

class TestAssignProfileToUser:
    """Tests for assign_profile_to_user function"""

    @pytest.mark.asyncio
    async def test_assign_profile_success(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test assigning a profile to a user"""
        from api.permissions.admin import create_profile, assign_profile_to_user

        conn = mock_db_connection()
        target_user_id = str(uuid.uuid4())
        insert_user(conn, target_user_id, "testuser")
        conn.close()

        created = await create_profile("Test", None, None, None, sample_user_id)
        result = await assign_profile_to_user(
            created["profile_id"],
            target_user_id,
            sample_user_id
        )

        assert result["status"] == "success"
        assert result["user_id"] == target_user_id
        assert result["profile_id"] == created["profile_id"]

    @pytest.mark.asyncio
    async def test_assign_profile_profile_not_found(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test assigning non-existent profile raises HTTPException"""
        from api.permissions.admin import assign_profile_to_user
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await assign_profile_to_user("nonexistent", sample_user_id, sample_user_id)

        assert exc_info.value.status_code == 404
        assert "Profile not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_assign_profile_user_not_found(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test assigning to non-existent user raises HTTPException"""
        from api.permissions.admin import create_profile, assign_profile_to_user
        from fastapi import HTTPException

        created = await create_profile("Test", None, None, None, sample_user_id)

        with pytest.raises(HTTPException) as exc_info:
            await assign_profile_to_user(created["profile_id"], "nonexistent-user", sample_user_id)

        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)


class TestUnassignProfileFromUser:
    """Tests for unassign_profile_from_user function"""

    @pytest.mark.asyncio
    async def test_unassign_profile_success(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test unassigning a profile from a user"""
        from api.permissions.admin import create_profile, assign_profile_to_user, unassign_profile_from_user

        conn = mock_db_connection()
        target_user_id = str(uuid.uuid4())
        insert_user(conn, target_user_id, "testuser")
        conn.close()

        created = await create_profile("Test", None, None, None, sample_user_id)
        await assign_profile_to_user(created["profile_id"], target_user_id, sample_user_id)

        result = await unassign_profile_from_user(
            created["profile_id"],
            target_user_id,
            sample_user_id
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_unassign_profile_not_found(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test unassigning non-existent assignment raises HTTPException"""
        from api.permissions.admin import unassign_profile_from_user
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await unassign_profile_from_user("nonexistent", sample_user_id, sample_user_id)

        assert exc_info.value.status_code == 404
        assert "Assignment not found" in str(exc_info.value.detail)


class TestGetUserProfiles:
    """Tests for get_user_profiles function"""

    @pytest.mark.asyncio
    async def test_get_user_profiles_empty(self, mock_db_connection, sample_user_id):
        """Test getting profiles when user has none"""
        from api.permissions.admin import get_user_profiles

        result = await get_user_profiles(sample_user_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_profiles_with_assignments(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test getting user's assigned profiles"""
        from api.permissions.admin import create_profile, assign_profile_to_user, get_user_profiles

        conn = mock_db_connection()
        target_user_id = str(uuid.uuid4())
        insert_user(conn, target_user_id, "testuser")
        conn.close()

        profile1 = await create_profile("Profile 1", None, None, None, sample_user_id)
        profile2 = await create_profile("Profile 2", None, None, None, sample_user_id)

        await assign_profile_to_user(profile1["profile_id"], target_user_id, sample_user_id)
        await assign_profile_to_user(profile2["profile_id"], target_user_id, sample_user_id)

        result = await get_user_profiles(target_user_id)

        assert len(result) == 2


# ========== Permission Set Tests ==========

class TestCreatePermissionSet:
    """Tests for create_permission_set function"""

    @pytest.mark.asyncio
    async def test_create_permission_set_success(self, mock_db_connection, sample_user_id):
        """Test creating a permission set"""
        from api.permissions.admin import create_permission_set

        result = await create_permission_set(
            set_name="Test Set",
            set_description="A test permission set",
            team_id=None,
            created_by=sample_user_id
        )

        assert "permission_set_id" in result
        assert result["set_name"] == "Test Set"
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_permission_set_generates_unique_id(self, mock_db_connection, sample_user_id):
        """Test that each set gets a unique ID"""
        from api.permissions.admin import create_permission_set

        result1 = await create_permission_set("Set 1", None, None, sample_user_id)
        result2 = await create_permission_set("Set 2", None, None, sample_user_id)

        assert result1["permission_set_id"] != result2["permission_set_id"]
        assert result1["permission_set_id"].startswith("permset_")


class TestGetAllPermissionSets:
    """Tests for get_all_permission_sets function"""

    @pytest.mark.asyncio
    async def test_get_all_permission_sets_empty(self, mock_db_connection):
        """Test getting sets when none exist"""
        from api.permissions.admin import get_all_permission_sets

        result = await get_all_permission_sets()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_permission_sets_returns_all(self, mock_db_connection, sample_user_id):
        """Test getting all permission sets"""
        from api.permissions.admin import create_permission_set, get_all_permission_sets

        await create_permission_set("Set 1", None, None, sample_user_id)
        await create_permission_set("Set 2", None, None, sample_user_id)

        result = await get_all_permission_sets()

        assert len(result) == 2


class TestAssignPermissionSetToUser:
    """Tests for assign_permission_set_to_user function"""

    @pytest.mark.asyncio
    async def test_assign_set_success(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test assigning a set to a user"""
        from api.permissions.admin import create_permission_set, assign_permission_set_to_user

        conn = mock_db_connection()
        target_user_id = str(uuid.uuid4())
        insert_user(conn, target_user_id, "testuser")
        conn.close()

        created = await create_permission_set("Test", None, None, sample_user_id)
        result = await assign_permission_set_to_user(
            created["permission_set_id"],
            target_user_id,
            None,  # No expiry
            sample_user_id
        )

        assert result["status"] == "success"
        assert result["permission_set_id"] == created["permission_set_id"]

    @pytest.mark.asyncio
    async def test_assign_set_with_expiry(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test assigning a set with expiration"""
        from api.permissions.admin import create_permission_set, assign_permission_set_to_user

        conn = mock_db_connection()
        target_user_id = str(uuid.uuid4())
        insert_user(conn, target_user_id, "testuser")
        conn.close()

        created = await create_permission_set("Test", None, None, sample_user_id)
        expires_at = "2030-12-31T23:59:59Z"

        result = await assign_permission_set_to_user(
            created["permission_set_id"],
            target_user_id,
            expires_at,
            sample_user_id
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_assign_set_not_found(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test assigning non-existent set raises HTTPException"""
        from api.permissions.admin import assign_permission_set_to_user
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await assign_permission_set_to_user("nonexistent", sample_user_id, None, sample_user_id)

        assert exc_info.value.status_code == 404
        assert "Permission set not found" in str(exc_info.value.detail)


class TestUnassignPermissionSetFromUser:
    """Tests for unassign_permission_set_from_user function"""

    @pytest.mark.asyncio
    async def test_unassign_set_success(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test unassigning a set from a user"""
        from api.permissions.admin import create_permission_set, assign_permission_set_to_user, unassign_permission_set_from_user

        conn = mock_db_connection()
        target_user_id = str(uuid.uuid4())
        insert_user(conn, target_user_id, "testuser")
        conn.close()

        created = await create_permission_set("Test", None, None, sample_user_id)
        await assign_permission_set_to_user(created["permission_set_id"], target_user_id, None, sample_user_id)

        result = await unassign_permission_set_from_user(
            created["permission_set_id"],
            target_user_id,
            sample_user_id
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_unassign_set_not_found(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test unassigning non-existent assignment raises HTTPException"""
        from api.permissions.admin import unassign_permission_set_from_user
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await unassign_permission_set_from_user("nonexistent", sample_user_id, sample_user_id)

        assert exc_info.value.status_code == 404
        assert "Assignment not found" in str(exc_info.value.detail)


class TestPermissionSetGrants:
    """Tests for permission set grants functions"""

    @pytest.mark.asyncio
    async def test_update_set_grants(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test updating permission set grants"""
        from api.permissions.admin import create_permission_set, update_permission_set_grants

        created = await create_permission_set("Test", None, None, sample_user_id)

        conn = mock_db_connection()
        insert_permission(conn, "perm1", "test.permission", "feature")
        conn.close()

        grants = [{"permission_id": "perm1", "is_granted": True}]
        result = await update_permission_set_grants(created["permission_set_id"], grants, sample_user_id)

        assert result["status"] == "success"
        assert result["grants_updated"] == 1

    @pytest.mark.asyncio
    async def test_update_set_grants_not_found(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test updating grants for non-existent set"""
        from api.permissions.admin import update_permission_set_grants
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await update_permission_set_grants("nonexistent", [], sample_user_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_set_grants(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test getting permission set grants"""
        from api.permissions.admin import create_permission_set, update_permission_set_grants, get_permission_set_grants

        created = await create_permission_set("Test", None, None, sample_user_id)

        conn = mock_db_connection()
        insert_permission(conn, "perm1", "test.permission", "feature")
        conn.close()

        grants = [{"permission_id": "perm1", "is_granted": True}]
        await update_permission_set_grants(created["permission_set_id"], grants, sample_user_id)

        result = await get_permission_set_grants(created["permission_set_id"])

        assert "permission_set_id" in result
        assert len(result["grants"]) == 1

    @pytest.mark.asyncio
    async def test_get_set_grants_not_found(self, mock_db_connection):
        """Test getting grants for non-existent set"""
        from api.permissions.admin import get_permission_set_grants
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_permission_set_grants("nonexistent")

        assert exc_info.value.status_code == 404


class TestDeletePermissionSetGrant:
    """Tests for delete_permission_set_grant function"""

    @pytest.mark.asyncio
    async def test_delete_grant_success(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test deleting a permission set grant"""
        from api.permissions.admin import create_permission_set, update_permission_set_grants, delete_permission_set_grant

        created = await create_permission_set("Test", None, None, sample_user_id)

        conn = mock_db_connection()
        insert_permission(conn, "perm1", "test.permission", "feature")
        conn.close()

        grants = [{"permission_id": "perm1", "is_granted": True}]
        await update_permission_set_grants(created["permission_set_id"], grants, sample_user_id)

        result = await delete_permission_set_grant(
            created["permission_set_id"],
            "perm1",
            sample_user_id
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_delete_grant_not_found(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test deleting non-existent grant raises HTTPException"""
        from api.permissions.admin import delete_permission_set_grant
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await delete_permission_set_grant("nonexistent", "perm1", sample_user_id)

        assert exc_info.value.status_code == 404


# ========== Cache Invalidation Tests ==========

class TestInvalidateUserPermissions:
    """Tests for invalidate_user_permissions function"""

    @pytest.mark.asyncio
    async def test_invalidate_success(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test invalidating user permissions cache"""
        from api.permissions.admin import invalidate_user_permissions

        target_user_id = str(uuid.uuid4())
        result = await invalidate_user_permissions(target_user_id, sample_user_id)

        assert result["status"] == "success"
        assert result["user_id"] == target_user_id
        assert result["cache_invalidated"] is True


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    @pytest.mark.asyncio
    async def test_full_profile_lifecycle(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test complete profile lifecycle"""
        from api.permissions.admin import (
            create_profile, get_profile, update_profile,
            update_profile_grants, get_profile_grants,
            assign_profile_to_user, get_user_profiles,
            unassign_profile_from_user
        )

        # Create user
        conn = mock_db_connection()
        target_user_id = str(uuid.uuid4())
        insert_user(conn, target_user_id, "testuser")
        insert_permission(conn, "perm1", "test.permission", "feature")
        conn.close()

        # Create profile
        profile = await create_profile("Test Profile", "Description", None, None, sample_user_id)

        # Verify creation
        retrieved = await get_profile(profile["profile_id"])
        assert retrieved["profile_name"] == "Test Profile"

        # Update profile
        updated = await update_profile(profile["profile_id"], {"profile_name": "Updated"}, sample_user_id)
        assert updated["profile_name"] == "Updated"

        # Add grants
        await update_profile_grants(
            profile["profile_id"],
            [{"permission_id": "perm1", "is_granted": True}],
            sample_user_id
        )
        grants = await get_profile_grants(profile["profile_id"])
        assert len(grants) == 1

        # Assign to user
        await assign_profile_to_user(profile["profile_id"], target_user_id, sample_user_id)
        user_profiles = await get_user_profiles(target_user_id)
        assert len(user_profiles) == 1

        # Unassign from user
        await unassign_profile_from_user(profile["profile_id"], target_user_id, sample_user_id)
        user_profiles = await get_user_profiles(target_user_id)
        assert len(user_profiles) == 0

    @pytest.mark.asyncio
    async def test_full_permission_set_lifecycle(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test complete permission set lifecycle"""
        from api.permissions.admin import (
            create_permission_set, get_all_permission_sets,
            update_permission_set_grants, get_permission_set_grants,
            assign_permission_set_to_user, unassign_permission_set_from_user
        )

        # Create user and permission
        conn = mock_db_connection()
        target_user_id = str(uuid.uuid4())
        insert_user(conn, target_user_id, "testuser")
        insert_permission(conn, "perm1", "test.permission", "feature")
        conn.close()

        # Create permission set
        perm_set = await create_permission_set("Test Set", "Description", None, sample_user_id)

        # Verify creation
        all_sets = await get_all_permission_sets()
        assert len(all_sets) == 1

        # Add grants
        await update_permission_set_grants(
            perm_set["permission_set_id"],
            [{"permission_id": "perm1", "is_granted": True}],
            sample_user_id
        )
        grants = await get_permission_set_grants(perm_set["permission_set_id"])
        assert len(grants["grants"]) == 1

        # Assign to user
        await assign_permission_set_to_user(
            perm_set["permission_set_id"],
            target_user_id,
            None,
            sample_user_id
        )

        # Unassign from user
        await unassign_permission_set_from_user(
            perm_set["permission_set_id"],
            target_user_id,
            sample_user_id
        )


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.mark.asyncio
    async def test_profile_with_unicode_name(self, mock_db_connection, sample_user_id):
        """Test creating profile with unicode name"""
        from api.permissions.admin import create_profile, get_profile

        result = await create_profile(
            profile_name="日本語プロファイル 🎉",
            profile_description="説明文",
            team_id=None,
            applies_to_role=None,
            created_by=sample_user_id
        )

        retrieved = await get_profile(result["profile_id"])
        assert retrieved["profile_name"] == "日本語プロファイル 🎉"

    @pytest.mark.asyncio
    async def test_reassign_profile(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test reassigning a profile updates the assignment"""
        from api.permissions.admin import create_profile, assign_profile_to_user, get_user_profiles

        conn = mock_db_connection()
        target_user_id = str(uuid.uuid4())
        insert_user(conn, target_user_id, "testuser")
        conn.close()

        profile = await create_profile("Test", None, None, None, sample_user_id)

        # Assign twice (should upsert)
        await assign_profile_to_user(profile["profile_id"], target_user_id, sample_user_id)
        await assign_profile_to_user(profile["profile_id"], target_user_id, sample_user_id)

        # Should only have one assignment
        user_profiles = await get_user_profiles(target_user_id)
        assert len(user_profiles) == 1

    @pytest.mark.asyncio
    async def test_profile_grants_with_scope(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test profile grants with permission scope"""
        from api.permissions.admin import create_profile, update_profile_grants, get_profile_grants

        profile = await create_profile("Test", None, None, None, sample_user_id)

        conn = mock_db_connection()
        insert_permission(conn, "perm1", "test.permission", "feature")
        conn.close()

        grants = [{
            "permission_id": "perm1",
            "is_granted": True,
            "permission_scope": {"resource_types": ["document", "file"]}
        }]

        await update_profile_grants(profile["profile_id"], grants, sample_user_id)
        result = await get_profile_grants(profile["profile_id"])

        assert len(result) == 1
        assert result[0]["permission_scope"] == {"resource_types": ["document", "file"]}

    @pytest.mark.asyncio
    async def test_empty_grants_list(self, mock_db_connection, sample_user_id, mock_audit_log, mock_permission_engine):
        """Test updating with empty grants list"""
        from api.permissions.admin import create_profile, update_profile_grants

        profile = await create_profile("Test", None, None, None, sample_user_id)
        result = await update_profile_grants(profile["profile_id"], [], sample_user_id)

        assert result["status"] == "success"
        assert result["grants_updated"] == 0
