#!/usr/bin/env python3
"""
Smoke test for Phase 2.3a Chat Service Refactor

Tests core chat operations to verify the modularization didn't break behavior:
- Session creation
- Session retrieval (by ID and list)
- Message persistence (user/assistant)
- Message history ordering
- Session deletion
"""

import asyncio
from datetime import datetime
from api.services.chat import (
    create_session,
    get_session,
    list_sessions,
    delete_session,
    append_message,
    get_messages,
)


async def main():
    print("=" * 70)
    print("CHAT SERVICE REFACTOR - RUNTIME SMOKE TEST")
    print("=" * 70)

    test_user_id = "chat_user_1"
    test_team_id = None  # Personal session

    print("\n=== 1) Create chat session ===")
    session = await create_session(
        title="Refactor Test Chat",
        model="llama3.2:latest",
        user_id=test_user_id,
        team_id=test_team_id,
    )
    print("Created session:", session)
    chat_id = session["id"]  # chat_memory returns "id" not "chat_id"
    print(f"  chat_id: {chat_id}")
    print(f"  title: {session['title']}")
    print(f"  model: {session['model']}")
    print("✓ Session created successfully")

    print("\n=== 2) Get session by ID ===")
    retrieved_session = await get_session(
        chat_id=chat_id,
        user_id=test_user_id,
        role=None,
        team_id=test_team_id,
    )
    print("Retrieved session:", retrieved_session)
    assert retrieved_session is not None, "Expected to retrieve session"
    assert retrieved_session["id"] == chat_id, f"Expected id {chat_id}"
    print("✓ Session retrieved correctly")

    print("\n=== 3) List user sessions ===")
    sessions = await list_sessions(
        user_id=test_user_id,
        role=None,
        team_id=test_team_id,
    )
    print(f"User sessions ({len(sessions)} total):")
    for s in sessions:
        print(f"  - {s['id']}: {s['title']} (model: {s.get('model', s.get('default_model'))})")

    # Should find our session in the list
    session_ids = [s["id"] for s in sessions]
    assert chat_id in session_ids, f"Expected {chat_id} in session list"
    print("✓ Session appears in user's session list")

    print("\n=== 4) Append user message ===")
    await append_message(
        chat_id=chat_id,
        role="user",
        content="What is the capital of France?",
        timestamp=datetime.utcnow().isoformat(),
        model=None,
        tokens=None,
        files=None,
    )
    print("Appended user message")
    print("✓ User message saved")

    print("\n=== 5) Append assistant message ===")
    await append_message(
        chat_id=chat_id,
        role="assistant",
        content="The capital of France is Paris.",
        timestamp=datetime.utcnow().isoformat(),
        model="llama3.2:latest",
        tokens=15,
        files=None,
    )
    print("Appended assistant message")
    print("✓ Assistant message saved")

    print("\n=== 6) Append another user message ===")
    await append_message(
        chat_id=chat_id,
        role="user",
        content="What is its population?",
        timestamp=datetime.utcnow().isoformat(),
        model=None,
        tokens=None,
        files=None,
    )
    print("Appended second user message")
    print("✓ Second user message saved")

    print("\n=== 7) Get message history ===")
    messages = await get_messages(
        chat_id=chat_id,
        limit=None,
    )
    print(f"Message history ({len(messages)} messages):")
    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        content_preview = content[:50] + "..." if len(content) > 50 else content
        print(f"  {i}. [{role}]: {content_preview}")

    # Verify we have 3 messages
    assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"

    # Verify ordering (user → assistant → user)
    assert messages[0].get("role") == "user", "First message should be user"
    assert messages[1].get("role") == "assistant", "Second message should be assistant"
    assert messages[2].get("role") == "user", "Third message should be user"

    # Verify content
    assert "France" in messages[0].get("content", ""), "First message should mention France"
    assert "Paris" in messages[1].get("content", ""), "Assistant should mention Paris"
    assert "population" in messages[2].get("content", ""), "Third message should mention population"

    print("✓ Message history retrieved correctly")
    print("✓ Message ordering preserved (user → assistant → user)")
    print("✓ Message content verified")

    print("\n=== 8) Delete session ===")
    success = await delete_session(
        chat_id=chat_id,
        user_id=test_user_id,
        role=None,
    )
    print(f"Delete result: {success}")
    assert success == True, f"Expected deletion to succeed"
    print("✓ Session deleted successfully")

    print("\n=== 9) Verify session is gone ===")
    deleted_session = await get_session(
        chat_id=chat_id,
        user_id=test_user_id,
        role=None,
        team_id=test_team_id,
    )
    print(f"Retrieval after deletion: {deleted_session}")
    assert deleted_session is None, "Expected None for deleted session"
    print("✓ Session no longer retrievable after deletion")

    print("\n" + "=" * 70)
    print("ALL SMOKE TESTS PASSED ✓")
    print("=" * 70)
    print("\nConclusion: Chat service refactor appears functionally correct.")
    print("Core operations (session lifecycle, message persistence) work as expected.")
    print("\nPhase 2.3a validation:")
    print("  - sessions.py delegation: ✓ (create, get, list, delete)")
    print("  - storage.py delegation: ✓ (DB operations via NeutronChatMemory)")
    print("  - Message ordering: ✓ (preserved across save/retrieve)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("\n" + "=" * 70)
        print("SMOKE TEST FAILED ✗")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        exit(1)
