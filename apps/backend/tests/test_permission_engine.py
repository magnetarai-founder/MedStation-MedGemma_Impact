"""
Comprehensive tests for api/permissions/ package (RBAC Permission Engine)

Tests cover:
- PermissionLevel enum and hierarchy
- UserPermissionContext dataclass
- PermissionEngine initialization
- Role baselines (founder_rights, super_admin, admin, member, guest)
- Permission checking (boolean, level-based, scope-based)
- Founder Rights bypass
- Super Admin permissions
- Cache management (invalidation)
- Permission explanation/diagnostics
- Global helpers (get_permission_engine, get_effective_permissions)
"""

import pytest
import sqlite3
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, Mock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.permissions.types import PermissionLevel, UserPermissionContext
from api.permissions.hierarchy import LEVEL_HIERARCHY
from api.permissions.engine import PermissionEngine


# ========== PermissionLevel Enum Tests ==========

class TestPermissionLevel:
    """Tests for PermissionLevel enum"""

    def test_enum_values(self):
        """Test all permission level values"""
        assert PermissionLevel.NONE.value == "none"
        assert PermissionLevel.READ.value == "read"
        assert PermissionLevel.WRITE.value == "write"
        assert PermissionLevel.ADMIN.value == "admin"

    def test_enum_count(self):
        """Test expected number of levels"""
        assert len(PermissionLevel) == 4

    def test_enum_from_string(self):
        """Test creating enum from string value"""
        assert PermissionLevel("none") == PermissionLevel.NONE
        assert PermissionLevel("read") == PermissionLevel.READ
        assert PermissionLevel("write") == PermissionLevel.WRITE
        assert PermissionLevel("admin") == PermissionLevel.ADMIN

    def test_str_enum(self):
        """Test PermissionLevel is str subclass"""
        assert isinstance(PermissionLevel.READ, str)
        assert PermissionLevel.READ == "read"


# ========== Level Hierarchy Tests ==========

class TestLevelHierarchy:
    """Tests for LEVEL_HIERARCHY"""

    def test_hierarchy_ordering(self):
        """Test hierarchy values are correctly ordered"""
        assert LEVEL_HIERARCHY[PermissionLevel.NONE] == 0
        assert LEVEL_HIERARCHY[PermissionLevel.READ] == 1
        assert LEVEL_HIERARCHY[PermissionLevel.WRITE] == 2
        assert LEVEL_HIERARCHY[PermissionLevel.ADMIN] == 3

    def test_hierarchy_comparison(self):
        """Test hierarchy can be used for comparison"""
        assert LEVEL_HIERARCHY[PermissionLevel.ADMIN] > LEVEL_HIERARCHY[PermissionLevel.WRITE]
        assert LEVEL_HIERARCHY[PermissionLevel.WRITE] > LEVEL_HIERARCHY[PermissionLevel.READ]
        assert LEVEL_HIERARCHY[PermissionLevel.READ] > LEVEL_HIERARCHY[PermissionLevel.NONE]


# ========== UserPermissionContext Tests ==========

class TestUserPermissionContext:
    """Tests for UserPermissionContext dataclass"""

    def test_basic_creation(self):
        """Test creating a user permission context"""
        ctx = UserPermissionContext(
            user_id="user-123",
            username="testuser",
            role="member"
        )
        assert ctx.user_id == "user-123"
        assert ctx.username == "testuser"
        assert ctx.role == "member"

    def test_default_values(self):
        """Test default values are initialized"""
        ctx = UserPermissionContext(
            user_id="user-123",
            username="testuser",
            role="member"
        )
        assert ctx.job_role is None
        assert ctx.team_id is None
        assert ctx.is_solo_mode is True
        assert ctx.profiles == []
        assert ctx.permission_sets == []
        assert ctx.effective_permissions == {}

    def test_full_context(self):
        """Test creating a fully populated context"""
        ctx = UserPermissionContext(
            user_id="user-123",
            username="testuser",
            role="admin",
            job_role="Product Manager",
            team_id="team-456",
            is_solo_mode=False,
            profiles=["profile-1", "profile-2"],
            permission_sets=["set-1"],
            effective_permissions={"chat.use": True}
        )
        assert ctx.job_role == "Product Manager"
        assert ctx.team_id == "team-456"
        assert ctx.is_solo_mode is False
        assert ctx.profiles == ["profile-1", "profile-2"]
        assert ctx.permission_sets == ["set-1"]
        assert ctx.effective_permissions == {"chat.use": True}


