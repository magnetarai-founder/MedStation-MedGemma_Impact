"""
Unit tests for SmartCache system.

Run with: pytest api/services/caching/test_smart_cache.py -v
"""

import asyncio
import time
from pathlib import Path

import pytest

from api.services.caching import CacheBackend, CacheEntry, SmartCache, get_smart_cache


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            access_count=0,
            ttl=300,
        )

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.access_count == 0
        assert entry.ttl == 300

    def test_is_expired(self):
        """Test expiration checking."""
        # Create entry that expires in 1 second
        entry = CacheEntry(key="test", value="data", ttl=1)
        assert not entry.is_expired()

        # Wait for expiration
        time.sleep(1.1)
        assert entry.is_expired()

    def test_is_stale(self):
        """Test staleness checking."""
        entry = CacheEntry(key="test", value="data", ttl=10)

        # Fresh entry
        assert not entry.is_stale(stale_threshold=0.8)

        # Wait for 80% of TTL
        time.sleep(8.1)
        assert entry.is_stale(stale_threshold=0.8)

    def test_access(self):
        """Test access tracking."""
        entry = CacheEntry(key="test", value="data")
        initial_time = entry.last_accessed

        time.sleep(0.1)
        entry.access()

        assert entry.access_count == 1
        assert entry.last_accessed > initial_time

    def test_eviction_score(self):
        """Test eviction score calculation."""
        entry1 = CacheEntry(key="old", value="data", access_count=1)
        time.sleep(0.1)
        entry2 = CacheEntry(key="recent", value="data", access_count=1)

        # Recent entry should have higher score
        assert entry2.eviction_score() > entry1.eviction_score()

        # Increase frequency of old entry
        entry1.access_count = 100

        # High frequency should increase score
        assert entry1.eviction_score() > entry2.eviction_score()


class TestSmartCacheBasics:
    """Test basic SmartCache operations."""

    @pytest.mark.asyncio
    async def test_cache_initialization(self):
        """Test cache initialization."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        assert cache.backend_type == CacheBackend.MEMORY
        assert cache.stats.hits == 0
        assert cache.stats.misses == 0

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_get_set(self):
        """Test basic get/set operations."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        # Set value
        await cache.set("test_key", {"data": "value"}, ttl=300)

        # Get value
        value = await cache.get("test_key")
        assert value == {"data": "value"}

        # Stats
        assert cache.stats.hits == 1
        assert cache.stats.misses == 0

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        # Get non-existent key
        value = await cache.get("nonexistent")
        assert value is None
        assert cache.stats.misses == 1

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test delete operation."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        # Set and delete
        await cache.set("test_key", "value")
        assert await cache.get("test_key") == "value"

        await cache.delete("test_key")
        assert await cache.get("test_key") is None

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing cache."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        # Add multiple entries
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # Clear cache
        await cache.clear()

        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert cache.stats.size == 0

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        # Set with short TTL
        await cache.set("test_key", "value", ttl=1)

        # Should exist initially
        assert await cache.get("test_key") == "value"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        assert await cache.get("test_key") is None

        await cache.shutdown()


