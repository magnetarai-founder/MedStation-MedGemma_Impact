# Smart Caching System for MagnetarCode

An intelligent, predictive caching system designed for MagnetarCode's AI-powered development environment.

## Features

### Core Capabilities
- **Predictive File Loading**: Uses Markov chains to predict what files users will need next
- **Pre-warming**: Automatically warms caches when workspaces are opened
- **Intelligent Prefetch**: Prefetches related context for LLM calls
- **Smart Eviction**: LRU + frequency-based eviction strategy
- **Multiple Backends**: Memory, SQLite, and Redis-compatible
- **Background Refresh**: Automatically refreshes stale entries

### What Gets Cached
- File contents
- Embeddings (vector representations)
- Search results
- LLM context
- Workspace metadata
- User preferences

## Quick Start

```python
from api.services.caching import get_smart_cache

# Initialize cache
cache = get_smart_cache()
await cache.initialize()

# Basic operations
await cache.set("key", {"data": "value"}, ttl=300)
value = await cache.get("key")

# Cleanup
await cache.shutdown()
```

## Architecture

### Cache Entry Structure
```python
@dataclass
class CacheEntry:
    key: str                 # Cache key
    value: Any              # Cached value (JSON-serializable)
    access_count: int       # Number of accesses (for frequency tracking)
    last_accessed: float    # Timestamp of last access (for LRU)
    created_at: float       # Creation timestamp
    ttl: int               # Time to live in seconds
    size_bytes: int        # Approximate size for memory management
```

### Statistics
```python
stats = cache.get_stats()
# Returns:
# {
#     "hits": 150,
#     "misses": 50,
#     "hit_rate": 75.0,
#     "evictions": 10,
#     "predictions": 30,
#     "prediction_accuracy": 80.0,
#     "size": 1000,
#     "utilization": 10.0
# }
```

## Usage Examples

### 1. File Caching with Prediction

```python
workspace_id = "ws_myproject"

# Cache file as user accesses it
await cache.set(
    f"file:/project/main.py",
    file_content,
    ttl=600,
    context=workspace_id
)

# Predict next files user will need
predictions = await cache.predict_next(
    "file:/project/main.py",
    context=workspace_id,
    top_k=5
)
# Returns: ["file:/project/utils.py", "file:/project/config.py", ...]
```

### 2. Workspace Cache Warming

```python
async def load_file(file_path: str) -> str:
    """Load file content from disk."""
    with open(file_path, 'r') as f:
        return f.read()

# Warm cache when workspace opens
files_cached = await cache.warm_cache(
    workspace_id="ws_myproject",
    workspace_root="/path/to/project",
    loader_func=load_file,
    file_patterns=["*.py", "*.js", "*.ts"]
)
```

### 3. Intelligent Prefetching

```python
# User is editing a controller file
current_file = "/app/controllers/user_controller.py"

# Prefetch related files (models, views, tests)
related_files = [
    "/app/models/user.py",
    "/app/views/user_view.py",
    "/app/tests/test_user_controller.py"
]

prefetched = await cache.prefetch(
    keys=[f"file:{f}" for f in related_files],
    loader_func=load_file,
    context="ws_app",
    ttl=600
)
```

### 4. LLM Context Caching

```python
# Cache embeddings
await cache.set(
    f"embedding:/project/auth/login.py",
    {
        "file": "/project/auth/login.py",
        "embedding": [0.1, 0.2, ...],  # 768-dim vector
        "timestamp": "2024-01-01"
    },
    ttl=3600
)

# Cache search results
await cache.set(
    f"search:authentication implementation",
    [
        {"file": "/auth/login.py", "score": 0.95},
        {"file": "/auth/session.py", "score": 0.87}
    ],
    ttl=300
)
```

### 5. Backend Selection

