"""
Smart Cache Implementation with Predictive Loading and Multi-Tier Storage

This module provides an intelligent caching system that:
1. Predicts what users will need next using Markov chains
2. Pre-warms caches based on usage patterns
3. Prefetches context for LLM calls
4. Uses LRU + frequency-based eviction
5. Supports multiple backends (memory, SQLite, Redis)
6. Background refreshes stale entries
"""

import asyncio
import json
import logging
import pickle
import sqlite3
import time
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


class CacheBackend(Enum):
    """Available cache backend types."""

    MEMORY = "memory"
    SQLITE = "sqlite"
    REDIS = "redis"


@dataclass
class CacheEntry:
    """
    Cache entry with metadata for intelligent eviction.

    Attributes:
        key: Cache key
        value: Cached value
        access_count: Number of times accessed
        last_accessed: Timestamp of last access
        created_at: Timestamp of creation
        ttl: Time to live in seconds
        size_bytes: Approximate size in bytes
    """

    key: str
    value: Any
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    ttl: int = 300  # 5 minutes default
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return time.time() > (self.created_at + self.ttl)

    def is_stale(self, stale_threshold: float = 0.8) -> bool:
        """Check if entry is stale (near expiration)."""
        age = time.time() - self.created_at
        return age > (self.ttl * stale_threshold)

    def access(self) -> None:
        """Mark entry as accessed."""
        self.access_count += 1
        self.last_accessed = time.time()

    def eviction_score(self) -> float:
        """
        Calculate eviction score (lower = more likely to evict).

        Combines LRU and frequency:
        - Recent access increases score
        - High frequency increases score
        """
        recency = time.time() - self.last_accessed
        frequency = self.access_count

        # Lower recency (more recent) = higher score
        # Higher frequency = higher score
        # Normalize recency to 0-1 range (assume max 1 hour)
        recency_score = max(0, 1 - (recency / 3600))
        frequency_score = min(frequency / 100, 1.0)  # Cap at 100 accesses

        return (recency_score * 0.6) + (frequency_score * 0.4)


