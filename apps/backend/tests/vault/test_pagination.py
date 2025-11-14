"""
Pagination Tests for Vault Endpoints

Tests limit/offset pagination contract for endpoints that support it:
- Comments
- Versions
- Trash files
- Search results

Verifies response shape: data, total, limit, offset, has_more
"""

import io
import pytest
from fastapi.testclient import TestClient


class TestCommentsPagination:
    """Test pagination for comments endpoint"""

    @pytest.fixture
    def file_with_many_comments(self, client: TestClient):
        """Create a file with 15 comments for pagination testing"""

        # Upload file
        file_content = b"File for comment pagination"
        files = {"file": ("comment_test.txt", io.BytesIO(file_content), "text/plain")}
        upload_data = {
            "vault_passphrase": "TestPassword123!",
            "vault_type": "real",
            "folder_path": "/"
        }

        upload_response = client.post("/api/v1/vault/upload", files=files, data=upload_data)
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]

        # Add 15 comments
        for i in range(15):
            comment_data = {
                "comment_text": f"Comment {i+1}",
                "vault_type": "real"
            }
            client.post(f"/api/v1/vault/files/{file_id}/comments", data=comment_data)

        yield file_id

    def test_comments_pagination(self, client: TestClient, file_with_many_comments):
        """Test comments pagination with limit/offset"""

        file_id = file_with_many_comments

        # First page: limit=10, offset=0
        page1_response = client.get(
            f"/api/v1/vault/files/{file_id}/comments",
            params={"vault_type": "real", "limit": 10, "offset": 0}
        )
        assert page1_response.status_code == 200

        page1_data = page1_response.json()

        # Verify pagination contract
        assert "data" in page1_data or "comments" in page1_data
        assert "total" in page1_data
        assert "limit" in page1_data
        assert "offset" in page1_data
        assert "has_more" in page1_data

        comments_page1 = page1_data.get("data") or page1_data.get("comments", [])
        total = page1_data["total"]

        # Should have 10 comments (or total if less)
        expected_count = min(10, total)
        assert len(comments_page1) == expected_count

        # has_more should be true if total > 10
        if total > 10:
            assert page1_data["has_more"] is True

        # Second page: limit=10, offset=10
        page2_response = client.get(
            f"/api/v1/vault/files/{file_id}/comments",
            params={"vault_type": "real", "limit": 10, "offset": 10}
        )
        assert page2_response.status_code == 200

        page2_data = page2_response.json()
        comments_page2 = page2_data.get("data") or page2_data.get("comments", [])

        # Should have remaining comments
        remaining = max(0, total - 10)
        assert len(comments_page2) == remaining


class TestVersionsPagination:
    """Test pagination for versions endpoint"""

    def test_versions_pagination_shape(self, client: TestClient):
        """Test versions endpoint returns correct pagination shape"""

        # Upload a file
        file_content = b"File for version pagination"
        files = {"file": ("version_test.txt", io.BytesIO(file_content), "text/plain")}
        upload_data = {
            "vault_passphrase": "TestPassword123!",
            "vault_type": "real",
            "folder_path": "/"
        }

        upload_response = client.post("/api/v1/vault/upload", files=files, data=upload_data)
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]

        # Get versions with pagination params
        versions_response = client.get(
            f"/api/v1/vault/files/{file_id}/versions",
            params={"vault_type": "real", "limit": 10, "offset": 0}
        )
        assert versions_response.status_code == 200

        versions_data = versions_response.json()

        # Verify pagination contract
        assert "data" in versions_data or "versions" in versions_data
        assert "total" in versions_data
        assert "has_more" in versions_data

        # Verify types
        versions = versions_data.get("data") or versions_data.get("versions", [])
        assert isinstance(versions, list)
        assert isinstance(versions_data["total"], int)
        assert isinstance(versions_data["has_more"], bool)


class TestTrashPagination:
    """Test pagination for trash endpoint"""

    @pytest.fixture
    def many_trashed_files(self, client: TestClient):
        """Create and trash 12 files"""

        file_ids = []

        for i in range(12):
            file_content = f"Trash test file {i+1}".encode()
            files = {"file": (f"trash_{i}.txt", io.BytesIO(file_content), "text/plain")}
            upload_data = {
                "vault_passphrase": "TestPassword123!",
                "vault_type": "real",
                "folder_path": "/"
            }

            upload_response = client.post("/api/v1/vault/upload", files=files, data=upload_data)
            if upload_response.status_code == 200:
                file_id = upload_response.json()["file_id"]
                file_ids.append(file_id)

                # Trash the file
                trash_data = {"vault_type": "real"}
                client.post(f"/api/v1/vault/files/{file_id}/trash", data=trash_data)

        yield file_ids

    def test_trash_pagination(self, client: TestClient, many_trashed_files):
        """Test trash listing with pagination"""

        # First page: limit=10, offset=0
        page1_response = client.get(
            "/api/v1/vault/trash",
            params={"vault_type": "real", "limit": 10, "offset": 0}
        )
        assert page1_response.status_code == 200

        page1_data = page1_response.json()

        # Verify pagination contract
        assert "data" in page1_data or "files" in page1_data
        assert "total" in page1_data
        assert "limit" in page1_data
        assert "offset" in page1_data
        assert "has_more" in page1_data

        trash_page1 = page1_data.get("data") or page1_data.get("files", [])
        total = page1_data["total"]

        # Should have up to 10 files
        assert len(trash_page1) <= 10

        # has_more should reflect if there are more results
        if total > 10:
            assert page1_data["has_more"] is True


class TestSearchPagination:
    """Test pagination for search endpoint"""

    def test_search_pagination_shape(self, client: TestClient):
        """Test search endpoint returns correct pagination shape"""

        # Search with pagination params
        search_response = client.get(
            "/api/v1/vault/search",
            params={
                "vault_type": "real",
                "query": "test",
                "limit": 10,
                "offset": 0
            }
        )
        assert search_response.status_code == 200

        search_data = search_response.json()

        # Verify pagination contract
        assert "results" in search_data or "data" in search_data
        assert "total" in search_data
        assert "limit" in search_data
        assert "offset" in search_data
        assert "has_more" in search_data

        # Verify types
        results = search_data.get("results") or search_data.get("data", [])
        assert isinstance(results, list)
        assert isinstance(search_data["total"], int)
        assert isinstance(search_data["has_more"], bool)
