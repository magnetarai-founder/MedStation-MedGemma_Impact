"""
Example usage of the SmartCache system for MagnetarCode.

This module demonstrates how to use the intelligent caching system with:
- Basic get/set operations
- Predictive file loading
- Cache warming for workspaces
- Prefetching related content
- Background refresh
- Multiple backends
"""

import asyncio
from pathlib import Path

from api.services.caching import CacheBackend, get_smart_cache


async def example_basic_usage():
    """Basic cache operations."""
    print("\n=== Basic Cache Operations ===")

    # Get cache instance (singleton)
    cache = get_smart_cache()
    await cache.initialize()

    # Set values with TTL
    await cache.set("user:123", {"name": "Alice", "email": "alice@example.com"}, ttl=300)
    await cache.set("user:456", {"name": "Bob", "email": "bob@example.com"}, ttl=300)

    # Get values
    user = await cache.get("user:123")
    print(f"Retrieved user: {user}")

    # Delete entry
    await cache.delete("user:456")

    # Get stats
    stats = cache.get_stats()
    print(f"Cache stats: {stats.to_dict()}")

    await cache.shutdown()


async def example_file_caching():
    """Cache file contents with prediction."""
    print("\n=== File Caching with Prediction ===")

    cache = get_smart_cache()
    await cache.initialize()

    workspace_id = "ws_project123"

    # Simulate accessing files in order
    files = [
        "/project/main.py",
        "/project/utils.py",
        "/project/models.py",
        "/project/utils.py",  # Access utils again
        "/project/config.py",
    ]

    # Cache file contents and train prediction model
    for file_path in files:
        # Simulate file content
        content = f"# Content of {file_path}\n" + "x" * 1000

        # Cache with context for prediction
        await cache.set(f"file:{file_path}", content, ttl=600, context=workspace_id)
        print(f"Cached: {file_path}")

    # Predict next files after accessing utils.py
    current_file = "/project/utils.py"
    predictions = await cache.predict_next(f"file:{current_file}", context=workspace_id, top_k=3)
    print(f"\nPredicted next files after {current_file}:")
    for pred in predictions:
        print(f"  - {pred}")

    await cache.shutdown()


async def example_workspace_warming():
    """Warm cache for a workspace on open."""
    print("\n=== Workspace Cache Warming ===")

    cache = get_smart_cache()
    await cache.initialize()

    workspace_id = "ws_myproject"
    workspace_root = "/path/to/myproject"

    # File loader function (simulated)
    async def load_file_content(file_path: str) -> str:
        """Load file content (in real usage, read from disk)."""
        await asyncio.sleep(0.01)  # Simulate I/O
        return f"Content of {file_path}"

    # Warm cache with common file patterns
    files_cached = await cache.warm_cache(
        workspace_id=workspace_id,
        workspace_root=workspace_root,
        loader_func=load_file_content,
        file_patterns=["*.py", "*.js", "*.md"],
    )

    print(f"Warmed cache with {files_cached} files")

    await cache.shutdown()


async def example_prefetching():
    """Prefetch related content based on current context."""
    print("\n=== Intelligent Prefetching ===")

    cache = get_smart_cache()
    await cache.initialize()

    workspace_id = "ws_app"

    # Simulate user workflow: editing a controller file
    current_file = "/app/controllers/user_controller.py"

    # Cache current file
    await cache.set(
        f"file:{current_file}",
        "class UserController: ...",
        ttl=600,
        context=workspace_id,
    )

    # Related files that might be needed next
    related_files = [
        "/app/models/user.py",
        "/app/views/user_view.py",
        "/app/tests/test_user_controller.py",
    ]

    # Prefetch loader
    async def load_file(file_path: str) -> str:
        await asyncio.sleep(0.01)
        return f"Content of {file_path}"

    # Prefetch related files
    prefetched = await cache.prefetch(
        keys=[f"file:{f}" for f in related_files],
        loader_func=load_file,
        context=workspace_id,
        ttl=600,
    )

    print(f"Prefetched {prefetched} related files")

    # Predict what user will access next
    predictions = await cache.predict_next(f"file:{current_file}", context=workspace_id)
    print(f"Next predicted files: {predictions}")

    await cache.shutdown()


async def example_embeddings_cache():
    """Cache embeddings and search results for LLM context."""
    print("\n=== Caching LLM Embeddings & Search Results ===")

    cache = get_smart_cache()
    await cache.initialize()

    # Cache file embeddings
    file_path = "/project/module.py"
    embedding = [0.1, 0.2, 0.3] * 100  # Mock 300-dim embedding

    await cache.set(
        f"embedding:{file_path}",
        {"file": file_path, "embedding": embedding, "timestamp": "2024-01-01"},
        ttl=3600,  # 1 hour
    )

    # Cache search results
    query = "authentication implementation"
    search_results = [
        {"file": "/auth/login.py", "score": 0.95},
        {"file": "/auth/session.py", "score": 0.87},
    ]

    await cache.set(f"search:{query}", search_results, ttl=300)

    # Retrieve cached embedding
    cached_embedding = await cache.get(f"embedding:{file_path}")
    print(f"Cached embedding dimensions: {len(cached_embedding['embedding'])}")

    # Retrieve cached search results
    cached_search = await cache.get(f"search:{query}")
    print(f"Cached search results: {len(cached_search)} files")

    await cache.shutdown()


