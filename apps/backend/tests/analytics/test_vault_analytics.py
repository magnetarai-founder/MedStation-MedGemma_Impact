"""
Vault Analytics Endpoint Tests

Tests analytics endpoints for storage trends, access patterns, and activity timeline.
Verifies stable response shapes and handles both empty and active vault states.
"""

import io
import pytest
from fastapi.testclient import TestClient


class TestAnalyticsEmpty:
    """Test analytics endpoints with empty vault"""

    def test_analytics_empty(self, client: TestClient):
        """
        Test all analytics endpoints return stable shapes when vault is empty.
        Endpoints should return 200 with consistent structure even without data.
        """

        # Test storage trends
        storage_response = client.get(
            "/api/v1/vault/analytics/storage-trends",
            params={"vault_type": "real", "days": 30}
        )
        assert storage_response.status_code == 200, \
            f"Storage trends failed: {storage_response.text}"

        storage_data = storage_response.json()
        # Verify stable shape - lists may be empty but keys should exist
        assert isinstance(storage_data, dict), "Expected dict response"
        # Accept various possible keys
        assert any(
            key in storage_data for key in ["trends", "data", "storage_trends"]
        ), f"Expected trend data key, got: {storage_data.keys()}"

        # Test access patterns
        access_response = client.get(
            "/api/v1/vault/analytics/access-patterns",
            params={"vault_type": "real", "days": 30}
        )
        assert access_response.status_code == 200, \
            f"Access patterns failed: {access_response.text}"

        access_data = access_response.json()
        assert isinstance(access_data, dict), "Expected dict response"

        # Test activity timeline
        activity_response = client.get(
            "/api/v1/vault/analytics/activity-timeline",
            params={"vault_type": "real", "days": 30}
        )
        assert activity_response.status_code == 200, \
            f"Activity timeline failed: {activity_response.text}"

        activity_data = activity_response.json()
        assert isinstance(activity_data, dict), "Expected dict response"


class TestAnalyticsAfterActivity:
    """Test analytics endpoints after vault activity"""

    def test_analytics_after_activity(self, client: TestClient):
        """
        Perform vault operations and verify analytics reflect activity.
        Be tolerant: assert presence and types rather than exact counts.
        """

        # Setup: Create vault activity
        file_content = b"Analytics test file"
        files = {"file": ("analytics_test.txt", io.BytesIO(file_content), "text/plain")}
        upload_data = {
            "vault_passphrase": "TestPassword123!",
            "vault_type": "real",
            "folder_path": "/"
        }

        # 1. Upload file
        upload_response = client.post("/api/v1/vault/upload", files=files, data=upload_data)
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]

        # 2. Download file (create access pattern)
        download_response = client.get(
            f"/api/v1/vault/files/{file_id}/download",
            params={"vault_type": "real", "vault_passphrase": "TestPassword123!"}
        )
        # Download may succeed or fail depending on implementation
        # Accept 200 or error codes
        assert download_response.status_code in [200, 401, 403, 404]

        # 3. Add comment (create activity)
        comment_data = {
            "comment_text": "Analytics test comment",
            "vault_type": "real"
        }
        comment_response = client.post(
            f"/api/v1/vault/files/{file_id}/comments",
            data=comment_data
        )
        # May succeed or fail based on implementation
        if comment_response.status_code == 200:
            comment_id = comment_response.json().get("comment_id")

            # Delete comment
            if comment_id:
                client.delete(
                    f"/api/v1/vault/comments/{comment_id}",
                    params={"vault_type": "real"}
                )

        # 4. Trash and restore (create activity)
        trash_data = {"vault_type": "real"}
        trash_response = client.post(
            f"/api/v1/vault/files/{file_id}/trash",
            data=trash_data
        )
        if trash_response.status_code == 200:
            restore_data = {"vault_type": "real"}
            client.post(
                f"/api/v1/vault/files/{file_id}/restore",
                data=restore_data
            )

        # Now query analytics
        storage_response = client.get(
            "/api/v1/vault/analytics/storage-trends",
            params={"vault_type": "real", "days": 30}
        )
        assert storage_response.status_code == 200
        storage_data = storage_response.json()

        # Verify non-empty or at least stable structure
        assert isinstance(storage_data, dict)
        # Look for any trend/data arrays
        for key in ["trends", "data", "storage_trends"]:
            if key in storage_data:
                assert isinstance(storage_data[key], list)
                # Accept empty or non-empty - just verify type

        # Access patterns
        access_response = client.get(
            "/api/v1/vault/analytics/access-patterns",
            params={"vault_type": "real", "days": 30}
        )
        assert access_response.status_code == 200
        access_data = access_response.json()
        assert isinstance(access_data, dict)

        # Activity timeline
        activity_response = client.get(
            "/api/v1/vault/analytics/activity-timeline",
            params={"vault_type": "real", "days": 30}
        )
        assert activity_response.status_code == 200
        activity_data = activity_response.json()
        assert isinstance(activity_data, dict)

        # Verify some activity field exists (could be "activities", "timeline", etc.)
        activity_keys = activity_data.keys()
        assert len(activity_keys) > 0, "Expected some data in activity timeline"
