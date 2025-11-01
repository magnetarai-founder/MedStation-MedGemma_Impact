#!/usr/bin/env python3
"""
User Isolation Test Suite

Tests that User A cannot access User B's data, and God Rights can see everything.
"""

import sys
import requests
import json
from typing import Dict

# Base URL
BASE_URL = "http://localhost:8000"

# ANSI colors for pretty output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(name: str):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}TEST: {name}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

def print_pass(msg: str):
    print(f"{GREEN}✓ PASS:{RESET} {msg}")

def print_fail(msg: str):
    print(f"{RED}✗ FAIL:{RESET} {msg}")

def print_info(msg: str):
    print(f"{YELLOW}ℹ INFO:{RESET} {msg}")

class TestUser:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.token = None
        self.user_id = None
        self.role = None
        self.sessions = []

    def register(self):
        """Register user"""
        print_info(f"Registering user: {self.username}")
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "username": self.username,
                "password": self.password,
                "device_name": f"Test Device - {self.username}"
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data["token"]
            self.user_id = data["user"]["user_id"]
            self.role = data["user"].get("role", "member")
            print_pass(f"Registered {self.username} (user_id: {self.user_id}, role: {self.role})")
            return True
        else:
            # Try login instead (user might already exist)
            return self.login()

    def login(self):
        """Login user"""
        print_info(f"Logging in user: {self.username}")
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "username": self.username,
                "password": self.password
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data["token"]
            self.user_id = data["user"]["user_id"]
            self.role = data["user"].get("role", "member")
            print_pass(f"Logged in {self.username} (user_id: {self.user_id}, role: {self.role})")
            return True
        else:
            print_fail(f"Login failed: {response.status_code} - {response.text}")
            return False

    def create_chat(self, title: str):
        """Create a chat session"""
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/sessions",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"title": title, "model": "qwen2.5-coder:7b-instruct"}
        )

        if response.status_code == 200:
            session = response.json()
            self.sessions.append(session["id"])
            print_pass(f"{self.username} created chat: {title} (id: {session['id']})")
            return session["id"]
        else:
            print_fail(f"Create chat failed: {response.status_code} - {response.text}")
            return None

    def list_chats(self):
        """List chat sessions"""
        response = requests.get(
            f"{BASE_URL}/api/v1/chat/sessions",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if response.status_code == 200:
            sessions = response.json()
            print_info(f"{self.username} sees {len(sessions)} chat(s)")
            return sessions
        else:
            print_fail(f"List chats failed: {response.status_code} - {response.text}")
            return []

    def get_chat(self, chat_id: str):
        """Get a specific chat session"""
        response = requests.get(
            f"{BASE_URL}/api/v1/chat/sessions/{chat_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if response.status_code == 200:
            return response.json()
        else:
            return None

    def delete_chat(self, chat_id: str):
        """Delete a chat session"""
        response = requests.delete(
            f"{BASE_URL}/api/v1/chat/sessions/{chat_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        return response.status_code == 200


def test_chat_isolation():
    """Test that users can only see their own chats"""
    print_test("Chat Isolation - Users Cannot See Each Other's Data")

    # Create two test users
    user_a = TestUser("test_user_a", "password_a_123")
    user_b = TestUser("test_user_b", "password_b_456")

    # Register/login both users
    if not user_a.register():
        print_fail("Failed to register User A")
        return False

    if not user_b.register():
        print_fail("Failed to register User B")
        return False

    # User A creates 2 chats
    chat_a1 = user_a.create_chat("User A - Chat 1")
    chat_a2 = user_a.create_chat("User A - Chat 2")

    # User B creates 1 chat
    chat_b1 = user_b.create_chat("User B - Chat 1")

    # Test 1: User A should only see their 2 chats
    print_info("\nTest 1: User A lists their chats")
    user_a_chats = user_a.list_chats()
    if len(user_a_chats) == 2:
        print_pass(f"User A sees exactly 2 chats (correct)")
    else:
        print_fail(f"User A sees {len(user_a_chats)} chats (expected 2)")
        return False

    # Test 2: User B should only see their 1 chat
    print_info("\nTest 2: User B lists their chats")
    user_b_chats = user_b.list_chats()
    if len(user_b_chats) == 1:
        print_pass(f"User B sees exactly 1 chat (correct)")
    else:
        print_fail(f"User B sees {len(user_b_chats)} chats (expected 1)")
        return False

    # Test 3: User B tries to access User A's chat (should fail)
    print_info("\nTest 3: User B attempts to access User A's chat")
    user_b_accessing_a_chat = user_b.get_chat(chat_a1)
    if user_b_accessing_a_chat is None:
        print_pass("User B CANNOT access User A's chat (correct - access denied)")
    else:
        print_fail("User B CAN access User A's chat (SECURITY VIOLATION!)")
        return False

    # Test 4: User A tries to access User B's chat (should fail)
    print_info("\nTest 4: User A attempts to access User B's chat")
    user_a_accessing_b_chat = user_a.get_chat(chat_b1)
    if user_a_accessing_b_chat is None:
        print_pass("User A CANNOT access User B's chat (correct - access denied)")
    else:
        print_fail("User A CAN access User B's chat (SECURITY VIOLATION!)")
        return False

    # Test 5: User B tries to delete User A's chat (should fail)
    print_info("\nTest 5: User B attempts to delete User A's chat")
    deleted = user_b.delete_chat(chat_a1)
    if not deleted:
        print_pass("User B CANNOT delete User A's chat (correct - access denied)")
    else:
        print_fail("User B CAN delete User A's chat (SECURITY VIOLATION!)")
        return False

    # Verify User A's chat still exists
    user_a_chat_still_exists = user_a.get_chat(chat_a1)
    if user_a_chat_still_exists:
        print_pass("User A's chat still exists after User B's delete attempt")
    else:
        print_fail("User A's chat was deleted by User B (SECURITY VIOLATION!)")
        return False

    # Cleanup: Delete test chats
    print_info("\nCleaning up test data...")
    user_a.delete_chat(chat_a1)
    user_a.delete_chat(chat_a2)
    user_b.delete_chat(chat_b1)

    return True


def test_god_rights_access():
    """Test that God Rights can see all users' data"""
    print_test("God Rights Access - Founder Can See All Data")

    # Create test user
    user_a = TestUser("test_user_god", "password_god_123")
    if not user_a.register():
        print_fail("Failed to register test user")
        return False

    # User creates a chat
    chat_a1 = user_a.create_chat("Test Chat for God Rights")

    # Login as God Rights
    god_rights = TestUser("elohim_founder", "ElohimOS_2024_Founder")
    if not god_rights.login():
        print_fail("Failed to login as God Rights")
        return False

    print_info(f"\nGod Rights logged in (role: {god_rights.role})")

    # Test 1: God Rights lists all chats
    print_info("\nTest 1: God Rights lists ALL chats on device")
    god_chats = god_rights.list_chats()
    print_pass(f"God Rights sees {len(god_chats)} total chat(s) across all users")

    # Test 2: God Rights can access any user's chat
    print_info("\nTest 2: God Rights accesses another user's chat")
    god_accessing_user_chat = god_rights.get_chat(chat_a1)
    if god_accessing_user_chat:
        print_pass("God Rights CAN access any user's chat (correct - support access)")
    else:
        print_fail("God Rights CANNOT access user's chat (should be able to)")
        return False

    # Test 3: God Rights can delete any user's chat
    print_info("\nTest 3: God Rights deletes another user's chat")
    deleted = god_rights.delete_chat(chat_a1)
    if deleted:
        print_pass("God Rights CAN delete any user's chat (correct - support access)")
    else:
        print_fail("God Rights CANNOT delete user's chat (should be able to)")
        return False

    # Verify chat is gone
    user_a_chat_exists = user_a.get_chat(chat_a1)
    if not user_a_chat_exists:
        print_pass("Chat was successfully deleted by God Rights")
    else:
        print_fail("Chat still exists after God Rights deletion")
        return False

    return True


def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}ElohimOS User Isolation Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print_fail(f"Server not responding at {BASE_URL}")
            sys.exit(1)
    except Exception as e:
        print_fail(f"Cannot connect to server at {BASE_URL}: {e}")
        print_info("Make sure the backend is running: cd apps/backend && python3 -m uvicorn api.main:app --reload")
        sys.exit(1)

    print_pass(f"Server is running at {BASE_URL}")

    # Run tests
    all_passed = True

    if not test_chat_isolation():
        all_passed = False

    if not test_god_rights_access():
        all_passed = False

    # Final results
    print(f"\n{BLUE}{'='*60}{RESET}")
    if all_passed:
        print(f"{GREEN}✅ ALL TESTS PASSED{RESET}")
        print(f"{GREEN}User isolation is working correctly!{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        sys.exit(0)
    else:
        print(f"{RED}❌ SOME TESTS FAILED{RESET}")
        print(f"{RED}User isolation has security issues!{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
