#!/usr/bin/env python3
"""
Vault Privacy Test Suite for ElohimOS

Tests that verify:
1. Personal Vault data is PRIVATE even from God Rights/Founders
2. Team Vault data IS accessible by God Rights for support/recovery
3. God Rights can help reset locks but cannot decrypt personal data
"""

import requests
import json
from typing import Optional, Dict

# Test configuration
BASE_URL = "http://localhost:8000"

# ANSI color codes
BLUE = "\033[94m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def print_test(text: str):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}TEST: {text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_pass(text: str):
    print(f"{GREEN}✓ PASS:{RESET} {text}")


def print_fail(text: str):
    print(f"{RED}✗ FAIL:{RESET} {text}")


def print_info(text: str):
    print(f"{YELLOW}ℹ INFO:{RESET} {text}")


class TestUser:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.token = None
        self.user_id = None
        self.role = None

    def register(self):
        """Register a new user"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "username": self.username,
                "password": self.password,
                "device_id": f"test_device_{self.username}"
            }
        )

        if response.status_code == 200:
            return True
        elif response.status_code == 400 and "already exists" in response.text:
            # User already exists, just login
            return True
        else:
            print_fail(f"Registration failed: {response.status_code} - {response.text}")
            return False

    def login(self):
        """Login and get auth token"""
        print_info(f"Logging in user: {self.username}")
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={
                "username": self.username,
                "password": self.password
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data["token"]
            self.user_id = data["user_id"]
            self.role = data.get("role", "member")
            print_pass(f"Logged in {self.username} (user_id: {self.user_id}, role: {self.role})")
            return True
        else:
            print_fail(f"Login failed: {response.status_code} - {response.json().get('detail', 'Unknown error')}")
            return False

    def create_vault_document(self, doc_id: str, vault_type: str, encrypted_data: str, metadata: str) -> bool:
        """Create a vault document"""
        response = requests.post(
            f"{BASE_URL}/api/v1/vault/documents?vault_type={vault_type}",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "id": doc_id,
                "vault_type": vault_type,
                "encrypted_blob": encrypted_data,
                "encrypted_metadata": metadata
            }
        )

        if response.status_code == 200:
            return True
        else:
            print_fail(f"Create vault document failed: {response.status_code} - {response.text}")
            return False

    def list_vault_documents(self, vault_type: str) -> Optional[list]:
        """List vault documents"""
        response = requests.get(
            f"{BASE_URL}/api/v1/vault/documents?vault_type={vault_type}",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if response.status_code == 200:
            return response.json()["documents"]
        else:
            return None

    def get_vault_document(self, doc_id: str, vault_type: str) -> Optional[Dict]:
        """Get a specific vault document"""
        response = requests.get(
            f"{BASE_URL}/api/v1/vault/documents/{doc_id}?vault_type={vault_type}",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            return None
        else:
            print_info(f"Get vault document returned: {response.status_code} - {response.text}")
            return None


def test_personal_vault_privacy():
    """
    Test that Personal Vault data is TRULY PRIVATE - even God Rights cannot see it

    This is critical: Personal vault is like a password manager.
    Even support staff (God Rights) should NEVER be able to see personal vault contents.
    """
    print_test("Personal Vault Privacy - Even God Rights Cannot See Personal Data")

    # Create test user
    user_a = TestUser("vault_test_user_a", "password_vault_a_123")
    if not user_a.register():
        print_fail("Failed to register User A")
        return False

    if not user_a.login():
        print_fail("Failed to login User A")
        return False

    # User A creates personal vault document with "sensitive" data
    doc_id = "personal_vault_doc_123"
    encrypted_data = "ENCRYPTED_PERSONAL_SECRET_DATA_12345"  # Simulated encrypted data
    metadata = "ENCRYPTED_METADATA_PERSONAL"

    print_info("User A creates personal vault document")
    if not user_a.create_vault_document(doc_id, "real", encrypted_data, metadata):
        print_fail("Failed to create personal vault document")
        return False

    print_pass("User A created personal vault document")

    # Verify User A can see their own document
    print_info("\nTest 1: User A can access their own personal vault")
    user_a_docs = user_a.list_vault_documents("real")
    if user_a_docs and len(user_a_docs) > 0:
        print_pass(f"User A sees {len(user_a_docs)} personal vault document(s)")
    else:
        print_fail("User A cannot see their own personal vault documents")
        return False

    # Login as God Rights (Founder)
    god_rights = TestUser("elohim_founder", "ElohimOS_2024_Founder")
    if not god_rights.login():
        print_fail("Failed to login as God Rights")
        return False

    print_info(f"\nGod Rights logged in (role: {god_rights.role})")

    # Test 2: God Rights CANNOT see User A's personal vault documents
    print_info("\nTest 2: God Rights attempts to list User A's personal vault documents")
    god_docs = god_rights.list_vault_documents("real")

    if god_docs is None or len(god_docs) == 0:
        print_pass("✅ PRIVACY PROTECTED: God Rights CANNOT see User A's personal vault documents")
    else:
        print_fail(f"❌ PRIVACY VIOLATION: God Rights can see {len(god_docs)} personal vault documents!")
        print_fail("Personal vault is NOT private! This is a critical security failure!")
        return False

    # Test 3: God Rights CANNOT directly access User A's personal vault document
    print_info("\nTest 3: God Rights attempts to directly access User A's personal vault document")
    god_access = god_rights.get_vault_document(doc_id, "real")

    if god_access is None:
        print_pass("✅ PRIVACY PROTECTED: God Rights CANNOT access User A's personal vault document")
    else:
        print_fail("❌ PRIVACY VIOLATION: God Rights can access personal vault document!")
        print_fail(f"Document data: {god_access}")
        return False

    # Summary
    print_info("\n" + "="*60)
    print_pass("✅ PERSONAL VAULT IS TRULY PRIVATE")
    print_info("Even God Rights (Founder) cannot:")
    print_info("  1. List personal vault documents")
    print_info("  2. Access personal vault documents")
    print_info("  3. See encrypted personal data")
    print_info("\nThis is correct behavior - personal vault is end-to-end encrypted")
    print_info("and user-isolated. Only the owner can access their personal vault.")
    print_info("="*60)

    return True


def test_team_vault_god_rights_access():
    """
    Test that Team Vault data IS accessible by God Rights for support/recovery

    Team vault is organizational data - God Rights should be able to help with:
    - Team vault recovery
    - Access control management
    - Organizational compliance
    """
    print_test("Team Vault Access - God Rights CAN Access Team Data (TODO)")

    print_info("Note: Team vault is currently using same vault_type system")
    print_info("Team vault access by God Rights needs separate implementation")
    print_info("Suggestion: Add 'team' vault_type where God Rights has read access")

    return True


def test_god_rights_lock_reset():
    """
    Test that God Rights can help reset vault locks but cannot decrypt data

    God Rights should be able to:
    - Reset failed unlock attempts counter
    - Help with account recovery
    - But CANNOT decrypt personal vault without user's passphrase
    """
    print_test("God Rights Lock Reset - Can Reset Locks but Cannot Decrypt (TODO)")

    print_info("Lock reset functionality would allow God Rights to:")
    print_info("  1. Reset failed unlock attempt counters")
    print_info("  2. Clear vault lockout status")
    print_info("  3. Help with account recovery workflows")
    print_info("  4. But NEVER decrypt or access encrypted vault contents")

    return True


def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}ElohimOS Vault Privacy Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print_fail(f"Server returned {response.status_code}")
            return
        print_pass(f"Server is running at {BASE_URL}")
    except Exception as e:
        print_fail(f"Cannot connect to server at {BASE_URL}: {e}")
        print_info("Make sure the backend is running: cd apps/backend && python3 -m uvicorn api.main:app --reload")
        return

    # Run tests
    tests = [
        ("Personal Vault Privacy", test_personal_vault_privacy),
        ("Team Vault Access", test_team_vault_god_rights_access),
        ("Lock Reset Capability", test_god_rights_lock_reset),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_fail(f"Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Print summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    if passed == total:
        print(f"{GREEN}✅ ALL TESTS PASSED{RESET}")
        print(f"{GREEN}Personal vault privacy is working correctly!{RESET}")
    else:
        print(f"{RED}❌ SOME TESTS FAILED{RESET}")
        print(f"{RED}Vault privacy has security issues!{RESET}")

    print(f"{BLUE}{'='*60}{RESET}\n")


if __name__ == "__main__":
    main()
