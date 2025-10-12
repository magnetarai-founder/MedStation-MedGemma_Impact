#!/usr/bin/env python3
"""
Test script for P2P Team Chat
Run this to verify the libp2p service works
"""

import asyncio
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_p2p_service():
    """Test the P2P chat service"""

    print("=" * 60)
    print("P2P Team Chat - Test Script")
    print("=" * 60)
    print()

    # Check if libp2p is installed
    try:
        import libp2p
        print("✓ libp2p is installed")
    except ImportError:
        print("✗ libp2p is NOT installed")
        print("  Install with: pip install libp2p multiaddr")
        return False

    # Import P2P service
    try:
        from p2p_chat_service import init_p2p_chat_service, get_p2p_chat_service
        from p2p_chat_models import CreateChannelRequest, SendMessageRequest, ChannelType, MessageType
        print("✓ P2P modules imported successfully")
    except Exception as e:
        print(f"✗ Failed to import P2P modules: {e}")
        return False

    print()
    print("=" * 60)
    print("Starting P2P Service Test")
    print("=" * 60)
    print()

    try:
        # Initialize service
        print("1. Initializing P2P service...")
        service = init_p2p_chat_service(
            display_name="Test User",
            device_name="Test MacBook"
        )
        print(f"   ✓ Service created")

        # Start service
        print("2. Starting P2P host...")
        await service.start()
        print(f"   ✓ P2P host started")
        print(f"   Peer ID: {service.peer_id}")

        # Get multiaddrs
        if service.host:
            addrs = [str(addr) for addr in service.host.get_addrs()]
            print(f"   Listening on:")
            for addr in addrs:
                print(f"     - {addr}")

        print()

        # Create a test channel
        print("3. Creating a test channel...")
        channel_request = CreateChannelRequest(
            name="General",
            type=ChannelType.PUBLIC,
            description="General discussion"
        )
        channel = await service.create_channel(channel_request)
        print(f"   ✓ Channel created: {channel.name} ({channel.id})")

        print()

        # List channels
        print("4. Listing channels...")
        channels = await service.list_channels()
        print(f"   ✓ Found {len(channels)} channel(s):")
        for ch in channels:
            print(f"     - {ch.name} ({ch.type.value})")

        print()

        # Send a test message
        print("5. Sending a test message...")
        message_request = SendMessageRequest(
            channel_id=channel.id,
            content="Hello from P2P test!",
            type=MessageType.TEXT
        )
        message = await service.send_message(message_request)
        print(f"   ✓ Message sent: {message.id}")
        print(f"     Content: {message.content}")

        print()

        # Get messages
        print("6. Retrieving messages...")
        messages = await service.get_messages(channel.id, limit=10)
        print(f"   ✓ Found {len(messages)} message(s):")
        for msg in messages:
            print(f"     [{msg.sender_name}]: {msg.content}")

        print()

        # List peers
        print("7. Checking for peers...")
        peers = await service.list_peers()
        print(f"   ✓ Found {len(peers)} peer(s):")
        for peer in peers:
            print(f"     - {peer.display_name} on {peer.device_name} ({peer.status.value})")

        print()
        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        print()
        print("The P2P service is working correctly.")
        print()
        print("Note: To test peer discovery, run this script on")
        print("another device on the same local network.")
        print()

        # Keep service running for a bit to allow peer discovery
        print("Keeping service alive for 10 seconds...")
        print("(Press Ctrl+C to stop earlier)")

        try:
            await asyncio.sleep(10)
        except KeyboardInterrupt:
            print("\nInterrupted by user")

        # Stop service
        print("\nStopping P2P service...")
        await service.stop()
        print("✓ Service stopped")

        return True

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        if service and service.is_running:
            await service.stop()
        return False

    except Exception as e:
        print(f"\n✗ Test failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

        if service and service.is_running:
            await service.stop()

        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_p2p_service())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(1)