# ========== PermissionEngine Initialization Tests ==========

class TestPermissionEngineInit:
    """Tests for PermissionEngine initialization"""

    def test_initialization(self):
        """Test engine initialization"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)
            assert engine.db_path == db_path
            assert engine._permission_cache == {}


# ========== Role Baseline Tests ==========

class TestRoleBaselines:
    """Tests for role baseline permissions"""

    @pytest.fixture
    def engine(self):
        """Create permission engine for testing"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            yield PermissionEngine(db_path)

    def test_founder_rights_baseline(self, engine):
        """Test founder_rights has empty baseline (bypass all)"""
        baseline = engine._get_role_baseline("founder_rights")
        assert baseline == {}

    def test_super_admin_baseline(self, engine):
        """Test super_admin has full permissions"""
        baseline = engine._get_role_baseline("super_admin")

        # Boolean features
        assert baseline["chat.use"] is True
        assert baseline["vault.use"] is True
        assert baseline["workflows.use"] is True
        assert baseline["panic.use"] is True
        assert baseline["backups.use"] is True

        # Level-based permissions
        assert baseline["vault.documents.create"] == PermissionLevel.ADMIN
        assert baseline["workflows.manage"] == PermissionLevel.ADMIN

        # System permissions
        assert baseline["system.view_admin_dashboard"] is True
        assert baseline["system.manage_permissions"] is True

    def test_admin_baseline(self, engine):
        """Test admin has most permissions but limited system perms"""
        baseline = engine._get_role_baseline("admin")

        # Boolean features
        assert baseline["chat.use"] is True
        assert baseline["vault.use"] is True
        assert baseline["backups.use"] is False  # Not by default

        # Level-based (WRITE not ADMIN)
        assert baseline["vault.documents.create"] == PermissionLevel.WRITE
        assert baseline["workflows.manage"] == PermissionLevel.READ

        # System permissions (limited)
        assert baseline["system.view_admin_dashboard"] is True
        assert baseline["system.manage_permissions"] is False

    def test_member_baseline(self, engine):
        """Test member has core features only"""
        baseline = engine._get_role_baseline("member")

        # Core features
        assert baseline["chat.use"] is True
        assert baseline["vault.use"] is True
        assert baseline["workflows.use"] is True
        assert baseline["docs.use"] is True

        # Advanced features disabled
        assert baseline["insights.use"] is False
        assert baseline["code.use"] is False
        assert baseline["panic.use"] is False
        assert baseline["backups.use"] is False

        # No system permissions
        assert baseline["system.view_admin_dashboard"] is False
        assert baseline["system.manage_users"] is False

    def test_guest_baseline(self, engine):
        """Test guest has read-only access"""
        baseline = engine._get_role_baseline("guest")

        # Very limited features
        assert baseline["chat.use"] is True
        assert baseline["docs.use"] is True
        assert baseline["vault.use"] is False
        assert baseline["workflows.use"] is False

        # Read-only levels
        assert baseline["vault.documents.create"] == PermissionLevel.NONE
        assert baseline["vault.documents.read"] == PermissionLevel.READ
        assert baseline["docs.read"] == PermissionLevel.READ
        assert baseline["docs.create"] == PermissionLevel.NONE

    def test_unknown_role_baseline(self, engine):
        """Test unknown role has empty baseline (deny all)"""
        baseline = engine._get_role_baseline("unknown_role")
        assert baseline == {}


# ========== Permission Checking Tests ==========

