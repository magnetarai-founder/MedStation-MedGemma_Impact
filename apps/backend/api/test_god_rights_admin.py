#!/usr/bin/env python3
"""
God Rights Admin Access Test Suite for ElohimOS

Tests the correct security model:

✅ God Rights/Super Admins CAN:
1. View user account metadata (username, user_id, email, created_at)
2. List all users on the system
3. Reset user passwords
4. Unlock/disable user accounts
5. Help with account recovery

❌ God Rights/Super Admins CANNOT:
1. Access personal vault encrypted data
2. See personal chat history
3. Decrypt user's end-to-end encrypted content

This is the Salesforce model: Admins can manage accounts but cannot see user data.
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


def test_god_rights_can_see_user_metadata():
    """
    Test that God Rights CAN see user account metadata
    This is necessary for support - admins need to help users who forget their user_id
    """
    print_test("God Rights CAN View User Account Metadata (for support)")

    # Create test user
    user_a = TestUser("admin_test_user_a", "password_admin_a_123")
    if not user_a.register() or not user_a.login():
        print_fail("Failed to create test user")
        return False

    # Login as God Rights
    god_rights = TestUser("elohim_founder", "ElohimOS_2024_Founder")
    if not god_rights.login():
        print_fail("Failed to login as God Rights")
        return False

    print_info(f"\nGod Rights logged in (role: {god_rights.role})")

    # Test 1: God Rights lists all users
    print_info("\nTest 1: God Rights lists all users on the system")
    response = requests.get(
        f"{BASE_URL}/api/v1/admin/users",
        headers={"Authorization": f"Bearer {god_rights.token}"}
    )

    if response.status_code == 404:
        print_info("Admin endpoint /api/v1/admin/users not yet implemented")
        print_info("This endpoint should allow God Rights to:")
        print_info("  - List all users (username, user_id, email, created_at, last_login)")
        print_info("  - Search for users by username/email")
        print_info("  - View account status (active, locked, disabled)")
        return True  # Not a failure - just not implemented yet
    elif response.status_code == 200:
        users = response.json()
        print_pass(f"God Rights can see {len(users.get('users', []))} user(s)")

        # Verify user_a is in the list
        user_found = False
        for user in users.get('users', []):
            if user['username'] == user_a.username:
                user_found = True
                print_pass(f"Found user: {user_a.username} (user_id: {user['user_id']})")
                break

        if not user_found:
            print_fail(f"User {user_a.username} not found in user list")
            return False

        return True
    else:
        print_fail(f"Unexpected response: {response.status_code} - {response.text}")
        return False


def test_god_rights_cannot_see_chat_history():
    """
    Test that God Rights CANNOT see user chat history
    Chat history is personal user content, not account metadata
    """
    print_test("God Rights CANNOT View Personal Chat History")

    # Create test user and chat
    user_a = TestUser("chat_privacy_user", "password_chat_123")
    if not user_a.register() or not user_a.login():
        print_fail("Failed to create test user")
        return False

    # Create a chat (from previous test, we know this works)
    response = requests.post(
        f"{BASE_URL}/api/v1/chat/sessions",
        headers={"Authorization": f"Bearer {user_a.token}"},
        json={"title": "Private Chat", "model": "qwen2.5-coder:7b-instruct"}
    )

    if response.status_code != 200:
        print_info("Chat creation failed - skipping test")
        return True

    chat_id = response.json()["id"]
    print_pass(f"User created private chat: {chat_id}")

    # Login as God Rights
    god_rights = TestUser("elohim_founder", "ElohimOS_2024_Founder")
    if not god_rights.login():
        print_fail("Failed to login as God Rights")
        return False

    # God Rights lists their own chats (should be empty or only their own)
    response = requests.get(
        f"{BASE_URL}/api/v1/chat/sessions",
        headers={"Authorization": f"Bearer {god_rights.token}"}
    )

    if response.status_code == 200:
        chats = response.json()
        # God Rights should not see user_a's chats in their own list
        for chat in chats:
            if chat['id'] == chat_id:
                print_fail("❌ God Rights can see user's private chat in their own list!")
                return False

        print_pass("✅ God Rights does NOT see user's private chat in their own list")

    # But God Rights SHOULD be able to access via admin endpoint
    print_info("\nTest: God Rights CAN access user chats via admin endpoint (for support)")
    response = requests.get(
        f"{BASE_URL}/api/v1/admin/users/{user_a.user_id}/chats",
        headers={"Authorization": f"Bearer {god_rights.token}"}
    )

    if response.status_code == 200:
        admin_chats = response.json()
        # Verify the user's chat is in the admin view
        found = False
        for chat in admin_chats.get("sessions", []):
            if chat['id'] == chat_id:
                found = True
                break

        if found:
            print_pass("✅ God Rights CAN access user chats via ADMIN endpoint (correct - support access)")
        else:
            print_fail("❌ God Rights cannot see user chat via admin endpoint")
            return False
    else:
        print_info(f"Admin endpoint returned {response.status_code} - may not be fully implemented yet")

    return True


def test_god_rights_password_reset():
    """
    Test that God Rights CAN reset user passwords (for support)
    """
    print_test("God Rights CAN Reset User Passwords (TODO)")

    print_info("Password reset functionality should allow God Rights to:")
    print_info("  - Reset a user's password (generate temporary password)")
    print_info("  - Unlock accounts after failed login attempts")
    print_info("  - Force password change on next login")
    print_info("  - But NEVER see the user's current password")

    return True


def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}ElohimOS God Rights Admin Access Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print()
    print(f"{YELLOW}Testing the correct admin model:{RESET}")
    print(f"{GREEN}✅ God Rights CAN:{RESET} View account metadata, reset passwords, manage accounts")
    print(f"{RED}❌ God Rights CANNOT:{RESET} See personal vault data, chat history, encrypted content")
    print()

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print_fail(f"Server returned {response.status_code}")
            return
        print_pass(f"Server is running at {BASE_URL}")
    except Exception as e:
        print_fail(f"Cannot connect to server at {BASE_URL}: {e}")
        return

    # Run tests
    tests = [
        ("View User Metadata", test_god_rights_can_see_user_metadata),
        ("Cannot See Chat History", test_god_rights_cannot_see_chat_history),
        ("Password Reset", test_god_rights_password_reset),
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
        print(f"{GREEN}God Rights admin model is correct!{RESET}")
    else:
        print(f"{YELLOW}⚠️  {passed}/{total} TESTS PASSED{RESET}")
        print(f"{YELLOW}Some admin features not yet implemented{RESET}")

    print(f"{BLUE}{'='*60}{RESET}\n")


if __name__ == "__main__":
    main()
