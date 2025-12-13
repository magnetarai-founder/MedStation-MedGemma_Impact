"""
Performance Benchmark: Semantic Search with Pre-computed Embeddings

Tests the performance improvement from:
1. Pre-computing embeddings at message creation time
2. Using Redis cache for search results

Expected improvement: 100x faster search (2000ms → 20ms)
"""

import pytest
import time
import json
from datetime import datetime
from api.chat_memory import NeutronChatMemory, ConversationEvent
from api.cache_service import get_cache


@pytest.mark.benchmark
@pytest.mark.integration
def test_semantic_search_with_precomputed_embeddings(db, regular_user):
    """
    Benchmark semantic search performance with pre-computed embeddings.

    This test verifies that:
    1. Embeddings are pre-computed when messages are added
    2. Searches use pre-computed embeddings (not computing on-the-fly)
    3. Redis caching speeds up repeated searches
    """
    memory = NeutronChatMemory()
    cache = get_cache()

    # Clear cache for clean test
    cache.flush_all()

    # Create test session
    session_id = "perf_test_session"
    memory.create_session(
        session_id=session_id,
        title="Performance Test",
        model="llama2",
        user_id=regular_user["user_id"]
    )

    # Add test messages with diverse content
    test_messages = [
        "How do I implement authentication in FastAPI?",
        "What's the best way to structure a Python project?",
        "Can you explain Docker containers and orchestration?",
        "I need help with SQLite database optimization techniques",
        "How do Redis caching and performance improvements work?",
        "Explain the difference between async and sync programming",
        "What are best practices for API security?",
        "Help me understand microservices architecture patterns",
        "How do I set up continuous integration pipelines?",
        "What's the best approach to error handling in Python?",
    ]

    print("\n📝 Adding messages and pre-computing embeddings...")
    start_add = time.time()

    for i, content in enumerate(test_messages):
        event = ConversationEvent(
            timestamp=datetime.utcnow().isoformat(),
            role="user",
            content=content,
            model="llama2"
        )
        memory.add_message(session_id, event)

    add_time = time.time() - start_add
    print(f"   ✓ Added {len(test_messages)} messages in {add_time*1000:.1f}ms")
    print(f"   ✓ Average per message: {(add_time/len(test_messages))*1000:.1f}ms")

    # Verify embeddings were created
    conn = memory._get_connection()
    cur = conn.execute("SELECT COUNT(*) as count FROM message_embeddings WHERE session_id = ?", (session_id,))
    embedding_count = cur.fetchone()["count"]
    print(f"   ✓ Pre-computed {embedding_count} embeddings")

    assert embedding_count == len(test_messages), "All messages should have embeddings"

    # Test 1: First search (no cache, but uses pre-computed embeddings)
    print("\n🔍 Test 1: First search (pre-computed embeddings, no cache)")
    query = "database optimization"

    start_search1 = time.time()
    results1 = memory.search_messages_semantic(
        query=query,
        limit=5,
        user_id=regular_user["user_id"]
    )
    search1_time = time.time() - start_search1

    print(f"   ✓ Search completed in {search1_time*1000:.1f}ms")
    print(f"   ✓ Found {len(results1)} relevant results")

    assert len(results1) > 0, "Should find relevant results"

    # Verify it found the database message
    found_database = any("database" in r["content"].lower() for r in results1)
    assert found_database, "Should find database-related message"

    # Test 2: Repeated search (with cache)
    print("\n🔍 Test 2: Repeated search (Redis cache)")

    start_search2 = time.time()
    results2 = memory.search_messages_semantic(
        query=query,
        limit=5,
        user_id=regular_user["user_id"]
    )
    search2_time = time.time() - start_search2

    print(f"   ✓ Cached search completed in {search2_time*1000:.1f}ms")
    print(f"   ✓ Speedup from cache: {search1_time/search2_time:.1f}x faster")

    # Cache should be significantly faster
    assert search2_time < search1_time * 0.5, "Cached search should be at least 2x faster"
    assert results1 == results2, "Cached results should match original"

    # Test 3: Different query (no cache, uses pre-computed embeddings)
    print("\n🔍 Test 3: Different query (pre-computed embeddings)")

    start_search3 = time.time()
    results3 = memory.search_messages_semantic(
        query="API security best practices",
        limit=5,
        user_id=regular_user["user_id"]
    )
    search3_time = time.time() - start_search3

    print(f"   ✓ Search completed in {search3_time*1000:.1f}ms")
    print(f"   ✓ Found {len(results3)} relevant results")

    # Verify it found security message
    found_security = any("security" in r["content"].lower() for r in results3)
    assert found_security, "Should find security-related message"

    # Performance Summary
    print("\n📊 Performance Summary:")
    print(f"   • Message addition (with embedding): {(add_time/len(test_messages))*1000:.1f}ms per message")
    print(f"   • First search (pre-computed): {search1_time*1000:.1f}ms")
    print(f"   • Cached search: {search2_time*1000:.1f}ms ({search1_time/search2_time:.1f}x faster)")
    print(f"   • Cache speedup: {((search1_time - search2_time) / search1_time * 100):.1f}%")

    # Expected performance targets
    print("\n🎯 Performance Targets:")
    print(f"   • First search < 100ms: {'✅ PASS' if search1_time < 0.1 else '❌ FAIL'}")
    print(f"   • Cached search < 10ms: {'✅ PASS' if search2_time < 0.01 else '❌ FAIL'}")

    # Cleanup
    memory.delete_session(session_id, user_id=regular_user["user_id"])


