"""Comprehensive tests for api/routes/admin.py

Tests the Admin "Danger Zone" router which handles destructive admin operations:
- Reset all data, uninstall app
- Clear chats, team messages, query library/history
- Clear temp files, code files
- Reset settings, reset data
- Export all, export chats, export queries

All endpoints require authentication and specific permissions.

Bug fix (test discovery): Changed Depends(get_current_user_dep) to
Depends(get_current_user_dep()) to correctly resolve the dependency.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# Import the router directly for testing
from api.routes.admin import router, AdminOperationResponse


# ========== Fixtures ==========

@pytest.fixture
def mock_founder_user():
    """Mock authenticated founder user with bypass permissions"""
    return {
        "user_id": "founder-user-123",
        "username": "founder",
        "role": "founder_rights"  # Bypasses permission checks
    }


@pytest.fixture
def mock_admin_user():
    """Mock authenticated admin user"""
    return {
        "user_id": "admin-user-123",
        "username": "admin",
        "role": "admin"
    }


@pytest.fixture
def app(mock_founder_user):
    """Create a test FastAPI app with the admin router and auth mocked"""
    from api.auth_middleware import get_current_user

    test_app = FastAPI()
    test_app.include_router(router)

    # Override get_current_user to return founder (bypasses permissions)
    test_app.dependency_overrides[get_current_user] = lambda: mock_founder_user

    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def unauthenticated_app():
    """Create test app without auth override (for testing auth required)"""
    from api.auth_middleware import get_current_user

    test_app = FastAPI()
    test_app.include_router(router)

    # Override to raise auth error
    async def raise_auth_error():
        raise HTTPException(status_code=401, detail="Not authenticated")

    test_app.dependency_overrides[get_current_user] = raise_auth_error

    return test_app


@pytest.fixture
def unauthenticated_client(unauthenticated_app):
    """Create test client without auth"""
    return TestClient(unauthenticated_app)


# ========== Test AdminOperationResponse Model ==========

class TestAdminOperationResponse:
    """Tests for AdminOperationResponse model"""

    def test_response_model_creation(self):
        """Test AdminOperationResponse model creation"""
        response = AdminOperationResponse(
            success=True,
            message="Operation completed",
            details={"key": "value"}
        )

        assert response.success is True
        assert response.message == "Operation completed"
        assert response.details == {"key": "value"}

    def test_response_model_defaults(self):
        """Test AdminOperationResponse default values"""
        response = AdminOperationResponse(
            success=False,
            message="Failed"
        )

        assert response.details == {}

    def test_response_model_serialization(self):
        """Test model serializes correctly"""
        response = AdminOperationResponse(
            success=True,
            message="Test",
            details={"count": 42}
        )
        data = response.model_dump()

        assert data["success"] is True
        assert data["message"] == "Test"
        assert data["details"]["count"] == 42


# ========== Test Router Configuration ==========

class TestRouterConfiguration:
    """Tests for router configuration"""

    def test_router_prefix(self):
        """Test router has correct prefix"""
        assert router.prefix == "/api/v1/admin"

    def test_router_tags(self):
        """Test router has correct tags"""
        assert "admin" in router.tags

    def test_router_has_routes(self):
        """Test router has routes defined"""
        assert len(router.routes) > 0

    def test_all_routes_are_post(self):
        """Test all admin routes use POST method"""
        for route in router.routes:
            if hasattr(route, 'methods'):
                assert 'POST' in route.methods, f"Route {route.path} should be POST"

    def test_expected_route_count(self):
        """Test router has all 13 expected endpoints"""
        # 10 danger zone + 3 export = 13 routes
        assert len(router.routes) == 13


# ========== Test get_current_user_dep Helper ==========

class TestGetCurrentUserDep:
    """Tests for get_current_user_dep helper"""

    def test_returns_callable(self):
        """Test get_current_user_dep returns a callable"""
        from api.routes.admin import get_current_user_dep

        result = get_current_user_dep()
        assert callable(result)

    def test_returns_get_current_user(self):
        """Test get_current_user_dep returns the auth middleware function"""
        from api.routes.admin import get_current_user_dep
        from api.auth_middleware import get_current_user

        result = get_current_user_dep()
        assert result == get_current_user


# ========== Test Authentication Requirements ==========

class TestAuthenticationRequired:
    """Tests that endpoints require authentication"""

    def test_reset_all_requires_auth(self, unauthenticated_client):
        """Test reset-all requires authentication"""
        response = unauthenticated_client.post("/api/v1/admin/reset-all")
        assert response.status_code == 401

    def test_uninstall_requires_auth(self, unauthenticated_client):
        """Test uninstall requires authentication"""
        response = unauthenticated_client.post("/api/v1/admin/uninstall")
        assert response.status_code == 401

    def test_clear_chats_requires_auth(self, unauthenticated_client):
        """Test clear-chats requires authentication"""
        response = unauthenticated_client.post("/api/v1/admin/clear-chats")
        assert response.status_code == 401

    def test_export_all_requires_auth(self, unauthenticated_client):
        """Test export-all requires authentication"""
        response = unauthenticated_client.post("/api/v1/admin/export-all")
        assert response.status_code == 401


# ========== Test Endpoint Existence (with mocked services) ==========

class TestEndpointExistence:
    """Tests that all expected endpoints exist and respond"""

    def test_reset_all_endpoint_exists(self, client):
        """Test /reset-all endpoint exists"""
        with patch('api.services.admin.reset_all_data', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/reset-all")
                assert response.status_code != 404

    def test_uninstall_endpoint_exists(self, client):
        """Test /uninstall endpoint exists"""
        with patch('api.services.admin.uninstall_app', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/uninstall")
                assert response.status_code != 404

    def test_clear_chats_endpoint_exists(self, client):
        """Test /clear-chats endpoint exists"""
        with patch('api.services.admin.clear_chats', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-chats")
                assert response.status_code != 404

    def test_clear_team_messages_endpoint_exists(self, client):
        """Test /clear-team-messages endpoint exists"""
        with patch('api.services.admin.clear_team_messages', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-team-messages")
                assert response.status_code != 404

    def test_clear_query_library_endpoint_exists(self, client):
        """Test /clear-query-library endpoint exists"""
        with patch('api.services.admin.clear_query_library', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-query-library")
                assert response.status_code != 404

    def test_clear_query_history_endpoint_exists(self, client):
        """Test /clear-query-history endpoint exists"""
        with patch('api.services.admin.clear_query_history', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-query-history")
                assert response.status_code != 404

    def test_clear_temp_files_endpoint_exists(self, client):
        """Test /clear-temp-files endpoint exists"""
        with patch('api.services.admin.clear_temp_files', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-temp-files")
                assert response.status_code != 404

    def test_clear_code_files_endpoint_exists(self, client):
        """Test /clear-code-files endpoint exists"""
        with patch('api.services.admin.clear_code_files', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-code-files")
                assert response.status_code != 404

    def test_reset_settings_endpoint_exists(self, client):
        """Test /reset-settings endpoint exists"""
        with patch('api.services.admin.reset_settings', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/reset-settings")
                assert response.status_code != 404

    def test_reset_data_endpoint_exists(self, client):
        """Test /reset-data endpoint exists"""
        with patch('api.services.admin.reset_data', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/reset-data")
                assert response.status_code != 404

    def test_export_all_endpoint_exists(self, client):
        """Test /export-all endpoint exists"""
        with patch('api.services.admin.export_all_data', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "path": "/tmp/backup.zip"}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/export-all")
                assert response.status_code != 404

    def test_export_chats_endpoint_exists(self, client):
        """Test /export-chats endpoint exists"""
        with patch('api.services.admin.export_chats', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "path": "/tmp/chats.json"}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/export-chats")
                assert response.status_code != 404

    def test_export_queries_endpoint_exists(self, client):
        """Test /export-queries endpoint exists"""
        with patch('api.services.admin.export_queries', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "path": "/tmp/queries.json"}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/export-queries")
                assert response.status_code != 404


# ========== Test Successful Operations ==========

class TestSuccessfulOperations:
    """Tests for successful admin operations with founder user (bypasses perms)"""

    def test_reset_all_success(self, client):
        """Test successful reset all operation"""
        with patch('api.services.admin.reset_all_data', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "message": "All data reset"}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/reset-all")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["success"] is True

    def test_uninstall_success(self, client):
        """Test successful uninstall operation"""
        with patch('api.services.admin.uninstall_app', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "message": "Uninstalled"}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/uninstall")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_clear_chats_success(self, client):
        """Test successful clear chats operation"""
        with patch('api.services.admin.clear_chats', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "message": "Chats cleared", "count": 42}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-chats")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_clear_team_messages_success(self, client):
        """Test successful clear team messages operation"""
        with patch('api.services.admin.clear_team_messages', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "message": "Messages cleared"}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-team-messages")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_clear_query_library_success(self, client):
        """Test successful clear query library operation"""
        with patch('api.services.admin.clear_query_library', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "message": "Library cleared"}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-query-library")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_clear_query_history_success(self, client):
        """Test successful clear query history operation"""
        with patch('api.services.admin.clear_query_history', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "message": "History cleared"}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-query-history")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_clear_temp_files_success(self, client):
        """Test successful clear temp files operation"""
        with patch('api.services.admin.clear_temp_files', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "message": "Temp files cleared", "files_deleted": 15}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-temp-files")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_clear_code_files_success(self, client):
        """Test successful clear code files operation"""
        with patch('api.services.admin.clear_code_files', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "message": "Code files cleared"}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-code-files")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_reset_settings_success(self, client):
        """Test successful reset settings operation"""
        with patch('api.services.admin.reset_settings', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "message": "Settings reset"}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/reset-settings")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_reset_data_success(self, client):
        """Test successful reset data operation"""
        with patch('api.services.admin.reset_data', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "message": "Data reset"}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/reset-data")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_export_all_success(self, client):
        """Test successful export all operation"""
        with patch('api.services.admin.export_all_data', new_callable=AsyncMock) as mock:
            mock.return_value = {
                "success": True,
                "message": "Exported",
                "path": "/tmp/backup.zip",
                "size_mb": 42.5
            }
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/export-all")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "path" in data["data"]["details"]

    def test_export_chats_success(self, client):
        """Test successful export chats operation"""
        with patch('api.services.admin.export_chats', new_callable=AsyncMock) as mock:
            mock.return_value = {
                "success": True,
                "message": "Chats exported",
                "path": "/tmp/chats.json",
                "count": 100
            }
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/export-chats")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_export_queries_success(self, client):
        """Test successful export queries operation"""
        with patch('api.services.admin.export_queries', new_callable=AsyncMock) as mock:
            mock.return_value = {
                "success": True,
                "message": "Queries exported",
                "path": "/tmp/queries.json"
            }
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/export-queries")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True


# ========== Test Error Handling ==========

class TestErrorHandling:
    """Tests for error handling in admin endpoints"""

    def test_service_exception_returns_500(self, client):
        """Test that service exceptions result in 500 error"""
        with patch('api.services.admin.reset_all_data', new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("Database error")
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/reset-all")

                assert response.status_code == 500

    def test_http_exception_passthrough(self, client):
        """Test HTTPException is passed through correctly"""
        with patch('api.services.admin.reset_all_data', new_callable=AsyncMock) as mock:
            mock.side_effect = HTTPException(status_code=400, detail="Bad request")
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/reset-all")

                assert response.status_code == 400

    def test_service_returns_failure(self, client):
        """Test handling when service returns failure status"""
        with patch('api.services.admin.clear_chats', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": False, "message": "No chats to clear"}
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-chats")

                # Still returns 200 - success/failure is in the response body
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["success"] is False


# ========== Test Permission Requirements ==========

class TestPermissionRequirements:
    """Tests for permission decorator usage"""

    def test_router_uses_require_perm_decorator(self):
        """Test routes have require_perm decorators"""
        from api.routes import admin
        assert hasattr(admin, 'require_perm')

    def test_danger_zone_endpoints_require_system_manage(self):
        """Verify danger zone endpoints are configured"""
        danger_endpoints = [
            "reset-all", "uninstall", "clear-chats", "clear-team-messages",
            "clear-query-library", "clear-query-history", "clear-temp-files",
            "clear-code-files", "reset-settings", "reset-data"
        ]

        route_paths = [r.path for r in router.routes if hasattr(r, 'path')]
        for endpoint in danger_endpoints:
            assert any(endpoint in path for path in route_paths), f"Missing endpoint: {endpoint}"

    def test_export_endpoints_exist(self):
        """Verify export endpoints exist"""
        export_endpoints = ["export-all", "export-chats", "export-queries"]

        route_paths = [r.path for r in router.routes if hasattr(r, 'path')]
        for endpoint in export_endpoints:
            assert any(endpoint in path for path in route_paths), f"Missing endpoint: {endpoint}"

    def test_non_founder_blocked_without_permission(self):
        """Test that non-founder users are blocked by permission check"""
        from api.auth_middleware import get_current_user

        test_app = FastAPI()
        test_app.include_router(router)

        # Use admin role (not founder_rights)
        regular_admin = {
            "user_id": "admin-123",
            "username": "admin",
            "role": "admin"
        }
        test_app.dependency_overrides[get_current_user] = lambda: regular_admin

        client = TestClient(test_app)

        with patch('api.services.admin.reset_all_data', new_callable=AsyncMock):
            with patch('api.routes.admin.record_audit_event'):
                # Mock permission engine to deny
                with patch('api.permissions.decorators.get_permission_engine') as mock_engine:
                    mock_instance = MagicMock()
                    mock_instance.load_user_context.return_value = MagicMock(
                        username="admin",
                        role="admin"
                    )
                    mock_instance.has_permission.return_value = False
                    mock_engine.return_value = mock_instance

                    response = client.post("/api/v1/admin/reset-all")
                    assert response.status_code == 403


# ========== Test Audit Logging ==========

class TestAuditLogging:
    """Tests for audit logging in admin operations"""

    def test_reset_all_logs_audit(self, client):
        """Test reset all operation is audited"""
        with patch('api.services.admin.reset_all_data', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True}
            with patch('api.routes.admin.record_audit_event') as mock_audit:
                response = client.post("/api/v1/admin/reset-all")

                assert response.status_code == 200
                mock_audit.assert_called_once()

    def test_export_all_logs_audit(self, client):
        """Test export all operation is audited"""
        with patch('api.services.admin.export_all_data', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "path": "/tmp/backup.zip"}
            with patch('api.routes.admin.record_audit_event') as mock_audit:
                response = client.post("/api/v1/admin/export-all")

                assert response.status_code == 200
                mock_audit.assert_called_once()

    def test_audit_contains_user_id(self, client):
        """Test audit event contains user ID"""
        with patch('api.services.admin.clear_chats', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True}
            with patch('api.routes.admin.record_audit_event') as mock_audit:
                response = client.post("/api/v1/admin/clear-chats")

                assert response.status_code == 200
                # Check that user_id was passed to audit
                call_args = mock_audit.call_args
                assert call_args.kwargs.get('user_id') == 'founder-user-123'


# ========== Test Route Names ==========

class TestRouteNames:
    """Tests for route naming conventions"""

    def test_routes_have_names(self):
        """Test all routes have descriptive names"""
        for route in router.routes:
            if hasattr(route, 'name') and route.name:
                assert route.name.startswith('admin_'), f"Route {route.path} name should start with admin_"

    def test_routes_have_summaries(self):
        """Test all routes have OpenAPI summaries"""
        for route in router.routes:
            if hasattr(route, 'summary'):
                assert route.summary is not None, f"Route {route.path} should have a summary"

    def test_danger_routes_indicate_danger(self):
        """Test danger zone routes are marked in summary"""
        danger_summaries = []
        for route in router.routes:
            if hasattr(route, 'summary') and route.summary:
                if 'DANGER' in route.summary:
                    danger_summaries.append(route.path)

        # Should have multiple danger zone endpoints
        assert len(danger_summaries) >= 5


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests for admin operations"""

    def test_multiple_operations_sequence(self, client):
        """Test multiple admin operations in sequence"""
        with patch('api.services.admin.clear_temp_files', new_callable=AsyncMock) as mock_temp:
            with patch('api.services.admin.clear_code_files', new_callable=AsyncMock) as mock_code:
                mock_temp.return_value = {"success": True}
                mock_code.return_value = {"success": True}
                with patch('api.routes.admin.record_audit_event'):
                    # Clear temp files
                    resp1 = client.post("/api/v1/admin/clear-temp-files")
                    assert resp1.status_code == 200

                    # Clear code files
                    resp2 = client.post("/api/v1/admin/clear-code-files")
                    assert resp2.status_code == 200

    def test_export_operations_return_path(self, client):
        """Test export operations return file path in details"""
        with patch('api.services.admin.export_all_data', new_callable=AsyncMock) as mock:
            mock.return_value = {
                "success": True,
                "message": "Backup created",
                "path": "/exports/backup_2024.zip",
                "size_mb": 42.5
            }
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/export-all")

                assert response.status_code == 200
                data = response.json()
                assert "path" in data["data"]["details"]

    def test_response_structure_consistency(self, client):
        """Test all endpoints return consistent response structure"""
        endpoints = [
            ("/api/v1/admin/reset-all", "api.services.admin.reset_all_data"),
            ("/api/v1/admin/clear-chats", "api.services.admin.clear_chats"),
            ("/api/v1/admin/export-all", "api.services.admin.export_all_data"),
        ]

        for endpoint, service_path in endpoints:
            with patch(service_path, new_callable=AsyncMock) as mock:
                mock.return_value = {"success": True, "message": "Done"}
                with patch('api.routes.admin.record_audit_event'):
                    response = client.post(endpoint)

                    assert response.status_code == 200
                    data = response.json()
                    # All responses should have consistent structure
                    assert "success" in data
                    assert "data" in data
                    assert "success" in data["data"]
                    assert "message" in data["data"]