class TestPermissionChecking:
    """Tests for permission checking logic"""

    def test_founder_rights_bypass(self):
        """Test founder_rights bypasses all permission checks"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            ctx = UserPermissionContext(
                user_id="founder",
                username="founder",
                role="founder_rights",
                effective_permissions={}  # Empty - doesn't matter
            )

            # Should be allowed even without explicit permission
            assert engine.has_permission(ctx, "any.permission") is True
            assert engine.has_permission(ctx, "system.manage_permissions") is True

    def test_super_admin_allowed_unless_denied(self):
        """Test super_admin is allowed unless explicitly denied"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            ctx = UserPermissionContext(
                user_id="admin",
                username="admin",
                role="super_admin",
                effective_permissions={
                    "allowed.perm": True,
                    "denied.perm": False,
                    "level.perm": PermissionLevel.NONE,
                }
            )

            # Allowed for undefined
            assert engine.has_permission(ctx, "undefined.perm") is True

            # Explicitly denied
            assert engine.has_permission(ctx, "denied.perm") is False
            assert engine.has_permission(ctx, "level.perm") is False

    def test_boolean_permission(self):
        """Test boolean permission checking"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            ctx = UserPermissionContext(
                user_id="user",
                username="user",
                role="member",
                effective_permissions={
                    "chat.use": True,
                    "backups.use": False,
                }
            )

            assert engine.has_permission(ctx, "chat.use") is True
            assert engine.has_permission(ctx, "backups.use") is False

    def test_level_permission_no_requirement(self):
        """Test level permission without specific level requirement"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            ctx = UserPermissionContext(
                user_id="user",
                username="user",
                role="member",
                effective_permissions={
                    "vault.read": PermissionLevel.READ,
                    "vault.none": PermissionLevel.NONE,
                }
            )

            # Any level except NONE is granted
            assert engine.has_permission(ctx, "vault.read") is True
            assert engine.has_permission(ctx, "vault.none") is False

    def test_level_permission_with_requirement(self):
        """Test level permission with specific level requirement"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            ctx = UserPermissionContext(
                user_id="user",
                username="user",
                role="member",
                effective_permissions={
                    "vault.docs": PermissionLevel.WRITE,
                }
            )

            # WRITE >= READ, so allowed
            assert engine.has_permission(ctx, "vault.docs", required_level="read") is True
            # WRITE >= WRITE, so allowed
            assert engine.has_permission(ctx, "vault.docs", required_level="write") is True
            # WRITE < ADMIN, so denied
            assert engine.has_permission(ctx, "vault.docs", required_level="admin") is False

    def test_undefined_permission_denied(self):
        """Test undefined permission is denied for regular users"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            ctx = UserPermissionContext(
                user_id="user",
                username="user",
                role="member",
                effective_permissions={}
            )

            assert engine.has_permission(ctx, "undefined.permission") is False

    def test_scope_permission(self):
        """Test scope-based permission checking"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            ctx = UserPermissionContext(
                user_id="user",
                username="user",
                role="member",
                effective_permissions={
                    "vault.scope": {"teams": ["team-1", "team-2"]},
                    "empty.scope": {},
                }
            )

            # Non-empty scope is granted
            assert engine.has_permission(ctx, "vault.scope") is True
            # Empty scope is denied
            assert engine.has_permission(ctx, "empty.scope") is False

    def test_invalid_required_level(self):
        """Test invalid required level returns False"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            ctx = UserPermissionContext(
                user_id="user",
                username="user",
                role="member",
                effective_permissions={
                    "vault.docs": PermissionLevel.WRITE,
                }
            )

            assert engine.has_permission(ctx, "vault.docs", required_level="invalid") is False


# ========== Cache Management Tests ==========

