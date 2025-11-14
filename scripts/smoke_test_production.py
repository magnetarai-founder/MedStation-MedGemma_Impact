#!/usr/bin/env python3
"""
ElohimOS Production Smoke Test

Quick validation of critical functionality after deployment.
Tests vault operations, auth flows, and system health.

Usage:
    python3 scripts/smoke_test_production.py [--host http://localhost:8000]
"""

import requests
import sys
import os
import time
import argparse
from typing import Dict, Optional

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

class SmokeTest:
    def __init__(self, host: str, founder_password: str):
        self.host = host.rstrip('/')
        self.founder_password = founder_password
        self.token: Optional[str] = None
        self.file_id: Optional[str] = None
        self.share_id: Optional[str] = None
        self.share_token: Optional[str] = None
        self.comment_id: Optional[str] = None

    def run(self) -> bool:
        """Run all smoke tests"""
        print("\n" + "="*80)
        print("ElohimOS Production Smoke Test - v1.0.0-rc1")
        print("="*80 + "\n")

        tests = [
            ("Health Check", self.test_health),
            ("Authentication", self.test_auth),
            ("File Upload", self.test_upload),
            ("Comment Add", self.test_comment_add),
            ("Comment Update", self.test_comment_update),
            ("Comment Delete", self.test_comment_delete),
            ("Share Create (One-Time)", self.test_share_create),
            ("Share Access", self.test_share_access),
            ("Share Revoke", self.test_share_revoke),
            ("Trash Operations", self.test_trash),
            ("Search", self.test_search),
            ("Analytics", self.test_analytics),
        ]

        passed = 0
        failed = 0

        for name, test_func in tests:
            print_info(f"Running: {name}")
            try:
                test_func()
                print_success(f"{name} passed")
                passed += 1
            except AssertionError as e:
                print_error(f"{name} failed: {e}")
                failed += 1
            except Exception as e:
                print_error(f"{name} error: {e}")
                failed += 1
            print()

        print("="*80)
        print(f"Results: {passed} passed, {failed} failed")
        print("="*80 + "\n")

        return failed == 0

    def test_health(self):
        """Test health endpoint"""
        response = requests.get(f"{self.host}/health", timeout=5)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"

        data = response.json()
        assert data.get("status") in ["healthy", "ok"], f"Unhealthy status: {data}"
        print_info(f"  Status: {data.get('status')}")

    def test_auth(self):
        """Test authentication"""
        response = requests.post(
            f"{self.host}/api/v1/auth/login",
            data={
                "username": "elohim_founder",
                "password": self.founder_password
            },
            timeout=5
        )

        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"

        data = response.json()
        assert "token" in data, "No token in response"

        self.token = data["token"]
        print_info(f"  Token: {self.token[:20]}...")

    def test_upload(self):
        """Test file upload"""
        assert self.token, "No auth token"

        # Create temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("ElohimOS smoke test file\n")
            temp_file = f.name

        try:
            with open(temp_file, 'rb') as f:
                response = requests.post(
                    f"{self.host}/api/v1/vault/upload",
                    headers={"Authorization": f"Bearer {self.token}"},
                    files={"file": ("smoke_test.txt", f, "text/plain")},
                    data={
                        "vault_passphrase": "SmokeTest123!",
                        "vault_type": "real",
                        "folder_path": "/"
                    },
                    timeout=10
                )

            assert response.status_code == 200, f"Upload failed: {response.status_code} - {response.text}"

            data = response.json()
            assert "file_id" in data, "No file_id in response"

            self.file_id = data["file_id"]
            print_info(f"  File ID: {self.file_id}")

        finally:
            os.unlink(temp_file)

    def test_comment_add(self):
        """Test adding comment"""
        assert self.token and self.file_id, "No token or file_id"

        response = requests.post(
            f"{self.host}/api/v1/vault/files/{self.file_id}/comments",
            headers={"Authorization": f"Bearer {self.token}"},
            data={
                "comment_text": "Smoke test comment",
                "vault_type": "real"
            },
            timeout=5
        )

        assert response.status_code == 200, f"Add comment failed: {response.status_code}"

        data = response.json()
        assert "comment_id" in data, "No comment_id in response"

        self.comment_id = data["comment_id"]
        print_info(f"  Comment ID: {self.comment_id}")

    def test_comment_update(self):
        """Test updating comment"""
        assert self.token and self.comment_id, "No token or comment_id"

        response = requests.put(
            f"{self.host}/api/v1/vault/comments/{self.comment_id}",
            headers={"Authorization": f"Bearer {self.token}"},
            data={
                "comment_text": "Updated smoke test comment",
                "vault_type": "real"
            },
            timeout=5
        )

        assert response.status_code == 200, f"Update comment failed: {response.status_code}"

    def test_comment_delete(self):
        """Test deleting comment"""
        assert self.token and self.comment_id, "No token or comment_id"

        response = requests.delete(
            f"{self.host}/api/v1/vault/comments/{self.comment_id}",
            headers={"Authorization": f"Bearer {self.token}"},
            params={"vault_type": "real"},
            timeout=5
        )

        assert response.status_code == 200, f"Delete comment failed: {response.status_code}"

    def test_share_create(self):
        """Test creating one-time share link"""
        assert self.token and self.file_id, "No token or file_id"

        response = requests.post(
            f"{self.host}/api/v1/vault/files/{self.file_id}/share",
            headers={"Authorization": f"Bearer {self.token}"},
            data={
                "vault_type": "real",
                "one_time": "true",  # One-time link
                "permissions": "download"
            },
            timeout=5
        )

        assert response.status_code == 200, f"Create share failed: {response.status_code}"

        data = response.json()
        assert "id" in data or "share_id" in data, "No share_id in response"
        assert "share_token" in data, "No share_token in response"

        self.share_id = data.get("id") or data.get("share_id")
        self.share_token = data["share_token"]
        print_info(f"  Share ID: {self.share_id}")
        print_info(f"  Share Token: {self.share_token[:10]}...")

    def test_share_access(self):
        """Test accessing share link"""
        assert self.share_token, "No share_token"

        response = requests.get(
            f"{self.host}/api/v1/vault/share/{self.share_token}",
            timeout=5
        )

        assert response.status_code == 200, f"Share access failed: {response.status_code}"

        data = response.json()
        assert "file_id" in data, "No file_id in share response"
        print_info(f"  Accessed file: {data['file_id']}")

    def test_share_revoke(self):
        """Test revoking share link"""
        assert self.token and self.share_id, "No token or share_id"

        response = requests.delete(
            f"{self.host}/api/v1/vault/shares/{self.share_id}",
            headers={"Authorization": f"Bearer {self.token}"},
            params={"vault_type": "real"},
            timeout=5
        )

        assert response.status_code == 200, f"Revoke share failed: {response.status_code}"

        # Verify share no longer accessible
        response = requests.get(
            f"{self.host}/api/v1/vault/share/{self.share_token}",
            timeout=5
        )
        assert response.status_code in [404, 410], "Share should be revoked"

    def test_trash(self):
        """Test trash operations"""
        assert self.token and self.file_id, "No token or file_id"

        # Move to trash
        response = requests.post(
            f"{self.host}/api/v1/vault/files/{self.file_id}/trash",
            headers={"Authorization": f"Bearer {self.token}"},
            data={"vault_type": "real"},
            timeout=5
        )
        assert response.status_code == 200, f"Move to trash failed: {response.status_code}"

        # List trash
        response = requests.get(
            f"{self.host}/api/v1/vault/trash",
            headers={"Authorization": f"Bearer {self.token}"},
            params={"vault_type": "real"},
            timeout=5
        )
        assert response.status_code == 200, f"List trash failed: {response.status_code}"

        # Restore
        response = requests.post(
            f"{self.host}/api/v1/vault/files/{self.file_id}/restore",
            headers={"Authorization": f"Bearer {self.token}"},
            data={"vault_type": "real"},
            timeout=5
        )
        assert response.status_code == 200, f"Restore failed: {response.status_code}"

        # Clean up - move back to trash and empty
        requests.post(
            f"{self.host}/api/v1/vault/files/{self.file_id}/trash",
            headers={"Authorization": f"Bearer {self.token}"},
            data={"vault_type": "real"}
        )

    def test_search(self):
        """Test search functionality"""
        assert self.token, "No token"

        response = requests.get(
            f"{self.host}/api/v1/vault/search",
            headers={"Authorization": f"Bearer {self.token}"},
            params={
                "vault_type": "real",
                "query": "smoke",
                "limit": 10
            },
            timeout=5
        )

        assert response.status_code == 200, f"Search failed: {response.status_code}"

        data = response.json()
        assert "results" in data or "data" in data, "No results in search response"
        print_info(f"  Found {data.get('total', 0)} results")

    def test_analytics(self):
        """Test analytics endpoints"""
        assert self.token, "No token"

        endpoints = [
            "/api/v1/vault/analytics/storage-trends",
            "/api/v1/vault/analytics/access-patterns",
            "/api/v1/vault/analytics/activity-timeline"
        ]

        for endpoint in endpoints:
            response = requests.get(
                f"{self.host}{endpoint}",
                headers={"Authorization": f"Bearer {self.token}"},
                params={"vault_type": "real", "days": 30},
                timeout=10
            )
            assert response.status_code == 200, f"Analytics {endpoint} failed: {response.status_code}"


def main():
    parser = argparse.ArgumentParser(description="ElohimOS Production Smoke Test")
    parser.add_argument("--host", default="http://localhost:8000", help="API host")
    parser.add_argument("--password", help="Founder password (or set ELOHIM_FOUNDER_PASSWORD)")
    args = parser.parse_args()

    # Get founder password
    password = args.password or os.getenv("ELOHIM_FOUNDER_PASSWORD")
    if not password:
        print_error("Founder password required. Set --password or ELOHIM_FOUNDER_PASSWORD env var")
        sys.exit(1)

    # Run tests
    tester = SmokeTest(args.host, password)
    success = tester.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