# ========== Test Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_empty_result_from_service(self, client):
        """Test handling of empty result from service"""
        with patch('api.services.admin.clear_query_history', new_callable=AsyncMock) as mock:
            mock.return_value = {}  # Empty dict
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-query-history")

                # Should still succeed with defaults
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["success"] is True  # Default to True

    def test_service_timeout_handling(self, client):
        """Test handling of service timeout - returns 504 Gateway Timeout"""
        import asyncio

        async def slow_service():
            await asyncio.sleep(0.1)
            return {"success": True}

        with patch('api.services.admin.reset_settings', new_callable=AsyncMock) as mock:
            mock.side_effect = asyncio.TimeoutError("Service timeout")
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/reset-settings")

                # Should return 504 Gateway Timeout for timeout errors
                assert response.status_code == 504

    def test_unicode_in_response_message(self, client):
        """Test handling of unicode in service response"""
        with patch('api.services.admin.clear_chats', new_callable=AsyncMock) as mock:
            mock.return_value = {
                "success": True,
                "message": "清除聊天记录成功 ✓"  # Chinese + emoji
            }
            with patch('api.routes.admin.record_audit_event'):
                response = client.post("/api/v1/admin/clear-chats")

                assert response.status_code == 200
                data = response.json()
                assert "清除" in data["data"]["message"]