```python
# Memory backend (default, fast but volatile)
cache = get_smart_cache(
    backend=CacheBackend.MEMORY,
    max_size=10000,
    max_size_bytes=100 * 1024 * 1024  # 100MB
)

# SQLite backend (persistent, survives restarts)
cache = get_smart_cache(
    backend=CacheBackend.SQLITE,
    max_size=50000
)

# Redis backend (distributed, shared across instances)
cache = get_smart_cache(
    backend=CacheBackend.REDIS,
    redis_url="redis://localhost:6379/0"
)
```

## Eviction Strategy

The cache uses a hybrid LRU + frequency-based eviction:

```python
eviction_score = (recency_score * 0.6) + (frequency_score * 0.4)
```

- **Recency (60%)**: More recently accessed entries have higher scores
- **Frequency (40%)**: More frequently accessed entries have higher scores
- **Result**: Entries with low scores are evicted first

This strategy is superior to pure LRU because:
- Frequently used files stay cached even if not accessed recently
- Recently accessed files are preferred over stale entries
- Balances short-term and long-term access patterns

## Prediction Model

Uses a Markov chain to learn access patterns:

```python
# How it works:
# 1. Records transitions: file_a -> file_b
# 2. Builds probability distribution
# 3. Predicts most likely next files

# Example pattern learned:
# main.py -> utils.py (80% of the time)
# main.py -> config.py (20% of the time)

predictions = await cache.predict_next("main.py")
# Returns: ["utils.py", "config.py"]
```

### Model Persistence

```python
# Save model to disk
cache.save_model()  # Saves to ~/.magnetarcode/data/prediction_model.pkl

# Load model on startup
cache.load_model()
```

## Background Refresh

Automatically refreshes stale entries:

```python
# Configure refresh behavior
await cache.start_background_refresh(
    refresh_interval=60,      # Check every 60 seconds
    stale_threshold=0.8       # Refresh when 80% of TTL elapsed
)
```

The background task:
1. Runs every `refresh_interval` seconds
2. Identifies entries near expiration (> `stale_threshold` * TTL)
3. Logs stale entries (can be extended to trigger refresh callbacks)

## Performance Characteristics

### Memory Backend
- **Get**: O(1) - Hash table lookup
- **Set**: O(1) average, O(n) worst case (eviction)
- **Eviction**: O(n) - Scans all entries for lowest score
- **Memory**: Up to `max_size_bytes` (configurable)

### SQLite Backend
- **Get**: O(log n) - Indexed lookup
- **Set**: O(log n) - Indexed insert
- **Eviction**: O(log n) - Indexed query
- **Persistence**: Yes - Survives restarts
- **Disk**: Grows with usage, auto-vacuums

### Redis Backend (planned)
- **Get**: O(1) - Redis GET
- **Set**: O(1) - Redis SET
- **Eviction**: O(1) - Redis handles it
- **Distributed**: Yes - Shared across instances

## Integration Examples

### With File Operations Service

```python
from api.services.file_operations import FileOperationsService
from api.services.caching import get_smart_cache

class CachedFileService:
    def __init__(self):
        self.file_service = FileOperationsService()
        self.cache = get_smart_cache()

    async def read_file(self, file_path: str, workspace_id: str) -> str:
        # Check cache first
        cache_key = f"file:{file_path}"
        content = await self.cache.get(cache_key, context=workspace_id)

        if content:
            return content

        # Cache miss - read from disk
        content = await self.file_service.read_file(file_path)

        # Cache for future requests
        await self.cache.set(cache_key, content, ttl=600, context=workspace_id)

        return content
```

### With Semantic Search

```python
from api.services.semantic_search import SemanticSearchEngine
from api.services.caching import get_smart_cache

class CachedSearchEngine:
    def __init__(self):
        self.search_engine = SemanticSearchEngine()
        self.cache = get_smart_cache()

    async def search(self, query: str, workspace_id: str) -> list[dict]:
        # Check cache
        cache_key = f"search:{query}:{workspace_id}"
        results = await self.cache.get(cache_key)

        if results:
            return results

        # Perform search
        results = await self.search_engine.search(query, workspace_id)

        # Cache results
        await self.cache.set(cache_key, results, ttl=300)

        return results
```