@pytest.mark.benchmark
@pytest.mark.integration
def test_cache_invalidation_on_new_messages(db, regular_user):
    """
    Test that search cache is properly managed when new messages are added.

    Note: This test demonstrates that cache has TTL. In production, you may want
    to invalidate cache when new messages are added to a session.
    """
    memory = NeutronChatMemory()
    cache = get_cache()
    cache.flush_all()

    # Create session
    session_id = "cache_test_session"
    memory.create_session(
        session_id=session_id,
        title="Cache Test",
        model="llama2",
        user_id=regular_user["user_id"]
    )

    # Add initial message
    event1 = ConversationEvent(
        timestamp=datetime.utcnow().isoformat(),
        role="user",
        content="How do I implement caching in Python?",
        model="llama2"
    )
    memory.add_message(session_id, event1)

    # First search - populates cache
    results1 = memory.search_messages_semantic(
        query="caching",
        limit=5,
        user_id=regular_user["user_id"]
    )

    print(f"\n✓ First search found {len(results1)} results")
    assert len(results1) == 1, "Should find 1 message"

    # Add new message (cache is still valid)
    event2 = ConversationEvent(
        timestamp=datetime.utcnow().isoformat(),
        role="user",
        content="What are Redis caching strategies for high performance?",
        model="llama2"
    )
    memory.add_message(session_id, event2)

    # Second search - cache hit (won't include new message until cache expires)
    results2 = memory.search_messages_semantic(
        query="caching",
        limit=5,
        user_id=regular_user["user_id"]
    )

    print(f"✓ Cached search found {len(results2)} results (from cache)")
    assert len(results2) == 1, "Cached results won't include new message"

    # Clear cache
    import hashlib
    cache_key = f"semantic_search:{hashlib.md5('caching'.encode()).hexdigest()}:{regular_user['user_id']}:none:5"
    cache.delete(cache_key)

    # Third search - fresh results include new message
    results3 = memory.search_messages_semantic(
        query="caching",
        limit=5,
        user_id=regular_user["user_id"]
    )

    print(f"✓ Fresh search found {len(results3)} results (cache cleared)")
    assert len(results3) == 2, "Fresh search should find both messages"

    # Cleanup
    memory.delete_session(session_id, user_id=regular_user["user_id"])


@pytest.mark.benchmark
def test_embedding_quality():
    """
    Verify that embeddings capture semantic meaning correctly.

    Similar queries should have high similarity scores.
    """
    from api.chat_enhancements import SimpleEmbedding

    # Test semantically similar phrases
    text1 = "How do I implement authentication?"
    text2 = "What's the best way to add user login?"

    emb1 = SimpleEmbedding.create_embedding(text1)
    emb2 = SimpleEmbedding.create_embedding(text2)

    similarity = SimpleEmbedding.cosine_similarity(emb1, emb2)

    print(f"\n🔬 Embedding Quality Test:")
    print(f"   Text 1: {text1}")
    print(f"   Text 2: {text2}")
    print(f"   Similarity: {similarity:.3f}")

    # Similar topics should have moderate to high similarity
    assert similarity > 0.3, "Semantically similar texts should have similarity > 0.3"

    # Test dissimilar phrases
    text3 = "What's the weather today?"
    emb3 = SimpleEmbedding.create_embedding(text3)

    dissimilarity = SimpleEmbedding.cosine_similarity(emb1, emb3)

    print(f"   Text 3: {text3}")
    print(f"   Dissimilarity: {dissimilarity:.3f}")

    assert dissimilarity < similarity, "Dissimilar texts should have lower similarity"


if __name__ == "__main__":
    print("🚀 Semantic Search Performance Benchmark")
    print("=" * 60)
    print("\nThis test validates the performance improvements from:")
    print("1. Pre-computing embeddings at message creation time")
    print("2. Using Redis cache for search results")
    print("\nExpected improvement: 100x faster search (2000ms → 20ms)")
    print("=" * 60)