@dataclass
class CacheStats:
    """
    Cache performance statistics.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        hit_rate: Hit rate percentage
        size: Current cache size (entries)
        size_bytes: Current cache size (bytes)
        evictions: Number of evictions
        predictions: Number of predictions made
        prediction_accuracy: Accuracy of predictions
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    predictions: int = 0
    correct_predictions: int = 0
    size: int = 0
    size_bytes: int = 0
    max_size: int = 10000
    max_size_bytes: int = 100 * 1024 * 1024  # 100MB

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    @property
    def prediction_accuracy(self) -> float:
        """Calculate prediction accuracy percentage."""
        return (
            (self.correct_predictions / self.predictions * 100) if self.predictions > 0 else 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate, 2),
            "evictions": self.evictions,
            "predictions": self.predictions,
            "prediction_accuracy": round(self.prediction_accuracy, 2),
            "size": self.size,
            "size_bytes": self.size_bytes,
            "max_size": self.max_size,
            "utilization": round((self.size / self.max_size * 100), 2) if self.max_size > 0 else 0.0,
        }


class PredictionModel:
    """
    Markov chain-based prediction model for next-file prediction.

    Uses user access patterns to predict what files they'll need next.
    Tracks transitions between files to build a probability model.
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize prediction model.

        Args:
            max_history: Maximum history to keep for training
        """
        self.max_history = max_history
        self._transitions: dict[str, Counter] = defaultdict(Counter)
        self._history: deque = deque(maxlen=max_history)
        self._lock = Lock()

    def record_access(self, key: str, context: str | None = None) -> None:
        """
        Record an access for training the model.

        Args:
            key: The accessed key (e.g., file path)
            context: Optional context (e.g., workspace_id)
        """
        with self._lock:
            full_key = f"{context}:{key}" if context else key

            # Record transition from previous key
            if self._history:
                prev_key = self._history[-1]
                self._transitions[prev_key][full_key] += 1

            self._history.append(full_key)

    def predict_next(self, current_key: str, context: str | None = None, top_k: int = 5) -> list[str]:
        """
        Predict next likely keys.

        Args:
            current_key: Current key
            context: Optional context
            top_k: Number of predictions to return

        Returns:
            List of predicted keys (most likely first)
        """
        with self._lock:
            full_key = f"{context}:{current_key}" if context else current_key

            if full_key not in self._transitions:
                return []

            # Get most common transitions
            predictions = self._transitions[full_key].most_common(top_k)

            # Extract keys and remove context prefix
            result = []
            for key, _count in predictions:
                if context and key.startswith(f"{context}:"):
                    result.append(key[len(f"{context}:") :])
                else:
                    result.append(key)

            return result

    def get_related_keys(self, key: str, context: str | None = None, threshold: int = 2) -> list[str]:
        """
        Get keys frequently accessed together.

        Args:
            key: The key to find relations for
            context: Optional context
            threshold: Minimum co-occurrence count

        Returns:
            List of related keys
        """
        with self._lock:
            full_key = f"{context}:{key}" if context else key

            if full_key not in self._transitions:
                return []

            related = []
            for next_key, count in self._transitions[full_key].items():
                if count >= threshold:
                    if context and next_key.startswith(f"{context}:"):
                        related.append(next_key[len(f"{context}:") :])
                    else:
                        related.append(next_key)

            return related

    def save(self, path: Path) -> None:
        """
        Save model to disk using pickle (safe for internal state only).

        Note: Uses pickle for internal model state which contains only
        Counter and deque objects - safe as this is trusted internal data.
        """
        with self._lock:
            data = {
                "transitions": dict(self._transitions),
                "history": list(self._history),
            }
            with open(path, "wb") as f:
                pickle.dump(data, f)

    def load(self, path: Path) -> None:
        """
        Load model from disk.

        Note: Only loads from trusted internal state files.
        """
        with self._lock:
            with open(path, "rb") as f:
                data = pickle.load(f)
                self._transitions = defaultdict(Counter, data["transitions"])
                self._history = deque(data["history"], maxlen=self.max_history)


class MemoryBackend:
    """In-memory cache backend with size limits."""

    def __init__(self, max_size: int = 10000, max_size_bytes: int = 100 * 1024 * 1024):
        self.max_size = max_size
        self.max_size_bytes = max_size_bytes
        self._cache: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._size_bytes = 0
        self._eviction_count = 0  # Track evictions for stats

    def get(self, key: str) -> CacheEntry | None:
        """Get entry from cache."""
        with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                entry.access()
                return entry
            elif entry:
                del self._cache[key]
                self._size_bytes -= entry.size_bytes
            return None

    def set(self, key: str, entry: CacheEntry) -> bool:
        """Set entry in cache."""
        with self._lock:
            # Remove old entry if exists
            if key in self._cache:
                self._size_bytes -= self._cache[key].size_bytes

            # Evict if needed
            while (
                len(self._cache) >= self.max_size or self._size_bytes + entry.size_bytes > self.max_size_bytes
            ):
                if not self._evict_one():
                    return False

            self._cache[key] = entry
            self._size_bytes += entry.size_bytes
            return True

    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._cache:
                self._size_bytes -= self._cache[key].size_bytes
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()
            self._size_bytes = 0

    def get_all_keys(self) -> list[str]:
        """Get all keys."""
        with self._lock:
            return list(self._cache.keys())

    def get_stale_keys(self, stale_threshold: float = 0.8) -> list[str]:
        """Get keys of stale entries."""
        with self._lock:
            return [k for k, v in self._cache.items() if v.is_stale(stale_threshold)]

    def size(self) -> tuple[int, int]:
        """Get cache size (entries, bytes)."""
        with self._lock:
            return len(self._cache), self._size_bytes

    def _evict_one(self) -> bool:
        """Evict one entry using LRU+frequency scoring."""
        if not self._cache:
            return False

        # Find entry with lowest eviction score
        evict_key = min(self._cache.keys(), key=lambda k: self._cache[k].eviction_score())
        self._size_bytes -= self._cache[evict_key].size_bytes
        del self._cache[evict_key]
        self._eviction_count += 1
        return True

    def get_and_reset_eviction_count(self) -> int:
        """Get eviction count since last call and reset to 0."""
        with self._lock:
            count = self._eviction_count
            self._eviction_count = 0
            return count


class SQLiteBackend:
    """SQLite-based persistent cache backend using JSON for serialization."""

    def __init__(self, db_path: Path, max_size: int = 100000):
        self.db_path = db_path
        self.max_size = max_size
        self._init_db()
        self._lock = Lock()
        self._eviction_count = 0  # Track evictions for stats

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    access_count INTEGER,
                    last_accessed REAL,
                    created_at REAL,
                    ttl INTEGER,
                    size_bytes INTEGER
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache_entries(last_accessed)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_created_ttl ON cache_entries(created_at, ttl)"
            )

    def _serialize_value(self, value: Any) -> str:
        """Serialize value to JSON string."""
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize value to JSON: {e}")
            # Fallback to string representation
            return json.dumps({"_type": "string", "value": str(value)})

    def _deserialize_value(self, serialized: str) -> Any:
        """Deserialize value from JSON string."""
        try:
            value = json.loads(serialized)
            # Handle fallback string representation
            if isinstance(value, dict) and value.get("_type") == "string":
                return value["value"]
            return value
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to deserialize JSON value: {e}")
            return None

    def get(self, key: str) -> CacheEntry | None:
        """Get entry from cache."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM cache_entries WHERE key = ?", (key,))
                row = cursor.fetchone()

                if not row:
                    return None

                entry = CacheEntry(
                    key=row["key"],
                    value=self._deserialize_value(row["value"]),
                    access_count=row["access_count"],
                    last_accessed=row["last_accessed"],
                    created_at=row["created_at"],
                    ttl=row["ttl"],
                    size_bytes=row["size_bytes"],
                )

                if entry.is_expired():
                    cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                    conn.commit()
                    return None

                # Update access stats
                cursor.execute(
                    """UPDATE cache_entries
                       SET access_count = ?, last_accessed = ?
                       WHERE key = ?""",
                    (entry.access_count + 1, time.time(), key),
                )
                conn.commit()

                entry.access()
                return entry

    def set(self, key: str, entry: CacheEntry) -> bool:
        """Set entry in cache."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Evict if needed
                cursor.execute("SELECT COUNT(*) FROM cache_entries")
                count = cursor.fetchone()[0]

                if count >= self.max_size:
                    self._evict_one(conn)

                # Serialize value
                serialized_value = self._serialize_value(entry.value)

                # Insert or replace
                cursor.execute(
                    """INSERT OR REPLACE INTO cache_entries
                       (key, value, access_count, last_accessed, created_at, ttl, size_bytes)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        entry.key,
                        serialized_value,
                        entry.access_count,
                        entry.last_accessed,
                        entry.created_at,
                        entry.ttl,
                        entry.size_bytes,
                    ),
                )
                conn.commit()
                return True

    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                conn.commit()
                return cursor.rowcount > 0

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache_entries")
                conn.commit()

    def get_all_keys(self) -> list[str]:
        """Get all keys."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key FROM cache_entries")
                return [row[0] for row in cursor.fetchall()]

    def get_stale_keys(self, stale_threshold: float = 0.8) -> list[str]:
        """Get keys of stale entries."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                current_time = time.time()
                cursor.execute(
                    """SELECT key, created_at, ttl FROM cache_entries
                       WHERE (? - created_at) > (ttl * ?)""",
                    (current_time, stale_threshold),
                )
                return [row[0] for row in cursor.fetchall()]

    def size(self) -> tuple[int, int]:
        """Get cache size (entries, bytes)."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), SUM(size_bytes) FROM cache_entries")
                count, total_bytes = cursor.fetchone()
                return count or 0, total_bytes or 0

    def _evict_one(self, conn: sqlite3.Connection) -> None:
        """Evict one entry using LRU+frequency scoring."""
        cursor = conn.cursor()

        # Calculate eviction scores and evict lowest
        cursor.execute("""
            SELECT key, access_count, last_accessed
            FROM cache_entries
            ORDER BY (
                (1 - ((? - last_accessed) / 3600.0)) * 0.6 +
                MIN(access_count / 100.0, 1.0) * 0.4
            ) ASC
            LIMIT 1
        """, (time.time(),))

        row = cursor.fetchone()
        if row:
            cursor.execute("DELETE FROM cache_entries WHERE key = ?", (row[0],))
            self._eviction_count += 1

    def get_and_reset_eviction_count(self) -> int:
        """Get eviction count since last call and reset to 0."""
        with self._lock:
            count = self._eviction_count
            self._eviction_count = 0
            return count


class RedisBackend:
    """
    Redis-based distributed cache backend.

    Features:
    - Distributed caching across multiple processes/machines
    - Automatic TTL-based expiration handled by Redis
    - Efficient key scanning with SCAN
    - Sorted set for eviction scoring
    """

    # Key prefixes for organization
    KEY_PREFIX = "smartcache:"
    SCORE_KEY = "smartcache:scores"

    def __init__(self, redis_url: str = "redis://localhost:6379", max_size: int = 100000):
        """
        Initialize Redis backend.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379)
            max_size: Maximum number of entries
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis package not installed. Install with: pip install redis>=5.0.0"
            )

        self.redis_url = redis_url
        self.max_size = max_size
        self._client: aioredis.Redis | None = None
        self._lock = asyncio.Lock()
        self._eviction_count = 0  # Track evictions for stats

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if self._client is None:
            self._client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We handle encoding ourselves
            )
            # Test connection
            await self._client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    def _make_key(self, key: str) -> str:
        """Create namespaced Redis key."""
        return f"{self.KEY_PREFIX}{key}"

    def _serialize_entry(self, entry: CacheEntry) -> bytes:
        """Serialize CacheEntry to JSON bytes."""
        data = {
            "key": entry.key,
            "value": entry.value,
            "access_count": entry.access_count,
            "last_accessed": entry.last_accessed,
            "created_at": entry.created_at,
            "ttl": entry.ttl,
            "size_bytes": entry.size_bytes,
        }
        # Use JSON for safe serialization
        try:
            return json.dumps(data, default=str).encode("utf-8")
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize entry: {e}")
            # Fallback: convert value to string
            data["value"] = str(entry.value)
            return json.dumps(data).encode("utf-8")

    def _deserialize_entry(self, data: bytes) -> CacheEntry | None:
        """Deserialize JSON bytes to CacheEntry."""
        try:
            parsed = json.loads(data.decode("utf-8"))
            return CacheEntry(
                key=parsed["key"],
                value=parsed["value"],
                access_count=parsed["access_count"],
                last_accessed=parsed["last_accessed"],
                created_at=parsed["created_at"],
                ttl=parsed["ttl"],
                size_bytes=parsed["size_bytes"],
            )
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to deserialize entry: {e}")
            return None

    async def get(self, key: str) -> CacheEntry | None:
        """Get entry from cache."""
        if not self._client:
            await self.connect()

        redis_key = self._make_key(key)

        async with self._lock:
            data = await self._client.get(redis_key)

            if not data:
                return None

            entry = self._deserialize_entry(data)
            if not entry:
                return None

            # Check expiration (Redis TTL handles this, but double-check)
            if entry.is_expired():
                await self._client.delete(redis_key)
                await self._client.zrem(self.SCORE_KEY, key)
                return None

            # Update access stats
            entry.access()

            # Update in Redis
            remaining_ttl = max(1, int(entry.ttl - (time.time() - entry.created_at)))
            await self._client.setex(redis_key, remaining_ttl, self._serialize_entry(entry))

            # Update eviction score
            await self._client.zadd(self.SCORE_KEY, {key: entry.eviction_score()})

            return entry

    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set entry in cache."""
        if not self._client:
            await self.connect()

        redis_key = self._make_key(key)

        async with self._lock:
            # Check size and evict if needed
            current_size = await self._client.zcard(self.SCORE_KEY)

            while current_size >= self.max_size:
                if not await self._evict_one():
                    return False
                current_size = await self._client.zcard(self.SCORE_KEY)

            # Store entry with TTL
            serialized = self._serialize_entry(entry)
            await self._client.setex(redis_key, entry.ttl, serialized)

            # Add to eviction score index
            await self._client.zadd(self.SCORE_KEY, {key: entry.eviction_score()})

            return True

    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        if not self._client:
            await self.connect()

        redis_key = self._make_key(key)

        async with self._lock:
            result = await self._client.delete(redis_key)
            await self._client.zrem(self.SCORE_KEY, key)
            return result > 0

    async def clear(self) -> None:
        """Clear all entries."""
        if not self._client:
            await self.connect()

        async with self._lock:
            # Use SCAN to find all keys with our prefix
            cursor = 0
            pattern = f"{self.KEY_PREFIX}*"

            while True:
                cursor, keys = await self._client.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._client.delete(*keys)
                if cursor == 0:
                    break

            # Clear scores
            await self._client.delete(self.SCORE_KEY)

    async def get_all_keys(self) -> list[str]:
        """Get all keys."""
        if not self._client:
            await self.connect()

        keys = []
        cursor = 0
        pattern = f"{self.KEY_PREFIX}*"
        prefix_len = len(self.KEY_PREFIX)

        while True:
            cursor, batch = await self._client.scan(cursor, match=pattern, count=100)
            keys.extend(k.decode("utf-8")[prefix_len:] for k in batch)
            if cursor == 0:
                break

        return keys

    async def get_stale_keys(self, stale_threshold: float = 0.8) -> list[str]:
        """Get keys of stale entries."""
        if not self._client:
            await self.connect()

        stale_keys = []
        all_keys = await self.get_all_keys()

        for key in all_keys:
            entry = await self.get(key)
            if entry and entry.is_stale(stale_threshold):
                stale_keys.append(key)

        return stale_keys

    async def size(self) -> tuple[int, int]:
        """Get cache size (entries, bytes)."""
        if not self._client:
            await self.connect()

        count = await self._client.zcard(self.SCORE_KEY)

        # Estimate total bytes by sampling
        total_bytes = 0
        sample_keys = await self.get_all_keys()

        for key in sample_keys[:100]:  # Sample up to 100 keys
            redis_key = self._make_key(key)
            data = await self._client.get(redis_key)
            if data:
                total_bytes += len(data)

        # Extrapolate if we have more keys
        if len(sample_keys) > 100:
            avg_size = total_bytes / 100
            total_bytes = int(avg_size * count)

        return count, total_bytes

    async def _evict_one(self) -> bool:
        """Evict one entry with lowest eviction score."""
        # Get entry with lowest score
        result = await self._client.zrange(self.SCORE_KEY, 0, 0)

        if not result:
            return False

        key = result[0].decode("utf-8") if isinstance(result[0], bytes) else result[0]
        redis_key = self._make_key(key)

        await self._client.delete(redis_key)
        await self._client.zrem(self.SCORE_KEY, key)
        self._eviction_count += 1

        return True

    def get_and_reset_eviction_count(self) -> int:
        """Get eviction count since last call and reset to 0."""
        count = self._eviction_count
        self._eviction_count = 0
        return count

    # Synchronous wrappers for compatibility with other backends
    def get_sync(self, key: str) -> CacheEntry | None:
        """Synchronous get (runs async in new event loop)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Can't run sync in async context
                logger.warning("Cannot run sync get in async context, returning None")
                return None
            return loop.run_until_complete(self.get(key))
        except RuntimeError:
            return asyncio.run(self.get(key))

    def set_sync(self, key: str, entry: CacheEntry) -> bool:
        """Synchronous set (runs async in new event loop)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                logger.warning("Cannot run sync set in async context, returning False")
                return False
            return loop.run_until_complete(self.set(key, entry))
        except RuntimeError:
            return asyncio.run(self.set(key, entry))


class SmartCache:
    """
    Intelligent cache with predictive loading and multi-tier storage.

    Features:
    - Predictive file loading using Markov chains
    - Pre-warming based on workspace usage patterns
    - Intelligent context prefetch for LLM calls
    - LRU + frequency-based eviction
    - Multiple backends (memory, SQLite, Redis)
    - Background refresh of stale entries
    """

    def __init__(
        self,
        backend: CacheBackend = CacheBackend.MEMORY,
        max_size: int = 10000,
        max_size_bytes: int = 100 * 1024 * 1024,
        db_path: Path | None = None,
        redis_url: str | None = None,
    ):
        """
        Initialize smart cache.

        Args:
            backend: Cache backend type
            max_size: Maximum number of entries
            max_size_bytes: Maximum cache size in bytes
            db_path: Path for SQLite database
            redis_url: Redis connection URL
        """
        self.backend_type = backend
        self.max_size = max_size
        self.max_size_bytes = max_size_bytes

        # Initialize backend
        self._is_async_backend = False  # Track if backend uses async methods
        if backend == CacheBackend.MEMORY:
            self._backend = MemoryBackend(max_size, max_size_bytes)
        elif backend == CacheBackend.SQLITE:
            if not db_path:
                db_path = Path.home() / ".magnetarcode" / "data" / "smart_cache.db"
                db_path.parent.mkdir(parents=True, exist_ok=True)
            self._backend = SQLiteBackend(db_path, max_size)
        elif backend == CacheBackend.REDIS:
            if not redis_url:
                redis_url = "redis://localhost:6379"
            self._backend = RedisBackend(redis_url, max_size)
            self._is_async_backend = True
        else:
            raise ValueError(f"Unknown backend: {backend}")

        # Statistics
        self.stats = CacheStats(max_size=max_size, max_size_bytes=max_size_bytes)

        # Prediction model
        self.prediction_model = PredictionModel()

        # Background refresh task
        self._refresh_task: asyncio.Task | None = None
        self._running = False

    async def initialize(self) -> None:
        """Initialize cache and start background tasks."""
        logger.info(f"Initializing SmartCache with {self.backend_type.value} backend")

        # Start background refresh
        await self.start_background_refresh()

    async def shutdown(self) -> None:
        """Shutdown cache and background tasks."""
        logger.info("Shutting down SmartCache")
        self._running = False

        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

    async def get(self, key: str, context: str | None = None) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key
            context: Optional context for prediction

        Returns:
            Cached value or None
        """
        entry = self._backend.get(key)

        if entry:
            self.stats.hits += 1
            self.prediction_model.record_access(key, context)
            logger.debug(f"Cache hit: {key}")
            return entry.value
        else:
            self.stats.misses += 1
            logger.debug(f"Cache miss: {key}")
            return None

    async def set(
        self, key: str, value: Any, ttl: int = 300, context: str | None = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            context: Optional context for prediction

        Returns:
            True if successful
        """
        # Estimate size using JSON serialization
        try:
            serialized = json.dumps(value, default=str)
            size_bytes = len(serialized.encode('utf-8'))
        except (TypeError, ValueError):
            size_bytes = 1024  # Default estimate

        entry = CacheEntry(
            key=key,
            value=value,
            ttl=ttl,
            size_bytes=size_bytes,
        )

        success = self._backend.set(key, entry)

        if success:
            self.prediction_model.record_access(key, context)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

        # Update stats including eviction count
        size, size_bytes = self._backend.size()
        self.stats.size = size
        self.stats.size_bytes = size_bytes

        # Collect eviction count from backend
        if hasattr(self._backend, 'get_and_reset_eviction_count'):
            evictions = self._backend.get_and_reset_eviction_count()
            self.stats.evictions += evictions

        return success

    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        success = self._backend.delete(key)
        if success:
            logger.debug(f"Cache delete: {key}")

        # Update stats
        size, size_bytes = self._backend.size()
        self.stats.size = size
        self.stats.size_bytes = size_bytes

        return success

    async def clear(self) -> None:
        """Clear all cache entries."""
        self._backend.clear()
        self.stats = CacheStats(max_size=self.max_size, max_size_bytes=self.max_size_bytes)
        logger.info("Cache cleared")

    async def predict_next(
        self, current_key: str, context: str | None = None, top_k: int = 5
    ) -> list[str]:
        """
        Predict next likely keys to be accessed.

        Args:
            current_key: Current key
            context: Optional context (e.g., workspace_id)
            top_k: Number of predictions

        Returns:
            List of predicted keys
        """
        predictions = self.prediction_model.predict_next(current_key, context, top_k)
        self.stats.predictions += len(predictions)
        logger.debug(f"Predicted {len(predictions)} next keys for {current_key}")
        return predictions

    async def prefetch(
        self, keys: list[str], loader_func: Any = None, context: str | None = None, ttl: int = 300
    ) -> int:
        """
        Prefetch multiple keys into cache.

        Args:
            keys: Keys to prefetch
            loader_func: Async function to load values (takes key as arg)
            context: Optional context
            ttl: Time to live

        Returns:
            Number of keys prefetched
        """
        if not loader_func:
            logger.warning("No loader function provided for prefetch")
            return 0

        prefetched = 0
        for key in keys:
            # Skip if already cached
            if await self.get(key, context):
                continue

            try:
                value = await loader_func(key)
                if value is not None:
                    await self.set(key, value, ttl=ttl, context=context)
                    prefetched += 1
            except Exception as e:
                logger.warning(f"Failed to prefetch {key}: {e}")

        logger.info(f"Prefetched {prefetched}/{len(keys)} keys")
        return prefetched

    async def warm_cache(
        self,
        workspace_id: str,
        workspace_root: str | None = None,
        loader_func: Any = None,
        file_patterns: list[str] | None = None,
    ) -> int:
        """
        Warm cache for a workspace based on usage patterns.

        Args:
            workspace_id: Workspace identifier
            workspace_root: Path to workspace root
            loader_func: Async function to load file contents
            file_patterns: File patterns to warm (e.g., ["*.py", "*.js"])

        Returns:
            Number of files cached
        """
        logger.info(f"Warming cache for workspace {workspace_id}")

        # Get related files from prediction model
        related_keys = self.prediction_model.get_related_keys(workspace_id, context=workspace_id)

        if not related_keys and workspace_root and file_patterns:
            # First time - scan workspace for common files
            from pathlib import Path

            related_keys = []
            for pattern in file_patterns:
                for path in Path(workspace_root).rglob(pattern):
                    if path.is_file():
                        related_keys.append(str(path))

        # Prefetch related files
        cached = await self.prefetch(related_keys[:50], loader_func, context=workspace_id)

        logger.info(f"Warmed cache with {cached} files for {workspace_id}")
        return cached

    async def background_refresh(self, refresh_interval: int = 60, stale_threshold: float = 0.8) -> None:
        """
        Background task to refresh stale entries.

        Args:
            refresh_interval: Interval between refresh checks (seconds)
            stale_threshold: Threshold for considering entry stale (0-1)
        """
        logger.info("Starting background cache refresh")
        self._running = True

        while self._running:
            try:
                await asyncio.sleep(refresh_interval)

                # Get stale keys
                stale_keys = self._backend.get_stale_keys(stale_threshold)

                if stale_keys:
                    logger.info(f"Found {len(stale_keys)} stale cache entries")

                    # For now, just log - could trigger refresh callbacks
                    for key in stale_keys[:10]:  # Limit to prevent spam
                        logger.debug(f"Stale entry: {key}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background refresh: {e}")

        logger.info("Stopped background cache refresh")

    async def start_background_refresh(
        self, refresh_interval: int = 60, stale_threshold: float = 0.8
    ) -> None:
        """Start background refresh task."""
        if not self._refresh_task or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(
                self.background_refresh(refresh_interval, stale_threshold)
            )

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        # Update size stats
        size, size_bytes = self._backend.size()
        self.stats.size = size
        self.stats.size_bytes = size_bytes
        return self.stats

    def get_prediction_model(self) -> PredictionModel:
        """Get the underlying prediction model."""
        return self.prediction_model

    def save_model(self, path: Path | None = None) -> None:
        """Save prediction model to disk."""
        if not path:
            path = Path.home() / ".magnetarcode" / "data" / "prediction_model.pkl"
            path.parent.mkdir(parents=True, exist_ok=True)

        self.prediction_model.save(path)
        logger.info(f"Saved prediction model to {path}")

    def load_model(self, path: Path | None = None) -> None:
        """Load prediction model from disk."""
        if not path:
            path = Path.home() / ".magnetarcode" / "data" / "prediction_model.pkl"

        if path.exists():
            self.prediction_model.load(path)
            logger.info(f"Loaded prediction model from {path}")
        else:
            logger.warning(f"Prediction model not found at {path}")


# Global cache instance with thread-safe initialization
_smart_cache: SmartCache | None = None
_smart_cache_lock = Lock()


def get_smart_cache(
    backend: CacheBackend = CacheBackend.MEMORY,
    max_size: int = 10000,
    max_size_bytes: int = 100 * 1024 * 1024,
) -> SmartCache:
    """
    Get global smart cache instance (thread-safe).

    Uses double-checked locking pattern to ensure only one instance
    is created even with concurrent access from multiple threads.

    Args:
        backend: Cache backend type
        max_size: Maximum number of entries
        max_size_bytes: Maximum cache size in bytes

    Returns:
        SmartCache instance
    """
    global _smart_cache

    # SECURITY: Double-checked locking pattern for thread-safe singleton
    # First check without lock for performance (fast path)
    if _smart_cache is None:
        with _smart_cache_lock:
            # Second check with lock to prevent race condition
            if _smart_cache is None:
                _smart_cache = SmartCache(
                    backend=backend,
                    max_size=max_size,
                    max_size_bytes=max_size_bytes,
                )
                logger.info("Created global SmartCache instance")

    return _smart_cache
