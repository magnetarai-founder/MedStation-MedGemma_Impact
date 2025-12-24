"""
Module: test_cache_service.py
Purpose: Test CacheService functionality including Redis operations, metrics, and decorator

Coverage:
- CacheService initialization (with/without Redis)
- Cache get/set operations
- Hit rate calculation
- Cache metrics (hits, misses, stats)
- Pattern deletion
- The @cached decorator
- Global cache instance management

Priority: 2.2 (Middleware & Infrastructure)
Expected Coverage Gain: +2-3%
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# Ensure test environment
os.environ["ELOHIM_ENV"] = "test"

# Add backend to path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "api"))


class TestCacheServiceWithoutRedis:
    """Test CacheService behavior when Redis is not available"""

    def test_cache_service_graceful_degradation(self):
        """Test that CacheService works without Redis (disabled mode)"""
        with patch.dict('sys.modules', {'redis': None}):
            # Reimport to pick up the mocked redis
            import importlib
            from api import cache_service
            importlib.reload(cache_service)

            # Create service with Redis unavailable
            with patch.object(cache_service, 'REDIS_AVAILABLE', False):
                service = cache_service.CacheService()

                # Should have no redis connection
                assert service.redis is None
                assert service.pool is None

                # get should return None gracefully
                result = service.get("test_key")
                assert result is None

    def test_redis_available_flag(self):
        """Test REDIS_AVAILABLE flag detection"""
        from api.cache_service import REDIS_AVAILABLE
        # Should be True if redis is installed, False otherwise
        # This test just verifies the flag exists and is boolean
        assert isinstance(REDIS_AVAILABLE, bool)


class TestCacheServiceOperations:
    """Test cache operations with mocked Redis"""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client"""
        mock = MagicMock()
        mock.ping.return_value = True
        mock.get.return_value = None
        mock.setex.return_value = True
        mock.delete.return_value = 1
        mock.keys.return_value = []
        mock.exists.return_value = 0
        mock.incrby.return_value = 1
        mock.expire.return_value = True
        mock.info.return_value = {"total_commands_processed": 100}
        mock.flushdb.return_value = True
        return mock

    @pytest.fixture
    def cache_service_with_mock(self, mock_redis):
        """Create CacheService with mocked Redis"""
        from api.cache_service import CacheService

        with patch('api.cache_service.redis') as mock_redis_module:
            mock_pool = MagicMock()
            mock_redis_module.Redis.return_value = mock_redis
            mock_redis_module.ConnectionError = Exception

            with patch('api.cache_service.ConnectionPool', return_value=mock_pool):
                with patch('api.cache_service.REDIS_AVAILABLE', True):
                    service = CacheService()
                    service.redis = mock_redis
                    return service

    def test_get_cache_hit(self, cache_service_with_mock, mock_redis):
        """Test cache get with hit"""
        # Simulate cache hit
        mock_redis.get.return_value = json.dumps({"data": "cached"})

        result = cache_service_with_mock.get("test_key")

        assert result == {"data": "cached"}
        assert cache_service_with_mock.hits == 1
        assert cache_service_with_mock.misses == 0

    def test_get_cache_miss(self, cache_service_with_mock, mock_redis):
        """Test cache get with miss"""
        mock_redis.get.return_value = None

        result = cache_service_with_mock.get("nonexistent_key")

        assert result is None
        assert cache_service_with_mock.misses == 1
        assert cache_service_with_mock.hits == 0

    def test_set_cache_value(self, cache_service_with_mock, mock_redis):
        """Test setting cache value with TTL"""
        result = cache_service_with_mock.set("key", {"value": 42}, ttl=300)

        assert result is True
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == "key"
        assert call_args[1] == 300  # TTL
        assert json.loads(call_args[2]) == {"value": 42}

    def test_delete_cache_key(self, cache_service_with_mock, mock_redis):
        """Test deleting cache key"""
        mock_redis.delete.return_value = 1

        result = cache_service_with_mock.delete("key_to_delete")

        assert result is True
        mock_redis.delete.assert_called_with("key_to_delete")

    def test_delete_nonexistent_key(self, cache_service_with_mock, mock_redis):
        """Test deleting nonexistent key returns False"""
        mock_redis.delete.return_value = 0

        result = cache_service_with_mock.delete("nonexistent")

        assert result is False

    def test_exists_key(self, cache_service_with_mock, mock_redis):
        """Test checking if key exists"""
        mock_redis.exists.return_value = 1

        result = cache_service_with_mock.exists("existing_key")

        assert result is True
        mock_redis.exists.assert_called_with("existing_key")

    def test_increment_counter(self, cache_service_with_mock, mock_redis):
        """Test incrementing a counter"""
        mock_redis.incrby.return_value = 5

        result = cache_service_with_mock.increment("counter_key", 3)

        assert result == 5
        mock_redis.incrby.assert_called_with("counter_key", 3)

    def test_expire_key(self, cache_service_with_mock, mock_redis):
        """Test setting TTL on existing key"""
        mock_redis.expire.return_value = True

        result = cache_service_with_mock.expire("key", 600)

        assert result is True
        mock_redis.expire.assert_called_with("key", 600)