class TestPredictionModel:
    """Test prediction model."""

    @pytest.mark.asyncio
    async def test_prediction_training(self):
        """Test training prediction model."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        context = "workspace_123"

        # Simulate access pattern: A -> B -> C
        await cache.set("file:A", "content_a", context=context)
        await cache.set("file:B", "content_b", context=context)
        await cache.set("file:C", "content_c", context=context)

        # Predict next after A
        predictions = await cache.predict_next("file:A", context=context)

        # Should predict B (most common transition)
        assert "file:B" in predictions

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_prediction_accuracy(self):
        """Test prediction accuracy improves with training."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        # Train pattern: main.py -> utils.py (10 times)
        for _ in range(10):
            await cache.set("file:main.py", "content")
            await cache.set("file:utils.py", "content")

        # Predict next
        predictions = await cache.predict_next("file:main.py", top_k=1)

        # Should predict utils.py
        assert predictions[0] == "file:utils.py"

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_context_isolation(self):
        """Test predictions are isolated by context."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        # Workspace 1 pattern: A -> B
        await cache.set("file:A", "content", context="ws1")
        await cache.set("file:B", "content", context="ws1")

        # Workspace 2 pattern: A -> C
        await cache.set("file:A", "content", context="ws2")
        await cache.set("file:C", "content", context="ws2")

        # Predictions should be different
        pred_ws1 = await cache.predict_next("file:A", context="ws1")
        pred_ws2 = await cache.predict_next("file:A", context="ws2")

        assert "file:B" in pred_ws1
        assert "file:C" in pred_ws2

        await cache.shutdown()


class TestPrefetching:
    """Test prefetching capabilities."""

    @pytest.mark.asyncio
    async def test_prefetch(self):
        """Test prefetching multiple keys."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        async def loader(key: str) -> str:
            """Mock file loader."""
            await asyncio.sleep(0.01)
            return f"content_of_{key}"

        keys = ["file:A", "file:B", "file:C"]
        prefetched = await cache.prefetch(keys, loader_func=loader)

        assert prefetched == 3

        # Verify all cached
        assert await cache.get("file:A") == "content_of_file:A"
        assert await cache.get("file:B") == "content_of_file:B"
        assert await cache.get("file:C") == "content_of_file:C"

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_prefetch_skips_existing(self):
        """Test prefetch skips already-cached keys."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        # Pre-cache one key
        await cache.set("file:A", "existing_content")

        async def loader(key: str) -> str:
            return f"content_of_{key}"

        keys = ["file:A", "file:B"]
        prefetched = await cache.prefetch(keys, loader_func=loader)

        # Should only prefetch file:B
        assert prefetched == 1
        assert await cache.get("file:A") == "existing_content"

        await cache.shutdown()


class TestEviction:
    """Test eviction strategies."""

    @pytest.mark.asyncio
    async def test_size_based_eviction(self):
        """Test eviction when size limit reached."""
        cache = SmartCache(backend=CacheBackend.MEMORY, max_size=3)
        await cache.initialize()

        # Fill cache to limit
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Add one more - should trigger eviction
        await cache.set("key4", "value4")

        stats = cache.get_stats()
        assert stats.size == 3
        assert stats.evictions >= 1

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU-based eviction."""
        cache = SmartCache(backend=CacheBackend.MEMORY, max_size=3)
        await cache.initialize()

        # Add entries
        await cache.set("old", "value")
        await asyncio.sleep(0.1)
        await cache.set("newer", "value")
        await asyncio.sleep(0.1)
        await cache.set("newest", "value")

        # Access 'old' to make it recent
        await cache.get("old")

        # Add new entry - should evict 'newer' (least recently used)
        await cache.set("new", "value")

        # 'old' should still be cached
        assert await cache.get("old") is not None

        await cache.shutdown()


class TestBackends:
    """Test different cache backends."""

    @pytest.mark.asyncio
    async def test_memory_backend(self):
        """Test memory backend."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        await cache.set("key", "value")
        assert await cache.get("key") == "value"

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_sqlite_backend(self):
        """Test SQLite backend."""
        db_path = Path("/tmp/test_cache.db")

        # Clean up before test
        if db_path.exists():
            db_path.unlink()

        cache = SmartCache(backend=CacheBackend.SQLITE, db_path=db_path)
        await cache.initialize()

        # Set value
        await cache.set("key", {"data": "value"})
        assert await cache.get("key") == {"data": "value"}

        await cache.shutdown()

        # Create new cache - data should persist
        cache2 = SmartCache(backend=CacheBackend.SQLITE, db_path=db_path)
        await cache2.initialize()

        assert await cache2.get("key") == {"data": "value"}

        await cache2.shutdown()

        # Cleanup
        db_path.unlink()


class TestStatistics:
    """Test cache statistics."""

    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        # Set up test data
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # 2 hits
        await cache.get("key1")
        await cache.get("key2")

        # 1 miss
        await cache.get("nonexistent")

        stats = cache.get_stats()
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.hit_rate == pytest.approx(66.67, rel=0.1)

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_size_tracking(self):
        """Test cache size tracking."""
        cache = SmartCache(backend=CacheBackend.MEMORY)
        await cache.initialize()

        # Add entries
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        stats = cache.get_stats()
        assert stats.size == 2
        assert stats.size_bytes > 0

        await cache.shutdown()


class TestModelPersistence:
    """Test prediction model persistence."""

    @pytest.mark.asyncio
    async def test_save_load_model(self):
        """Test saving and loading prediction model."""
        model_path = Path("/tmp/test_prediction_model.pkl")

        # Create cache and train model
        cache1 = SmartCache(backend=CacheBackend.MEMORY)
        await cache1.initialize()

        await cache1.set("file:A", "content")
        await cache1.set("file:B", "content")

        # Save model
        cache1.save_model(model_path)

        # Create new cache and load model
        cache2 = SmartCache(backend=CacheBackend.MEMORY)
        await cache2.initialize()
        cache2.load_model(model_path)

        # Predictions should work
        predictions = await cache2.predict_next("file:A")
        assert "file:B" in predictions

        await cache1.shutdown()
        await cache2.shutdown()

        # Cleanup
        model_path.unlink()


class TestGlobalInstance:
    """Test global cache instance."""

    @pytest.mark.asyncio
    async def test_get_smart_cache_singleton(self):
        """Test global cache is a singleton."""
        cache1 = get_smart_cache()
        cache2 = get_smart_cache()

        # Should be same instance
        assert cache1 is cache2

        await cache1.initialize()
        await cache1.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
