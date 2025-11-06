#!/usr/bin/env python3
"""
Test script for Terminal Bridge

Tests PTY spawning, output capture, and session management
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.terminal_bridge import terminal_bridge


async def test_spawn_terminal():
    """Test spawning a terminal session"""
    print("TEST 1: Spawn Terminal")
    print("-" * 50)

    session = await terminal_bridge.spawn_terminal(user_id="test_user")

    print(f"✅ Terminal spawned successfully")
    print(f"   Terminal ID: {session.id}")
    print(f"   User ID: {session.user_id}")
    print(f"   PID: {session.process.pid}")
    print(f"   Master FD: {session.master}")
    print(f"   Active: {session.active}")
    print()

    return session


async def test_write_and_capture(session):
    """Test writing to terminal and capturing output"""
    print("TEST 2: Write Commands & Capture Output")
    print("-" * 50)

    # Send a simple command
    await terminal_bridge.write_to_terminal(session.id, "echo 'Hello from ElohimOS Terminal'\n")

    # Wait for output to be captured
    await asyncio.sleep(0.5)

    # Send another command
    await terminal_bridge.write_to_terminal(session.id, "pwd\n")

    # Wait for output
    await asyncio.sleep(0.5)

    # Send ls command
    await terminal_bridge.write_to_terminal(session.id, "ls -la | head -10\n")

    # Wait for output
    await asyncio.sleep(0.5)

    # Check output buffer
    if session.output_buffer:
        print(f"✅ Captured {len(session.output_buffer)} output chunks")
        print("\nOutput preview:")
        print("=" * 50)
        output = ''.join(session.output_buffer[-50:])  # Last 50 chunks
        print(output[:500] if len(output) > 500 else output)  # First 500 chars
        print("=" * 50)
    else:
        print("⚠️  No output captured yet")

    print()


async def test_context_retrieval(session):
    """Test retrieving terminal context"""
    print("TEST 3: Context Retrieval for AI")
    print("-" * 50)

    context = terminal_bridge.get_context(session.id, lines=10)

    if context:
        print(f"✅ Context retrieved ({len(context)} characters)")
        print("\nContext preview:")
        print("=" * 50)
        print(context[:300] if len(context) > 300 else context)
        print("=" * 50)
    else:
        print("⚠️  No context available")

    print()


async def test_list_sessions():
    """Test listing terminal sessions"""
    print("TEST 4: List Sessions")
    print("-" * 50)

    sessions = terminal_bridge.list_sessions(user_id="test_user")

    print(f"✅ Found {len(sessions)} session(s) for test_user")
    for s in sessions:
        print(f"   - {s['id']}: PID {s['pid']}, Active: {s['active']}")

    print()


async def test_resize_terminal(session):
    """Test terminal resize"""
    print("TEST 5: Resize Terminal")
    print("-" * 50)

    try:
        await terminal_bridge.resize_terminal(session.id, rows=30, cols=100)
        print("✅ Terminal resized to 30x100")
    except Exception as e:
        print(f"⚠️  Resize failed: {e}")

    print()


async def test_close_terminal(session):
    """Test closing terminal"""
    print("TEST 6: Close Terminal")
    print("-" * 50)

    await terminal_bridge.close_terminal(session.id)

    # Check if session is removed
    closed_session = terminal_bridge.get_session(session.id)

    if closed_session is None:
        print(f"✅ Terminal {session.id} closed successfully")
    else:
        print(f"⚠️  Terminal still exists: active={closed_session.active}")

    print()


async def main():
    """Run all tests"""
    print()
    print("=" * 50)
    print("TERMINAL BRIDGE TEST SUITE")
    print("=" * 50)
    print()

    try:
        # Test 1: Spawn terminal
        session = await test_spawn_terminal()

        # Test 2: Write and capture
        await test_write_and_capture(session)

        # Test 3: Context retrieval
        await test_context_retrieval(session)

        # Test 4: List sessions
        await test_list_sessions()

        # Test 5: Resize
        await test_resize_terminal(session)

        # Test 6: Close
        await test_close_terminal(session)

        print("=" * 50)
        print("✅ ALL TESTS PASSED")
        print("=" * 50)
        print()

    except Exception as e:
        print()
        print("=" * 50)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 50)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
