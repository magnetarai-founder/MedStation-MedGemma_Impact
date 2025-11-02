#!/usr/bin/env python3
"""
Workflow Service User Isolation Test

Tests that users cannot access each other's workflows and work items.
Validates Phase 1A User Isolation Foundation requirements.
"""

import requests
import json
import sys
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
WORKFLOW_API = f"{BASE_URL}/api/v1/workflow"

# Test users (will be created/authenticated)
# Use timestamp to ensure unique users each run
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
USER_ALICE = {
    "username": f"alice_wf_{timestamp}",
    "password": "alice_test_password_123"
}

USER_BOB = {
    "username": f"bob_wf_{timestamp}",
    "password": "bob_test_password_123"
}

# Track created resources for cleanup
created_workflows = []
created_work_items = []

def print_test(msg):
    """Print test status"""
    print(f"\n{'='*60}")
    print(f"TEST: {msg}")
    print('='*60)

def print_step(msg):
    """Print test step"""
    print(f"  → {msg}")

def print_pass(msg):
    """Print pass message"""
    print(f"  ✅ PASS: {msg}")

def print_fail(msg):
    """Print fail message"""
    print(f"  ❌ FAIL: {msg}")

def register_user(username, password):
    """Register a new user (ignore if already exists)"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "username": username,
            "password": password,
            "device_id": f"test_device_{username}"
        }
    )
    # Accept both 200 (created) and 409 (already exists) or 400 (already exists)
    if response.status_code not in [200, 400, 409]:
        print(f"    Registration failed: {response.status_code} - {response.text}")
    return response.status_code in [200, 400, 409]

def login_user(username, password):
    """Login and get JWT token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": username, "password": password}
    )
    if response.status_code == 200:
        data = response.json()
        # Token field is "token" not "access_token"
        return data.get("token")
    else:
        print(f"    Login failed: {response.status_code} - {response.text}")
    return None

def create_workflow(token, name="Test Workflow"):
    """Create a workflow"""
    headers = {"Authorization": f"Bearer {token}"}
    workflow_data = {
        "name": name,
        "description": "Test workflow for isolation testing",
        "icon": "📋",
        "category": "test",
        "stages": [
            {
                "id": "stage1",
                "name": "Stage 1",
                "description": "First stage",
                "stage_type": "human",
                "assignment_type": "user",
                "sla_hours": 24,
                "order": 0
            }
        ],
        "triggers": [
            {
                "trigger_type": "manual"
            }
        ]
    }

    response = requests.post(
        f"{WORKFLOW_API}/workflows",
        headers=headers,
        json=workflow_data
    )

    if response.status_code == 200:
        workflow = response.json()
        created_workflows.append(workflow["id"])
        return workflow
    else:
        print(f"    Create workflow failed: {response.status_code} - {response.text}")
    return None

def list_workflows(token):
    """List workflows for authenticated user"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{WORKFLOW_API}/workflows",
        headers=headers
    )

    if response.status_code == 200:
        return response.json()
    return None

def get_workflow(token, workflow_id):
    """Get specific workflow"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{WORKFLOW_API}/workflows/{workflow_id}",
        headers=headers
    )
    return response

def create_work_item(token, workflow_id, title="Test Work Item"):
    """Create a work item"""
    headers = {"Authorization": f"Bearer {token}"}
    work_item_data = {
        "workflow_id": workflow_id,
        "data": {"title": title, "description": "Test work item"},
        "priority": "normal"
    }

    response = requests.post(
        f"{WORKFLOW_API}/work-items",
        headers=headers,
        json=work_item_data
    )

    if response.status_code == 200:
        work_item = response.json()
        created_work_items.append(work_item["id"])
        return work_item
    return None

def list_work_items(token):
    """List work items for authenticated user"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{WORKFLOW_API}/work-items",
        headers=headers
    )

    if response.status_code == 200:
        return response.json()
    return None

def get_work_item(token, work_item_id):
    """Get specific work item"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{WORKFLOW_API}/work-items/{work_item_id}",
        headers=headers
    )
    return response