async def example_sqlite_backend():
    """Use SQLite backend for persistent caching."""
    print("\n=== SQLite Persistent Backend ===")

    # Create cache with SQLite backend
    cache = get_smart_cache(
        backend=CacheBackend.SQLITE,
        max_size=50000,
    )
    await cache.initialize()

    # Cache persists across restarts
    await cache.set("persistent:data", {"value": 42, "name": "answer"}, ttl=86400)

    # Get value
    value = await cache.get("persistent:data")
    print(f"Retrieved from SQLite: {value}")

    # Stats
    stats = cache.get_stats()
    print(f"SQLite cache stats: {stats.to_dict()}")

    await cache.shutdown()


async def example_background_refresh():
    """Demonstrate background refresh of stale entries."""
    print("\n=== Background Refresh ===")

    cache = get_smart_cache()
    await cache.initialize()

    # Add entries with short TTL
    await cache.set("data:1", {"value": 1}, ttl=10)
    await cache.set("data:2", {"value": 2}, ttl=10)
    await cache.set("data:3", {"value": 3}, ttl=10)

    print("Waiting for entries to become stale...")
    await asyncio.sleep(8)  # Wait 80% of TTL

    # Background refresh task will detect stale entries
    stats = cache.get_stats()
    print(f"Cache size: {stats.size} entries")

    await cache.shutdown()


async def example_eviction_strategy():
    """Demonstrate LRU + frequency-based eviction."""
    print("\n=== Smart Eviction Strategy ===")

    # Create small cache to trigger eviction
    cache = get_smart_cache(
        backend=CacheBackend.MEMORY,
        max_size=5,  # Only 5 entries
    )
    await cache.initialize()

    # Add entries
    for i in range(5):
        await cache.set(f"entry:{i}", f"value_{i}", ttl=300)

    # Access some entries multiple times (increase frequency)
    await cache.get("entry:0")
    await cache.get("entry:0")
    await cache.get("entry:0")  # High frequency

    await cache.get("entry:1")
    await cache.get("entry:1")  # Medium frequency

    # Add new entry - should evict entry with lowest score
    await cache.set("entry:5", "value_5", ttl=300)

    # Check which entries remain
    stats = cache.get_stats()
    print(f"Cache size after eviction: {stats.size} (max: {stats.max_size})")
    print(f"Evictions: {stats.evictions}")

    await cache.shutdown()


async def example_context_prefetch_llm():
    """Prefetch context for LLM calls based on conversation flow."""
    print("\n=== LLM Context Prefetching ===")

    cache = get_smart_cache()
    await cache.initialize()

    conversation_id = "conv_123"

    # User mentions a file in chat
    mentioned_file = "/project/auth/login.py"

    # Cache the file content
    await cache.set(
        f"file:{mentioned_file}",
        "def login(username, password): ...",
        ttl=600,
        context=conversation_id,
    )

    # Predict and prefetch related files for LLM context
    related_files = [
        "/project/auth/session.py",
        "/project/models/user.py",
        "/project/config/auth_config.py",
    ]

    async def load_file(key: str) -> str:
        file_path = key.replace("file:", "")
        return f"Content of {file_path}"

    prefetched = await cache.prefetch(
        keys=[f"file:{f}" for f in related_files],
        loader_func=load_file,
        context=conversation_id,
        ttl=600,
    )

    print(f"Prefetched {prefetched} files for LLM context")

    # Get predictions for next likely files
    predictions = await cache.predict_next(
        f"file:{mentioned_file}",
        context=conversation_id,
        top_k=5,
    )
    print(f"Predicted next context files: {predictions}")

    await cache.shutdown()


async def example_model_persistence():
    """Save and load prediction model."""
    print("\n=== Prediction Model Persistence ===")

    cache = get_smart_cache()
    await cache.initialize()

    # Train model with some patterns
    files = [
        ("main.py", "utils.py"),
        ("main.py", "config.py"),
        ("utils.py", "helpers.py"),
        ("utils.py", "config.py"),
    ]

    for file1, file2 in files:
        await cache.set(f"file:{file1}", "content1", ttl=300)
        await cache.set(f"file:{file2}", "content2", ttl=300)

    # Save model
    model_path = Path("/tmp/test_prediction_model.pkl")
    cache.save_model(model_path)
    print(f"Saved model to {model_path}")

    # Create new cache and load model
    cache2 = get_smart_cache()
    await cache2.initialize()
    cache2.load_model(model_path)
    print("Loaded model into new cache instance")

    # Test predictions
    predictions = await cache2.predict_next("file:main.py", top_k=2)
    print(f"Predictions from loaded model: {predictions}")

    # Cleanup
    model_path.unlink()
    await cache.shutdown()
    await cache2.shutdown()


async def main():
    """Run all examples."""
    print("=" * 60)
    print("SmartCache Examples for MagnetarCode")
    print("=" * 60)

    await example_basic_usage()
    await example_file_caching()
    await example_prefetching()
    await example_embeddings_cache()
    await example_eviction_strategy()
    await example_context_prefetch_llm()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
