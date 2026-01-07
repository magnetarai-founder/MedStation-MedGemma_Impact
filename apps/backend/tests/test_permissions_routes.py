"""Comprehensive tests for api/routes/permissions.py

Tests the RBAC (Role-Based Access Control) management router:
- Permission registry endpoints
- Permission profile CRUD
- Profile grants management
- User assignment (profiles and permission sets)
- Permission set CRUD
- Cache invalidation
- Effective permissions query

All endpoints require authentication and system.manage_permissions permission.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# Import the router directly for testing
from api.routes.permissions import router


# ========== Test Data Templates ==========

def make_permission(permission_id="p1", key="vault.read"):
    """Create a valid permission dict with all required fields"""
    return {
        "permission_id": permission_id,
        "permission_key": key,
        "permission_name": f"{key.replace('.', ' ').title()}",
        "permission_description": f"Permission for {key}",
        "category": key.split(".")[0] if "." in key else "system",
        "subcategory": None,
        "permission_type": "boolean",
        "is_system": False,
        "created_at": "2025-01-01T00:00:00Z"
    }


def make_profile(profile_id="prof1", name="Test Profile"):
    """Create a valid permission profile dict with all required fields"""
    return {
        "profile_id": profile_id,
        "profile_name": name,
        "profile_description": f"Description for {name}",
        "team_id": None,
        "applies_to_role": None,
        "created_by": "admin",
        "created_at": "2025-01-01T00:00:00Z",
        "modified_at": "2025-01-01T00:00:00Z",
        "is_active": True
    }


def make_permission_set(set_id="set1", name="Test Set"):
    """Create a valid permission set dict with all required fields"""
    return {
        "permission_set_id": set_id,
        "set_name": name,
        "set_description": f"Description for {name}",
        "team_id": None,
        "created_by": "admin",
        "created_at": "2025-01-01T00:00:00Z",
        "is_active": True
    }


# ========== Fixtures ==========

@pytest.fixture
def mock_founder_user():
    """Mock authenticated founder user with bypass permissions"""
    return {
        "user_id": "founder-user-123",
        "username": "founder",
        "role": "founder_rights"
    }


@pytest.fixture
def app(mock_founder_user):
    """Create a test FastAPI app with the permissions router and auth mocked"""
    from api.auth_middleware import get_current_user

    test_app = FastAPI()
    test_app.include_router(router)

    # Override get_current_user dependency
    test_app.dependency_overrides[get_current_user] = lambda: mock_founder_user

    # Add middleware to set request.state.user
    @test_app.middleware("http")
    async def add_user_state(request, call_next):
        request.state.user = mock_founder_user
        response = await call_next(request)
        return response

    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


# ========== Test Router Configuration ==========

class TestRouterConfiguration:
    """Tests for router configuration"""

    def test_router_prefix(self):
        """Test router has correct prefix"""
        assert router.prefix == "/api/v1/permissions"

    def test_router_tags(self):
        """Test router has correct tags"""
        assert "permissions" in router.tags

    def test_router_has_routes(self):
        """Test router has routes defined"""
        assert len(router.routes) > 0

    def test_expected_route_count(self):
        """Test router has expected number of endpoints"""
        # At least 15 endpoints
        assert len(router.routes) >= 15

    def test_router_has_auth_dependency(self):
        """Test router has authentication dependency at router level"""
        assert len(router.dependencies) > 0


# ========== Test Permission Registry Endpoints ==========

class TestPermissionRegistryEndpoints:
    """Tests for /permissions endpoint"""

    def test_get_all_permissions_success(self, client):
        """Test getting all permissions"""
        with patch('api.services.permissions.get_all_permissions', new_callable=AsyncMock) as mock:
            mock.return_value = [make_permission("p1", "vault.read"), make_permission("p2", "vault.write")]
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/permissions")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]) == 2

    def test_get_permissions_with_category_filter(self, client):
        """Test getting permissions filtered by category"""
        with patch('api.services.permissions.get_all_permissions', new_callable=AsyncMock) as mock:
            mock.return_value = [make_permission("p1", "vault.read")]
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/permissions?category=vault")

                assert response.status_code == 200
                mock.assert_called_once_with("vault")


# ========== Test Profile Endpoints ==========

class TestProfileEndpoints:
    """Tests for permission profile CRUD endpoints"""

    def test_get_all_profiles_success(self, client):
        """Test getting all permission profiles"""
        with patch('api.services.permissions.get_all_profiles', new_callable=AsyncMock) as mock:
            mock.return_value = [make_profile("prof1", "Admin Profile"), make_profile("prof2", "User Profile")]
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/profiles")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]) == 2

    def test_get_profiles_with_team_filter(self, client):
        """Test getting profiles filtered by team"""
        with patch('api.services.permissions.get_all_profiles', new_callable=AsyncMock) as mock:
            mock.return_value = []
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/profiles?team_id=team-123")

                assert response.status_code == 200
                mock.assert_called_once_with("team-123")

    def test_create_profile_success(self, client):
        """Test creating a permission profile"""
        with patch('api.services.permissions.create_profile', new_callable=AsyncMock) as mock:
            mock.return_value = make_profile("new-prof", "New Profile")
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.post(
                    "/api/v1/permissions/profiles",
                    json={
                        "profile_name": "New Profile",
                        "profile_description": "Test profile"
                    }
                )

                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["data"]["profile_name"] == "New Profile"

    def test_get_profile_by_id_success(self, client):
        """Test getting a specific profile"""
        with patch('api.services.permissions.get_profile', new_callable=AsyncMock) as mock:
            mock.return_value = make_profile("prof1", "Admin Profile")
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/profiles/prof1")

                assert response.status_code == 200
                data = response.json()
                assert data["data"]["profile_id"] == "prof1"

    def test_update_profile_success(self, client):
        """Test updating a permission profile"""
        updated_profile = make_profile("prof1", "Updated Profile")
        with patch('api.services.permissions.update_profile', new_callable=AsyncMock) as mock:
            mock.return_value = updated_profile
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.put(
                    "/api/v1/permissions/profiles/prof1",
                    json={"profile_name": "Updated Profile"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["data"]["profile_name"] == "Updated Profile"


# ========== Test Profile Grants Endpoints ==========

class TestProfileGrantsEndpoints:
    """Tests for profile grants management"""

    def test_get_profile_grants_success(self, client):
        """Test getting grants for a profile"""
        with patch('api.services.permissions.get_profile_grants', new_callable=AsyncMock) as mock:
            mock.return_value = [
                {"permission_id": "p1", "level": "read"},
                {"permission_id": "p2", "level": "write"}
            ]
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/profiles/prof1/grants")

                assert response.status_code == 200
                data = response.json()
                assert len(data["data"]) == 2

    def test_update_profile_grants_success(self, client):
        """Test updating grants for a profile"""
        with patch('api.services.permissions.update_profile_grants', new_callable=AsyncMock) as mock:
            mock.return_value = {"updated": 2}
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.post(
                    "/api/v1/permissions/profiles/prof1/grants",
                    json=[
                        {"permission_id": "p1", "is_granted": True, "permission_level": "read"},
                        {"permission_id": "p2", "is_granted": True, "permission_level": "write"}
                    ]
                )

                assert response.status_code == 200


# ========== Test User Assignment Endpoints ==========

class TestUserAssignmentEndpoints:
    """Tests for assigning/unassigning profiles to users"""

    def test_assign_profile_to_user_success(self, client):
        """Test assigning a profile to a user"""
        with patch('api.services.permissions.assign_profile_to_user', new_callable=AsyncMock) as mock:
            mock.return_value = {"assigned": True, "user_id": "user-123"}
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.post("/api/v1/permissions/profiles/prof1/assign/user-123")

                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True

    def test_unassign_profile_from_user_success(self, client):
        """Test unassigning a profile from a user"""
        with patch('api.services.permissions.unassign_profile_from_user', new_callable=AsyncMock) as mock:
            mock.return_value = {"unassigned": True}
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.delete("/api/v1/permissions/profiles/prof1/assign/user-123")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_get_user_profiles_success(self, client):
        """Test getting profiles assigned to a user"""
        with patch('api.services.permissions.get_user_profiles', new_callable=AsyncMock) as mock:
            mock.return_value = [{"profile_id": "prof1", "profile_name": "Admin Profile"}]
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/users/user-123/profiles")

                assert response.status_code == 200
                data = response.json()
                assert len(data["data"]) == 1


# ========== Test Permission Set Endpoints ==========

class TestPermissionSetEndpoints:
    """Tests for permission set CRUD endpoints"""

    def test_get_all_permission_sets_success(self, client):
        """Test getting all permission sets"""
        with patch('api.services.permissions.get_all_permission_sets', new_callable=AsyncMock) as mock:
            mock.return_value = [
                make_permission_set("set1", "Admin Set"),
                make_permission_set("set2", "User Set")
            ]
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/permission-sets")

                assert response.status_code == 200
                data = response.json()
                assert len(data["data"]) == 2

    def test_create_permission_set_success(self, client):
        """Test creating a permission set"""
        with patch('api.services.permissions.create_permission_set', new_callable=AsyncMock) as mock:
            mock.return_value = make_permission_set("new-set", "New Set")
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.post(
                    "/api/v1/permissions/permission-sets",
                    json={
                        "set_name": "New Set",
                        "set_description": "Test set"
                    }
                )

                assert response.status_code == 201
                data = response.json()
                assert data["data"]["set_name"] == "New Set"

    def test_assign_permission_set_success(self, client):
        """Test assigning a permission set to a user"""
        with patch('api.services.permissions.assign_permission_set_to_user', new_callable=AsyncMock) as mock:
            mock.return_value = {"assigned": True}
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.post("/api/v1/permissions/permission-sets/set1/assign/user-123")

                assert response.status_code == 201

    def test_assign_permission_set_with_expiry(self, client):
        """Test assigning a permission set with expiration"""
        with patch('api.services.permissions.assign_permission_set_to_user', new_callable=AsyncMock) as mock:
            mock.return_value = {"assigned": True, "expires_at": "2025-12-31"}
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.post(
                    "/api/v1/permissions/permission-sets/set1/assign/user-123?expires_at=2025-12-31"
                )

                assert response.status_code == 201
                mock.assert_called_once()
                call_args = mock.call_args
                assert call_args.kwargs.get("expires_at") == "2025-12-31"

    def test_unassign_permission_set_success(self, client):
        """Test unassigning a permission set from a user"""
        with patch('api.services.permissions.unassign_permission_set_from_user', new_callable=AsyncMock) as mock:
            mock.return_value = {"unassigned": True}
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.delete("/api/v1/permissions/permission-sets/set1/assign/user-123")

                assert response.status_code == 200


# ========== Test Permission Set Grants Endpoints ==========

class TestPermissionSetGrantsEndpoints:
    """Tests for permission set grants management"""

    def test_get_permission_set_grants_success(self, client):
        """Test getting grants for a permission set"""
        with patch('api.services.permissions.get_permission_set_grants', new_callable=AsyncMock) as mock:
            mock.return_value = [{"permission_id": "p1", "level": "admin"}]
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/permission-sets/set1/grants")

                assert response.status_code == 200

    def test_update_permission_set_grants_success(self, client):
        """Test updating grants for a permission set"""
        with patch('api.services.permissions.update_permission_set_grants', new_callable=AsyncMock) as mock:
            mock.return_value = {"updated": 1}
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.post(
                    "/api/v1/permissions/permission-sets/set1/grants",
                    json=[{"permission_id": "p1", "is_granted": True, "permission_level": "admin"}]
                )

                assert response.status_code == 200

    def test_delete_permission_set_grant_success(self, client):
        """Test deleting a specific grant from a permission set"""
        with patch('api.services.permissions.delete_permission_set_grant', new_callable=AsyncMock) as mock:
            mock.return_value = {"deleted": True}
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.delete("/api/v1/permissions/permission-sets/set1/grants/p1")

                assert response.status_code == 200


# ========== Test Cache Invalidation ==========

class TestCacheInvalidation:
    """Tests for cache invalidation endpoint"""

    def test_invalidate_user_permissions_success(self, client):
        """Test invalidating user permission cache"""
        with patch('api.services.permissions.invalidate_user_permissions', new_callable=AsyncMock) as mock:
            mock.return_value = {"invalidated": True, "user_id": "user-123"}
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.post("/api/v1/permissions/users/user-123/permissions/invalidate")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True


# ========== Test Effective Permissions ==========

class TestEffectivePermissions:
    """Tests for effective permissions endpoint"""

    def test_get_effective_permissions_success(self, client, mock_founder_user):
        """Test getting effective permissions for current user"""
        mock_context = MagicMock()
        mock_context.effective_permissions = {"vault.read": True, "vault.write": True}

        with patch('permission_engine.get_permission_engine') as mock_engine:
            mock_engine_instance = MagicMock()
            mock_engine_instance.load_user_context.return_value = mock_context
            mock_engine.return_value = mock_engine_instance

            response = client.get("/api/v1/permissions/effective")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["user_id"] == "founder-user-123"
            assert "effective_permissions" in data["data"]

    def test_get_effective_permissions_with_team(self, client):
        """Test getting effective permissions with team context"""
        mock_context = MagicMock()
        mock_context.effective_permissions = {"team.read": True}

        with patch('permission_engine.get_permission_engine') as mock_engine:
            mock_engine_instance = MagicMock()
            mock_engine_instance.load_user_context.return_value = mock_context
            mock_engine.return_value = mock_engine_instance

            response = client.get("/api/v1/permissions/effective?team_id=team-123")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["team_id"] == "team-123"


# ========== Test Error Handling ==========

class TestErrorHandling:
    """Tests for error handling in permission endpoints"""

    def test_service_exception_returns_500(self, client):
        """Test that service exceptions result in 500 error"""
        with patch('api.services.permissions.get_all_permissions', new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("Database error")
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/permissions")

                assert response.status_code == 500

    def test_http_exception_passthrough(self, client):
        """Test HTTPException is passed through correctly"""
        with patch('api.services.permissions.get_profile', new_callable=AsyncMock) as mock:
            mock.side_effect = HTTPException(status_code=404, detail="Profile not found")
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/profiles/nonexistent")

                assert response.status_code == 404


# ========== Test Route Names ==========

class TestRouteNames:
    """Tests for route naming conventions"""

    def test_routes_have_names(self):
        """Test all routes have descriptive names"""
        for route in router.routes:
            if hasattr(route, 'name') and route.name:
                assert route.name.startswith('permissions_'), f"Route {route.path} name should start with permissions_"

    def test_all_expected_routes_exist(self):
        """Test all expected endpoints are defined"""
        route_names = [r.name for r in router.routes if hasattr(r, 'name')]

        expected_routes = [
            "permissions_get_all",
            "permissions_get_profiles",
            "permissions_create_profile",
            "permissions_get_profile",
            "permissions_update_profile",
            "permissions_get_profile_grants",
            "permissions_update_profile_grants",
            "permissions_assign_profile",
            "permissions_unassign_profile",
            "permissions_get_user_profiles",
            "permissions_get_permission_sets",
            "permissions_create_permission_set",
            "permissions_assign_permission_set",
            "permissions_unassign_permission_set",
            "permissions_get_permission_set_grants",
            "permissions_update_permission_set_grants",
            "permissions_delete_permission_set_grant",
            "permissions_invalidate_user_permissions",
            "permissions_get_effective",
        ]

        for expected in expected_routes:
            assert expected in route_names, f"Missing route: {expected}"


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests for permission workflows"""

    def test_profile_lifecycle(self, client):
        """Test complete profile lifecycle: create -> update -> assign -> unassign"""
        with patch('permission_engine.require_perm') as mock_perm:
            mock_perm.return_value = lambda f: f

            # Create profile
            with patch('api.services.permissions.create_profile', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = make_profile("new-prof", "Test Profile")
                response = client.post(
                    "/api/v1/permissions/profiles",
                    json={"profile_name": "Test Profile"}
                )
                assert response.status_code == 201

            # Update profile
            with patch('api.services.permissions.update_profile', new_callable=AsyncMock) as mock_update:
                mock_update.return_value = make_profile("new-prof", "Updated Profile")
                response = client.put(
                    "/api/v1/permissions/profiles/new-prof",
                    json={"profile_name": "Updated Profile"}
                )
                assert response.status_code == 200

            # Assign to user
            with patch('api.services.permissions.assign_profile_to_user', new_callable=AsyncMock) as mock_assign:
                mock_assign.return_value = {"assigned": True}
                response = client.post("/api/v1/permissions/profiles/new-prof/assign/user-123")
                assert response.status_code == 201

            # Unassign from user
            with patch('api.services.permissions.unassign_profile_from_user', new_callable=AsyncMock) as mock_unassign:
                mock_unassign.return_value = {"unassigned": True}
                response = client.delete("/api/v1/permissions/profiles/new-prof/assign/user-123")
                assert response.status_code == 200

    def test_permission_set_with_grants(self, client):
        """Test creating permission set and adding grants"""
        with patch('permission_engine.require_perm') as mock_perm:
            mock_perm.return_value = lambda f: f

            # Create set
            with patch('api.services.permissions.create_permission_set', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = make_permission_set("new-set", "Admin Override")
                response = client.post(
                    "/api/v1/permissions/permission-sets",
                    json={"set_name": "Admin Override"}
                )
                assert response.status_code == 201

            # Add grants
            with patch('api.services.permissions.update_permission_set_grants', new_callable=AsyncMock) as mock_grants:
                mock_grants.return_value = {"updated": 2}
                response = client.post(
                    "/api/v1/permissions/permission-sets/new-set/grants",
                    json=[{"permission_id": "admin.all", "is_granted": True, "permission_level": "admin"}]
                )
                assert response.status_code == 200

            # Assign to user
            with patch('api.services.permissions.assign_permission_set_to_user', new_callable=AsyncMock) as mock_assign:
                mock_assign.return_value = {"assigned": True}
                response = client.post("/api/v1/permissions/permission-sets/new-set/assign/user-123")
                assert response.status_code == 201


# ========== Test Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_empty_permissions_list(self, client):
        """Test handling of empty permissions list"""
        with patch('api.services.permissions.get_all_permissions', new_callable=AsyncMock) as mock:
            mock.return_value = []
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/permissions")

                assert response.status_code == 200
                data = response.json()
                assert data["data"] == []

    def test_empty_profiles_list(self, client):
        """Test handling of empty profiles list"""
        with patch('api.services.permissions.get_all_profiles', new_callable=AsyncMock) as mock:
            mock.return_value = []
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.get("/api/v1/permissions/profiles")

                assert response.status_code == 200
                data = response.json()
                assert data["data"] == []

    def test_unicode_in_profile_name(self, client):
        """Test handling of unicode in profile name"""
        unicode_profile = make_profile("unicode-prof", "管理员配置 🔐")
        with patch('api.services.permissions.create_profile', new_callable=AsyncMock) as mock:
            mock.return_value = unicode_profile
            with patch('permission_engine.require_perm') as mock_perm:
                mock_perm.return_value = lambda f: f

                response = client.post(
                    "/api/v1/permissions/profiles",
                    json={"profile_name": "管理员配置 🔐"}
                )

                assert response.status_code == 201
                data = response.json()
                assert "管理员" in data["data"]["profile_name"]
