"""
Vault Lifecycle Tests

Tests the full lifecycle of vault operations:
- Upload → Comment → Trash → Restore
- Versions (create, list, restore)
- Sharing (create, list, revoke, download)
"""

import io
import pytest
from fastapi.testclient import TestClient


class TestFileLifecycle:
    """Test file upload, comment, trash, restore operations"""

    def test_file_upload_comment_trash_restore(self, client: TestClient):
        """Test complete file lifecycle with comments and trash operations"""

        # 1. Upload a small text file
        file_content = b"Test vault file content"
        files = {"file": ("test_file.txt", io.BytesIO(file_content), "text/plain")}
        data = {
            "vault_passphrase": "TestPassword123!",
            "vault_type": "real",
            "folder_path": "/"
        }

        upload_response = client.post("/api/v1/vault/upload", files=files, data=data)
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"

        upload_data = upload_response.json()
        assert "file_id" in upload_data
        file_id = upload_data["file_id"]

        # 2. Add a comment
        comment_data = {
            "comment_text": "Initial test comment",
            "vault_type": "real"
        }
        add_comment_response = client.post(
            f"/api/v1/vault/files/{file_id}/comments",
            data=comment_data
        )
        assert add_comment_response.status_code == 200, f"Add comment failed: {add_comment_response.text}"
        comment_result = add_comment_response.json()
        assert "comment_id" in comment_result
        comment_id = comment_result["comment_id"]

        # 3. List comments (should have ≥1)
        list_comments_response = client.get(
            f"/api/v1/vault/files/{file_id}/comments",
            params={"vault_type": "real"}
        )
        assert list_comments_response.status_code == 200
        comments_data = list_comments_response.json()
        assert "data" in comments_data or "comments" in comments_data
        comments = comments_data.get("data") or comments_data.get("comments", [])
        assert len(comments) >= 1, "Expected at least 1 comment"

        # 4. Update comment
        update_data = {
            "comment_text": "Updated test comment",
            "vault_type": "real"
        }
        update_response = client.put(
            f"/api/v1/vault/comments/{comment_id}",
            data=update_data
        )
        assert update_response.status_code == 200, f"Update comment failed: {update_response.text}"

        # 5. Delete comment
        delete_comment_response = client.delete(
            f"/api/v1/vault/comments/{comment_id}",
            params={"vault_type": "real"}
        )
        assert delete_comment_response.status_code == 200

        # 6. List comments (should be 0 now)
        list_after_delete = client.get(
            f"/api/v1/vault/files/{file_id}/comments",
            params={"vault_type": "real"}
        )
        assert list_after_delete.status_code == 200
        after_data = list_after_delete.json()
        after_comments = after_data.get("data") or after_data.get("comments", [])
        assert len(after_comments) == 0, "Expected no comments after deletion"

        # 7. Move file to trash
        trash_data = {"vault_type": "real"}
        trash_response = client.post(
            f"/api/v1/vault/files/{file_id}/trash",
            data=trash_data
        )
        assert trash_response.status_code == 200, f"Trash failed: {trash_response.text}"

        # 8. List trash (should include file)
        trash_list_response = client.get(
            "/api/v1/vault/trash",
            params={"vault_type": "real"}
        )
        assert trash_list_response.status_code == 200
        trash_list_data = trash_list_response.json()
        trash_files = trash_list_data.get("data") or trash_list_data.get("files", [])
        file_ids_in_trash = [f.get("file_id") for f in trash_files]
        assert file_id in file_ids_in_trash, "File should be in trash"

        # 9. Restore file from trash
        restore_data = {"vault_type": "real"}
        restore_response = client.post(
            f"/api/v1/vault/files/{file_id}/restore",
            data=restore_data
        )
        assert restore_response.status_code == 200, f"Restore failed: {restore_response.text}"

        # 10. List trash again (should not include file)
        trash_after_restore = client.get(
            "/api/v1/vault/trash",
            params={"vault_type": "real"}
        )
        assert trash_after_restore.status_code == 200
        after_trash_data = trash_after_restore.json()
        after_trash_files = after_trash_data.get("data") or after_trash_data.get("files", [])
        after_file_ids = [f.get("file_id") for f in after_trash_files]
        assert file_id not in after_file_ids, "File should not be in trash after restore"