### With Agent Executor

```python
from api.services.agent_executor import AgentExecutor
from api.services.caching import get_smart_cache

class AgentWithCache:
    def __init__(self):
        self.agent = AgentExecutor()
        self.cache = get_smart_cache()

    async def execute_task(self, task: str, context: dict) -> dict:
        # Prefetch likely needed files based on task
        if "edit" in task.lower():
            mentioned_files = self._extract_files(task)
            predictions = []

            for file in mentioned_files:
                preds = await self.cache.predict_next(
                    f"file:{file}",
                    context=context.get("workspace_id"),
                    top_k=3
                )
                predictions.extend(preds)

            # Prefetch predicted files
            await self.cache.prefetch(
                keys=predictions,
                loader_func=self._load_file,
                context=context.get("workspace_id")
            )

        # Execute agent task
        return await self.agent.execute(task, context)
```

## Configuration

### Environment Variables

```bash
# Cache backend
CACHE_BACKEND=memory  # memory, sqlite, redis

# Memory backend
CACHE_MAX_SIZE=10000
CACHE_MAX_SIZE_BYTES=104857600  # 100MB

# SQLite backend
CACHE_DB_PATH=~/.magnetarcode/data/smart_cache.db

# Redis backend
CACHE_REDIS_URL=redis://localhost:6379/0

# Background refresh
CACHE_REFRESH_INTERVAL=60
CACHE_STALE_THRESHOLD=0.8
```

### Programmatic Configuration

```python
from api.services.caching import SmartCache, CacheBackend

cache = SmartCache(
    backend=CacheBackend.MEMORY,
    max_size=10000,
    max_size_bytes=100 * 1024 * 1024,
    db_path=Path("~/.magnetarcode/data/cache.db"),
    redis_url="redis://localhost:6379/0"
)
```

## Best Practices

### 1. Use Context for Workspace Isolation
```python
# Good - predictions are workspace-specific
await cache.set(key, value, context=workspace_id)

# Bad - predictions mixed across workspaces
await cache.set(key, value)
```

### 2. Choose Appropriate TTLs
```python
# File contents - medium TTL (files change)
await cache.set("file:main.py", content, ttl=600)  # 10 minutes

# Embeddings - longer TTL (expensive to compute)
await cache.set("embedding:main.py", embedding, ttl=3600)  # 1 hour

# Search results - shorter TTL (codebase changes)
await cache.set("search:query", results, ttl=300)  # 5 minutes
```

### 3. Warm Cache on Workspace Open
```python
# Improve initial user experience
await cache.warm_cache(
    workspace_id=workspace_id,
    workspace_root=workspace_root,
    loader_func=load_file,
    file_patterns=["*.py", "*.js", "*.ts", "*.md"]
)
```

### 4. Prefetch Predictively
```python
# When user opens a file, prefetch related files
current_file = user_opened_file()
predictions = await cache.predict_next(f"file:{current_file}", context=workspace_id)
await cache.prefetch(predictions, load_file, context=workspace_id)
```

### 5. Monitor Cache Performance
```python
# Regularly check stats
stats = cache.get_stats()
if stats.hit_rate < 50:
    logger.warning(f"Low cache hit rate: {stats.hit_rate}%")
```

## Testing

Run the examples:
```bash
cd /Users/indiedevhipps/Documents/MagnetarCode/apps/backend
python -m api.services.caching.examples
```

## Future Enhancements

- [ ] Redis backend implementation
- [ ] Distributed cache invalidation
- [ ] Machine learning-based prediction (beyond Markov chains)
- [ ] Cache partitioning by workspace
- [ ] Automatic refresh callbacks
- [ ] Cache compression for large values
- [ ] Multi-level caching (L1/L2/L3)
- [ ] Cache warming based on time-of-day patterns
- [ ] Integration with VSCode extension for preloading

## License

Part of MagnetarCode - see main project license.