class TestCacheMetrics:
    """Test cache hit rate and metrics tracking"""

    def test_hit_rate_calculation_empty(self):
        """Test hit rate when no requests made"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            # No hits or misses
            assert service.hit_rate() == 0.0

    def test_hit_rate_calculation_with_data(self):
        """Test hit rate calculation with hits and misses"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            service.hits = 80
            service.misses = 20

            # 80 hits / 100 total = 80%
            assert service.hit_rate() == 80.0

    def test_hit_rate_all_hits(self):
        """Test hit rate when all requests are hits"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            service.hits = 100
            service.misses = 0

            assert service.hit_rate() == 100.0

    def test_hit_rate_all_misses(self):
        """Test hit rate when all requests are misses"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            service.hits = 0
            service.misses = 50

            assert service.hit_rate() == 0.0

    def test_reset_stats(self):
        """Test resetting hit/miss counters"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            service.hits = 100
            service.misses = 50

            service.reset_stats()

            assert service.hits == 0
            assert service.misses == 0


class TestPatternDeletion:
    """Test pattern-based cache invalidation"""

    def test_delete_pattern_with_matches(self):
        """Test deleting keys matching pattern"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            mock_redis = MagicMock()
            mock_redis.keys.return_value = ["user:1", "user:2", "user:3"]
            mock_redis.delete.return_value = 3
            service.redis = mock_redis

            result = service.delete_pattern("user:*")

            assert result == 3
            mock_redis.keys.assert_called_with("user:*")
            mock_redis.delete.assert_called_with("user:1", "user:2", "user:3")

    def test_delete_pattern_no_matches(self):
        """Test deleting pattern with no matching keys"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            mock_redis = MagicMock()
            mock_redis.keys.return_value = []
            service.redis = mock_redis

            result = service.delete_pattern("nonexistent:*")

            assert result == 0
            mock_redis.delete.assert_not_called()


class TestCachedDecorator:
    """Test the @cached decorator functionality"""

    def test_cached_decorator_caches_result(self):
        """Test that decorator caches function results"""
        from api.cache_service import CacheService, cached

        # Create mock cache
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # First call: cache miss
        mock_cache.set.return_value = True

        call_count = 0

        @cached(ttl=300, cache_instance=mock_cache)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        mock_cache.set.assert_called()

    def test_cached_decorator_returns_cached_value(self):
        """Test that decorator returns cached value on hit"""
        from api.cache_service import CacheService, cached

        # Create mock cache that returns cached value
        mock_cache = MagicMock()
        mock_cache.get.return_value = {"cached": True}

        call_count = 0

        @cached(ttl=300, cache_instance=mock_cache)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return {"result": x}

        # Call should return cached value without executing function
        result = expensive_function(5)
        assert result == {"cached": True}
        assert call_count == 0  # Function never called


class TestGlobalCacheInstance:
    """Test global cache instance management"""

    def test_get_cache_returns_singleton(self):
        """Test that get_cache returns singleton instance"""
        from api import cache_service

        # Reset global instance
        cache_service._cache_instance = None

        with patch('api.cache_service.CacheService') as MockCacheService:
            mock_instance = MagicMock()
            MockCacheService.return_value = mock_instance

            # First call creates instance
            cache1 = cache_service.get_cache()
            # Second call returns same instance
            cache2 = cache_service.get_cache()

            # Should be same instance
            assert cache1 is cache2
            # Constructor called only once
            MockCacheService.assert_called_once()

    def test_close_cache_clears_instance(self):
        """Test that close_cache clears the global instance"""
        from api import cache_service

        # Set up a mock instance
        mock_instance = MagicMock()
        cache_service._cache_instance = mock_instance

        cache_service.close_cache()

        # Instance should be cleared
        assert cache_service._cache_instance is None
        # Close should have been called
        mock_instance.close.assert_called_once()

    def test_close_cache_when_none(self):
        """Test close_cache when no instance exists"""
        from api import cache_service

        # Ensure no instance
        cache_service._cache_instance = None

        # Should not raise
        cache_service.close_cache()

        assert cache_service._cache_instance is None


class TestCacheErrorHandling:
    """Test error handling in cache operations"""

    def test_get_handles_exception(self):
        """Test that get handles exceptions gracefully"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            mock_redis = MagicMock()
            mock_redis.get.side_effect = Exception("Connection lost")
            service.redis = mock_redis

            result = service.get("key")

            # Should return None and count as miss
            assert result is None
            assert service.misses == 1

    def test_set_handles_exception(self):
        """Test that set handles exceptions gracefully"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            mock_redis = MagicMock()
            mock_redis.setex.side_effect = Exception("Redis unavailable")
            service.redis = mock_redis

            result = service.set("key", "value")

            # Should return False on error
            assert result is False

    def test_delete_handles_exception(self):
        """Test that delete handles exceptions gracefully"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            mock_redis = MagicMock()
            mock_redis.delete.side_effect = Exception("Error")
            service.redis = mock_redis

            result = service.delete("key")

            assert result is False

    def test_exists_handles_exception(self):
        """Test that exists handles exceptions gracefully"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            mock_redis = MagicMock()
            mock_redis.exists.side_effect = Exception("Error")
            service.redis = mock_redis

            result = service.exists("key")

            assert result is False

    def test_increment_handles_exception(self):
        """Test that increment handles exceptions gracefully"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            mock_redis = MagicMock()
            mock_redis.incrby.side_effect = Exception("Error")
            service.redis = mock_redis

            result = service.increment("key")

            assert result == 0

    def test_expire_handles_exception(self):
        """Test that expire handles exceptions gracefully"""
        from api.cache_service import CacheService

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            mock_redis = MagicMock()
            mock_redis.expire.side_effect = Exception("Error")
            service.redis = mock_redis

            result = service.expire("key", 100)

            assert result is False