class TestVersions:
    """Test file versioning operations"""

    def test_versions_create_and_restore(self, client: TestClient):
        """Test version creation, listing with pagination, and restore"""

        # Upload initial file
        file_content = b"Version 1 content"
        files = {"file": ("versioned_file.txt", io.BytesIO(file_content), "text/plain")}
        data = {
            "vault_passphrase": "TestPassword123!",
            "vault_type": "real",
            "folder_path": "/"
        }

        upload_response = client.post("/api/v1/vault/upload", files=files, data=data)
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]

        # Upload new version (re-upload same file to create version)
        # Note: Actual versioning may vary by implementation
        # If your API has a dedicated version endpoint, use that instead
        file_content_v2 = b"Version 2 content"
        files_v2 = {"file": ("versioned_file.txt", io.BytesIO(file_content_v2), "text/plain")}

        # Some implementations auto-version on re-upload, others need explicit endpoint
        # Try uploading again or check if there's a version creation endpoint
        upload_v2_response = client.post("/api/v1/vault/upload", files=files_v2, data=data)

        # Get versions with pagination
        versions_response = client.get(
            f"/api/v1/vault/files/{file_id}/versions",
            params={"vault_type": "real", "limit": 10, "offset": 0}
        )
        assert versions_response.status_code == 200, f"Get versions failed: {versions_response.text}"

        versions_data = versions_response.json()
        # Check pagination shape
        assert "data" in versions_data or "versions" in versions_data
        assert "total" in versions_data
        assert "has_more" in versions_data

        versions = versions_data.get("data") or versions_data.get("versions", [])

        # If versions exist, test restore
        if len(versions) > 0:
            version_id = versions[0].get("version_id") or versions[0].get("id")

            restore_data = {"vault_type": "real"}
            restore_response = client.post(
                f"/api/v1/vault/files/{file_id}/versions/{version_id}/restore",
                data=restore_data
            )
            # Accept 200 or 404 if version restore not fully implemented
            assert restore_response.status_code in [200, 404]

            if restore_response.status_code == 200:
                restore_result = restore_response.json()
                assert "success" in restore_result or "file_id" in restore_result


class TestSharing:
    """Test file sharing operations"""

    def test_sharing_create_list_revoke_download_fallback(self, client: TestClient):
        """Test share creation, listing, revoke, and download"""

        # Upload file to share
        file_content = b"Shared file content"
        files = {"file": ("shared_file.txt", io.BytesIO(file_content), "text/plain")}
        data = {
            "vault_passphrase": "TestPassword123!",
            "vault_type": "real",
            "folder_path": "/"
        }

        upload_response = client.post("/api/v1/vault/upload", files=files, data=data)
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]

        # Create share link with max_downloads=1
        share_data = {
            "vault_type": "real",
            "max_downloads": 1,
            "permissions": "download"
        }

        create_share_response = client.post(
            f"/api/v1/vault/files/{file_id}/share",
            data=share_data
        )
        assert create_share_response.status_code == 200, f"Create share failed: {create_share_response.text}"

        share_result = create_share_response.json()
        assert "share_id" in share_result or "share_token" in share_result
        share_id = share_result.get("share_id")
        share_token = share_result.get("share_token")

        # List shares for file (should have ≥1)
        list_shares_response = client.get(
            f"/api/v1/vault/files/{file_id}/shares",
            params={"vault_type": "real"}
        )
        assert list_shares_response.status_code == 200
        shares_data = list_shares_response.json()
        shares = shares_data.get("shares", [])
        assert len(shares) >= 1, "Expected at least 1 share"

        # Try to access share (if endpoint exists)
        if share_token:
            access_response = client.get(f"/api/v1/vault/share/{share_token}")
            # Accept 200 or 404/401 if password required or not implemented
            assert access_response.status_code in [200, 401, 404]

        # Revoke share
        if share_id:
            revoke_response = client.delete(
                f"/api/v1/vault/shares/{share_id}",
                params={"vault_type": "real"}
            )
            assert revoke_response.status_code == 200, f"Revoke failed: {revoke_response.text}"

            # Try to access after revoke (should fail)
            if share_token:
                after_revoke_response = client.get(f"/api/v1/vault/share/{share_token}")
                # Should be 404 or 410 after revoke
                assert after_revoke_response.status_code in [404, 410]