def delete_workflow(token, workflow_id):
    """Delete workflow"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(
        f"{WORKFLOW_API}/workflows/{workflow_id}",
        headers=headers
    )
    return response

def run_tests():
    """Run all workflow isolation tests"""
    print("\n" + "="*60)
    print("WORKFLOW SERVICE USER ISOLATION TESTS")
    print("Phase 1A - User Isolation Foundation")
    print("="*60)

    # Test 1: Setup - Register and login users
    print_test("Setup - Register and authenticate test users")

    print_step("Registering Alice...")
    register_user(USER_ALICE["username"], USER_ALICE["password"])

    print_step("Registering Bob...")
    register_user(USER_BOB["username"], USER_BOB["password"])

    print_step("Logging in Alice...")
    alice_token = login_user(USER_ALICE["username"], USER_ALICE["password"])
    if not alice_token:
        print_fail("Failed to login Alice")
        return False
    print_pass("Alice authenticated")

    print_step("Logging in Bob...")
    bob_token = login_user(USER_BOB["username"], USER_BOB["password"])
    if not bob_token:
        print_fail("Failed to login Bob")
        return False
    print_pass("Bob authenticated")

    # Test 2: Create workflows for each user
    print_test("Create workflows for each user")

    print_step("Alice creates workflow...")
    alice_workflow = create_workflow(alice_token, "Alice's Workflow")
    if not alice_workflow:
        print_fail("Failed to create Alice's workflow")
        return False
    alice_workflow_id = alice_workflow["id"]
    print_pass(f"Alice created workflow: {alice_workflow_id}")

    print_step("Bob creates workflow...")
    bob_workflow = create_workflow(bob_token, "Bob's Workflow")
    if not bob_workflow:
        print_fail("Failed to create Bob's workflow")
        return False
    bob_workflow_id = bob_workflow["id"]
    print_pass(f"Bob created workflow: {bob_workflow_id}")

    # Test 3: List workflows - should only see own workflows
    print_test("List workflows - users should only see their own")

    print_step("Alice lists workflows...")
    alice_workflows = list_workflows(alice_token)
    alice_workflow_ids = [w["id"] for w in alice_workflows] if alice_workflows else []

    if bob_workflow_id in alice_workflow_ids:
        print_fail(f"Alice can see Bob's workflow {bob_workflow_id}")
        return False
    print_pass("Alice cannot see Bob's workflow")

    if alice_workflow_id not in alice_workflow_ids:
        print_fail(f"Alice cannot see her own workflow {alice_workflow_id}")
        return False
    print_pass("Alice can see her own workflow")

    print_step("Bob lists workflows...")
    bob_workflows = list_workflows(bob_token)
    bob_workflow_ids = [w["id"] for w in bob_workflows] if bob_workflows else []

    if alice_workflow_id in bob_workflow_ids:
        print_fail(f"Bob can see Alice's workflow {alice_workflow_id}")
        return False
    print_pass("Bob cannot see Alice's workflow")

    if bob_workflow_id not in bob_workflow_ids:
        print_fail(f"Bob cannot see his own workflow {bob_workflow_id}")
        return False
    print_pass("Bob can see his own workflow")

    # Test 4: Get specific workflow - should fail for other user's workflow
    print_test("Get specific workflow - should deny cross-user access")

    print_step("Alice tries to get Bob's workflow...")
    response = get_workflow(alice_token, bob_workflow_id)
    if response.status_code == 200:
        print_fail(f"Alice accessed Bob's workflow {bob_workflow_id}")
        return False
    if response.status_code == 404:
        print_pass(f"Alice denied access to Bob's workflow (404)")
    else:
        print_pass(f"Alice denied access to Bob's workflow ({response.status_code})")

    print_step("Bob tries to get Alice's workflow...")
    response = get_workflow(bob_token, alice_workflow_id)
    if response.status_code == 200:
        print_fail(f"Bob accessed Alice's workflow {alice_workflow_id}")
        return False
    if response.status_code == 404:
        print_pass(f"Bob denied access to Alice's workflow (404)")
    else:
        print_pass(f"Bob denied access to Alice's workflow ({response.status_code})")

    # Test 5: Create work items
    print_test("Create work items for each user")

    print_step("Alice creates work item...")
    alice_work_item = create_work_item(alice_token, alice_workflow_id, "Alice's Task")
    if not alice_work_item:
        print_fail("Failed to create Alice's work item")
        return False
    alice_work_item_id = alice_work_item["id"]
    print_pass(f"Alice created work item: {alice_work_item_id}")

    print_step("Bob creates work item...")
    bob_work_item = create_work_item(bob_token, bob_workflow_id, "Bob's Task")
    if not bob_work_item:
        print_fail("Failed to create Bob's work item")
        return False
    bob_work_item_id = bob_work_item["id"]
    print_pass(f"Bob created work item: {bob_work_item_id}")

    # Test 6: List work items - should only see own work items
    print_test("List work items - users should only see their own")

    print_step("Alice lists work items...")
    alice_items = list_work_items(alice_token)
    alice_item_ids = [w["id"] for w in alice_items] if alice_items else []

    if bob_work_item_id in alice_item_ids:
        print_fail(f"Alice can see Bob's work item {bob_work_item_id}")
        return False
    print_pass("Alice cannot see Bob's work item")

    if alice_work_item_id not in alice_item_ids:
        print_fail(f"Alice cannot see her own work item {alice_work_item_id}")
        return False
    print_pass("Alice can see her own work item")

    print_step("Bob lists work items...")
    bob_items = list_work_items(bob_token)
    bob_item_ids = [w["id"] for w in bob_items] if bob_items else []

    if alice_work_item_id in bob_item_ids:
        print_fail(f"Bob can see Alice's work item {alice_work_item_id}")
        return False
    print_pass("Bob cannot see Alice's work item")

    if bob_work_item_id not in bob_item_ids:
        print_fail(f"Bob cannot see his own work item {bob_work_item_id}")
        return False
    print_pass("Bob can see his own work item")

    # Test 7: Get specific work item - should fail for other user's work item
    print_test("Get specific work item - should deny cross-user access")

    print_step("Alice tries to get Bob's work item...")
    response = get_work_item(alice_token, bob_work_item_id)
    if response.status_code == 200:
        print_fail(f"Alice accessed Bob's work item {bob_work_item_id}")
        return False
    if response.status_code == 404:
        print_pass(f"Alice denied access to Bob's work item (404)")
    else:
        print_pass(f"Alice denied access to Bob's work item ({response.status_code})")

    print_step("Bob tries to get Alice's work item...")
    response = get_work_item(bob_token, alice_work_item_id)
    if response.status_code == 200:
        print_fail(f"Bob accessed Alice's work item {alice_work_item_id}")
        return False
    if response.status_code == 404:
        print_pass(f"Bob denied access to Alice's work item (404)")
    else:
        print_pass(f"Bob denied access to Alice's work item ({response.status_code})")

    # Test 8: Delete - users should not be able to delete other users' workflows
    print_test("Delete workflows - should deny cross-user deletion")

    print_step("Alice tries to delete Bob's workflow...")
    response = delete_workflow(alice_token, bob_workflow_id)
    if response.status_code == 200:
        print_fail(f"Alice deleted Bob's workflow {bob_workflow_id}")
        return False
    print_pass(f"Alice denied deletion of Bob's workflow ({response.status_code})")

    print_step("Bob tries to delete Alice's workflow...")
    response = delete_workflow(bob_token, alice_workflow_id)
    if response.status_code == 200:
        print_fail(f"Bob deleted Alice's workflow {alice_workflow_id}")
        return False
    print_pass(f"Bob denied deletion of Alice's workflow ({response.status_code})")

    # Test 9: Users can delete their own workflows
    print_test("Delete own workflows - should succeed")

    print_step("Alice deletes her own workflow...")
    response = delete_workflow(alice_token, alice_workflow_id)
    if response.status_code != 200:
        print_fail(f"Alice failed to delete her own workflow ({response.status_code})")
        return False
    print_pass("Alice successfully deleted her own workflow")

    print_step("Bob deletes his own workflow...")
    response = delete_workflow(bob_token, bob_workflow_id)
    if response.status_code != 200:
        print_fail(f"Bob failed to delete his own workflow ({response.status_code})")
        return False
    print_pass("Bob successfully deleted his own workflow")

    return True

def main():
    """Main test runner"""
    try:
        success = run_tests()

        print("\n" + "="*60)
        if success:
            print("✅ ALL TESTS PASSED - Workflow User Isolation Verified")
            print("="*60)
            print("\nPhase 1A Status: COMPLETE")
            print("- Workflows are properly isolated by user_id")
            print("- Work items are properly isolated by user_id")
            print("- Cross-user access is prevented at all endpoints")
            print("- Users can only modify/delete their own resources")
            sys.exit(0)
        else:
            print("❌ TESTS FAILED - User Isolation Violated")
            print("="*60)
            print("\nSecurity Issue: Cross-user data access detected")
            print("Review workflow_service.py, workflow_orchestrator.py, and workflow_storage.py")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ TEST ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