class TestCacheManagement:
    """Tests for permission cache management"""

    def test_cache_on_load(self):
        """Test permissions are cached on load"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"

            # Create minimal database
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    role TEXT DEFAULT 'member'
                )
            """)
            cur.execute("INSERT INTO users (user_id, username, role) VALUES (?, ?, ?)",
                       ("user-1", "testuser", "member"))
            # Create stub tables for profiles/sets queries
            cur.execute("""
                CREATE TABLE user_permission_profiles (
                    user_id TEXT,
                    profile_id TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE permission_profiles (
                    profile_id TEXT,
                    team_id TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            cur.execute("""
                CREATE TABLE user_permission_sets (
                    user_id TEXT,
                    permission_set_id TEXT,
                    expires_at TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE permission_sets (
                    permission_set_id TEXT,
                    team_id TEXT
                )
            """)
            conn.commit()
            conn.close()

            engine = PermissionEngine(db_path)

            # First load - should cache
            ctx = engine.load_user_context("user-1")
            assert "user-1:system" in engine._permission_cache

            # Second load - should hit cache
            ctx2 = engine.load_user_context("user-1")
            assert ctx2.effective_permissions == ctx.effective_permissions

    def test_invalidate_user_permissions(self):
        """Test cache invalidation for a user"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            # Manually populate cache
            engine._permission_cache["user-1:system"] = {"chat.use": True}
            engine._permission_cache["user-1:team-1"] = {"team.use": True}
            engine._permission_cache["user-2:system"] = {"chat.use": True}

            # Invalidate user-1
            engine.invalidate_user_permissions("user-1")

            # user-1 entries should be removed
            assert "user-1:system" not in engine._permission_cache
            assert "user-1:team-1" not in engine._permission_cache

            # user-2 should still exist
            assert "user-2:system" in engine._permission_cache


# ========== Permission Explanation Tests ==========

class TestPermissionExplanation:
    """Tests for permission explanation/diagnostics"""

    def test_explanation_disabled_by_default(self):
        """Test explanation returns error when diagnostics disabled"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            ctx = UserPermissionContext(
                user_id="user",
                username="user",
                role="member",
                effective_permissions={"chat.use": True}
            )

            # Should return error since MEDSTATIONOS_PERMS_EXPLAIN not set
            result = engine.explain_permission(ctx, "chat.use")
            assert "error" in result
            assert "Diagnostics disabled" in result["error"]

    def test_explanation_enabled(self):
        """Test explanation when diagnostics enabled"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            ctx = UserPermissionContext(
                user_id="user",
                username="user",
                role="member",
                profiles=["profile-1"],
                permission_sets=["set-1"],
                effective_permissions={"chat.use": True}
            )

            with patch('api.permissions.engine.DIAGNOSTICS_ENABLED', True):
                result = engine.explain_permission(ctx, "chat.use")

            assert result["decision"] == "allow"
            assert result["permission_key"] == "chat.use"
            assert result["user_id"] == "user"
            assert result["role"] == "member"
            assert result["profiles"] == ["profile-1"]
            assert "reason" in result

    def test_explanation_founder_rights(self):
        """Test explanation for founder_rights bypass"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            ctx = UserPermissionContext(
                user_id="founder",
                username="founder",
                role="founder_rights",
                effective_permissions={}
            )

            with patch('api.permissions.engine.DIAGNOSTICS_ENABLED', True):
                result = engine.explain_permission(ctx, "any.permission")

            assert result["decision"] == "allow"
            assert "Founder Rights" in result["reason"]


# ========== Compatibility Shim Tests ==========

class TestCompatibilityShim:
    """Tests for the compatibility shim (api/permission_engine.py)"""

    def test_imports_from_shim(self):
        """Test that all exports are available from shim"""
        from api.permission_engine import (
            PermissionLevel,
            UserPermissionContext,
            LEVEL_HIERARCHY,
            PermissionEngine,
            get_permission_engine,
            get_effective_permissions,
            require_perm,
            require_perm_team,
            has_permission,
        )

        # All imports should succeed
        assert PermissionLevel is not None
        assert UserPermissionContext is not None
        assert LEVEL_HIERARCHY is not None
        assert PermissionEngine is not None

    def test_has_permission_wrapper(self):
        """Test has_permission compatibility wrapper"""
        from api.permission_engine import has_permission

        # Mock the engine
        mock_engine = MagicMock()
        mock_engine.has_permission.return_value = True

        ctx = UserPermissionContext(
            user_id="user",
            username="user",
            role="member",
            effective_permissions={"chat.use": True}
        )

        with patch('api.permission_engine.get_permission_engine', return_value=mock_engine):
            result = has_permission(ctx, "chat.use")

        assert result is True
        mock_engine.has_permission.assert_called_once()


# ========== Edge Cases Tests ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_empty_profiles_and_sets(self):
        """Test resolution with no profiles or sets"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            # Create minimal conn mock
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value = mock_cursor

            perms = engine._resolve_permissions(mock_conn, "member", [], [])

            # Should have member baseline
            assert perms["chat.use"] is True

    def test_level_comparison_edge_cases(self):
        """Test level comparison edge cases"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            ctx = UserPermissionContext(
                user_id="user",
                username="user",
                role="member",
                effective_permissions={
                    "level.none": PermissionLevel.NONE,
                    "level.read": PermissionLevel.READ,
                    "level.admin": PermissionLevel.ADMIN,
                }
            )

            # NONE with none requirement - still False (NONE is not granted)
            assert engine.has_permission(ctx, "level.none") is False

            # READ meets READ requirement
            assert engine.has_permission(ctx, "level.read", required_level="read") is True

            # ADMIN meets all requirements
            assert engine.has_permission(ctx, "level.admin", required_level="admin") is True
            assert engine.has_permission(ctx, "level.admin", required_level="write") is True
            assert engine.has_permission(ctx, "level.admin", required_level="read") is True

    def test_cache_key_with_team(self):
        """Test cache keys include team context"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = PermissionEngine(db_path)

            # Populate cache with different team contexts
            engine._permission_cache["user-1:system"] = {"base": True}
            engine._permission_cache["user-1:team-a"] = {"team": True}
            engine._permission_cache["user-1:team-b"] = {"team": True}

            # All three should exist independently
            assert len([k for k in engine._permission_cache if k.startswith("user-1:")]) == 3


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests with database"""

    @pytest.fixture
    def db_with_schema(self):
        """Create database with full permission schema"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Users table
            cur.execute("""
                CREATE TABLE users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    job_role TEXT,
                    team_id TEXT
                )
            """)

            # Permission profiles
            cur.execute("""
                CREATE TABLE permission_profiles (
                    profile_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    team_id TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)

            # User profile assignments
            cur.execute("""
                CREATE TABLE user_permission_profiles (
                    user_id TEXT,
                    profile_id TEXT,
                    PRIMARY KEY (user_id, profile_id)
                )
            """)

            # Permission sets
            cur.execute("""
                CREATE TABLE permission_sets (
                    permission_set_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    team_id TEXT
                )
            """)

            # User permission set assignments
            cur.execute("""
                CREATE TABLE user_permission_sets (
                    user_id TEXT,
                    permission_set_id TEXT,
                    expires_at TEXT,
                    PRIMARY KEY (user_id, permission_set_id)
                )
            """)

            # Permissions registry
            cur.execute("""
                CREATE TABLE permissions (
                    permission_id TEXT PRIMARY KEY,
                    permission_key TEXT UNIQUE NOT NULL,
                    permission_type TEXT DEFAULT 'boolean'
                )
            """)

            # Profile permissions
            cur.execute("""
                CREATE TABLE profile_permissions (
                    profile_id TEXT,
                    permission_id TEXT,
                    is_granted INTEGER,
                    permission_level TEXT,
                    permission_scope TEXT,
                    PRIMARY KEY (profile_id, permission_id)
                )
            """)

            # Insert test data
            cur.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                       ("user-1", "testuser", "member", "Engineer", None))

            conn.commit()
            conn.close()

            yield db_path

    def test_load_user_context_from_db(self, db_with_schema):
        """Test loading user context from database"""
        engine = PermissionEngine(db_with_schema)
        ctx = engine.load_user_context("user-1")

        assert ctx.user_id == "user-1"
        assert ctx.username == "testuser"
        assert ctx.role == "member"
        assert ctx.job_role == "Engineer"
        assert ctx.is_solo_mode is True  # No team_id

    def test_user_not_found(self, db_with_schema):
        """Test error when user not found"""
        engine = PermissionEngine(db_with_schema)

        with pytest.raises(ValueError, match="User not found"):
            engine.load_user_context("nonexistent")
