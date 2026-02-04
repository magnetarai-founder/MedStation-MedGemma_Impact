"""
Integration Guide: Using SmartCache with MagnetarCode Services

This file shows how to integrate the SmartCache system with existing
MagnetarCode services for maximum performance gains.
"""

import asyncio
from pathlib import Path
from typing import Any

from api.services.caching import get_smart_cache


# ============================================================================
# Integration 1: File Operations Service
# ============================================================================


class CachedFileOperationsService:
    """
    Wrapper around FileOperationsService with intelligent caching.

    Caches:
    - File contents
    - File metadata
    - Directory listings
    """

    def __init__(self):
        # Import here to avoid circular dependencies
        from api.services.file_operations import FileOperationsService

        self.file_ops = FileOperationsService()
        self.cache = get_smart_cache()

    async def initialize(self):
        """Initialize cache and file operations."""
        await self.cache.initialize()

    async def read_file(self, file_path: str, workspace_id: str) -> str:
        """
        Read file with caching and prediction.

        Args:
            file_path: Path to file
            workspace_id: Workspace identifier

        Returns:
            File contents
        """
        cache_key = f"file:{file_path}"

        # Check cache
        content = await self.cache.get(cache_key, context=workspace_id)
        if content:
            # Predict and prefetch related files
            predictions = await self.cache.predict_next(cache_key, context=workspace_id, top_k=3)

            # Prefetch in background (fire-and-forget)
            asyncio.create_task(
                self._prefetch_files(predictions, workspace_id)
            )

            return content

        # Cache miss - read from disk
        content = await self.file_ops.read_file(file_path)

        # Cache for future requests (10 min TTL)
        await self.cache.set(cache_key, content, ttl=600, context=workspace_id)

        return content

    async def _prefetch_files(self, file_paths: list[str], workspace_id: str):
        """Prefetch files in background."""
        async def load_file(key: str) -> str:
            file_path = key.replace("file:", "")
            try:
                return await self.file_ops.read_file(file_path)
            except Exception:
                return None

        await self.cache.prefetch(
            keys=file_paths,
            loader_func=load_file,
            context=workspace_id,
            ttl=600
        )

    async def get_directory_listing(self, dir_path: str, workspace_id: str) -> list[dict]:
        """Get directory listing with caching."""
        cache_key = f"dir:{dir_path}"

        # Check cache (shorter TTL for directory listings)
        listing = await self.cache.get(cache_key, context=workspace_id)
        if listing:
            return listing

        # Get from file system
        listing = await self.file_ops.list_directory(dir_path)

        # Cache for 30 seconds
        await self.cache.set(cache_key, listing, ttl=30, context=workspace_id)

        return listing


# ============================================================================
# Integration 2: Semantic Search Service
# ============================================================================


class CachedSemanticSearchService:
    """
    Wrapper around SemanticSearchEngine with caching.

    Caches:
    - Search results
    - File embeddings
    - Query embeddings
    """

    def __init__(self):
        from api.services.semantic_search import SemanticSearchEngine

        self.search_engine = SemanticSearchEngine()
        self.cache = get_smart_cache()

    async def initialize(self):
        """Initialize cache and search engine."""
        await self.cache.initialize()

    async def search(
        self, query: str, workspace_id: str, top_k: int = 10
    ) -> list[dict]:
        """
        Search with caching.

        Args:
            query: Search query
            workspace_id: Workspace identifier
            top_k: Number of results

        Returns:
            Search results
        """
        cache_key = f"search:{query}:{workspace_id}:{top_k}"

        # Check cache (5 min TTL)
        results = await self.cache.get(cache_key)
        if results:
            # Prefetch file contents for top results
            file_paths = [r["file"] for r in results[:3]]
            asyncio.create_task(
                self._prefetch_result_files(file_paths, workspace_id)
            )
            return results

        # Perform search
        results = await self.search_engine.search(query, workspace_id, top_k=top_k)

        # Cache results
        await self.cache.set(cache_key, results, ttl=300)

        return results

    async def get_embedding(self, text: str, cache_ttl: int = 3600) -> list[float]:
        """
        Get text embedding with caching.

        Args:
            text: Text to embed
            cache_ttl: Cache TTL (default: 1 hour)

        Returns:
            Embedding vector
        """
        import hashlib

        # Use hash of text as cache key
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        cache_key = f"embedding:{text_hash}"

        # Check cache
        embedding = await self.cache.get(cache_key)
        if embedding:
            return embedding

        # Compute embedding
        embedding = await self.search_engine.get_embedding(text)

        # Cache (embeddings are expensive to compute)
        await self.cache.set(cache_key, embedding, ttl=cache_ttl)

        return embedding

    async def _prefetch_result_files(self, file_paths: list[str], workspace_id: str):
        """Prefetch file contents for search results."""
        from api.services.file_operations import FileOperationsService

        file_ops = FileOperationsService()

        async def load_file(key: str) -> str:
            file_path = key.replace("file:", "")
            try:
                return await file_ops.read_file(file_path)
            except Exception:
                return None

        await self.cache.prefetch(
            keys=[f"file:{fp}" for fp in file_paths],
            loader_func=load_file,
            context=workspace_id,
            ttl=600
        )


# ============================================================================
# Integration 3: Agent Executor with Context Prefetching
# ============================================================================


class CachedAgentExecutor:
    """
    Agent executor with intelligent context caching and prefetching.

    Automatically prefetches likely-needed files when agent starts a task.
    """

    def __init__(self):
        from api.services.agent_executor import AgentExecutor

        self.agent = AgentExecutor()
        self.cache = get_smart_cache()

    async def initialize(self):
        """Initialize cache and agent."""
        await self.cache.initialize()

    async def execute_task(
        self, task: str, workspace_id: str, context: dict | None = None
    ) -> dict:
        """
        Execute agent task with smart caching.

        Args:
            task: Task description
            workspace_id: Workspace identifier
            context: Additional context

        Returns:
            Execution result
        """
        # Extract mentioned files from task
        mentioned_files = self._extract_file_mentions(task)

        # Prefetch mentioned files and predictions
        if mentioned_files:
            await self._prefetch_task_context(mentioned_files, workspace_id)

        # Execute agent task
        result = await self.agent.execute(task, context or {})

        return result

    def _extract_file_mentions(self, task: str) -> list[str]:
        """Extract file paths mentioned in task description."""
        import re

        # Simple regex to find file paths (can be improved)
        pattern = r'[/\w.-]+\.(py|js|ts|md|json|yaml|yml|txt)'
        matches = re.findall(pattern, task)

        return [f"file:{m}" for m in matches]

    async def _prefetch_task_context(
        self, mentioned_files: list[str], workspace_id: str
    ):
        """Prefetch files and predictions for task context."""
        from api.services.file_operations import FileOperationsService

        file_ops = FileOperationsService()

        # Prefetch mentioned files
        async def load_file(key: str) -> str:
            file_path = key.replace("file:", "")
            try:
                return await file_ops.read_file(file_path)
            except Exception:
                return None

        await self.cache.prefetch(
            keys=mentioned_files,
            loader_func=load_file,
            context=workspace_id,
            ttl=600
        )

        # Get predictions for each mentioned file
        all_predictions = []
        for file_key in mentioned_files:
            predictions = await self.cache.predict_next(
                file_key,
                context=workspace_id,
                top_k=3
            )
            all_predictions.extend(predictions)

        # Prefetch predicted files
        if all_predictions:
            await self.cache.prefetch(
                keys=all_predictions[:10],  # Limit to prevent overload
                loader_func=load_file,
                context=workspace_id,
                ttl=600
            )


# ============================================================================
# Integration 4: Workspace Session Manager with Cache Warming
# ============================================================================


class CachedWorkspaceSessionManager:
    """
    Workspace session manager with automatic cache warming.

    Warms cache when workspace is opened based on usage patterns.
    """

    def __init__(self):
        from api.services.workspace_session import WorkspaceSessionManager

        self.session_manager = WorkspaceSessionManager()
        self.cache = get_smart_cache()

    async def initialize(self):
        """Initialize cache."""
        await self.cache.initialize()

    async def open_workspace(
        self, user_id: str, workspace_root: str, workspace_id: str
    ) -> dict:
        """
        Open workspace with cache warming.

        Args:
            user_id: User identifier
            workspace_root: Path to workspace
            workspace_id: Workspace identifier

        Returns:
            Session information
        """
        # Create/get session
        session_id = self.session_manager.get_or_create_for_workspace(
            user_id, workspace_root
        )

        # Warm cache in background
        asyncio.create_task(
            self._warm_workspace_cache(workspace_id, workspace_root)
        )

        return {
            "session_id": session_id,
            "workspace_root": workspace_root,
            "cache_warming": True
        }

    async def _warm_workspace_cache(self, workspace_id: str, workspace_root: str):
        """Warm cache for workspace."""
        from api.services.file_operations import FileOperationsService

        file_ops = FileOperationsService()

        async def load_file(file_path: str) -> str:
            try:
                return await file_ops.read_file(file_path)
            except Exception:
                return None

        # Get common file patterns for this workspace type
        patterns = self._detect_workspace_patterns(workspace_root)

        # Warm cache
        files_cached = await self.cache.warm_cache(
            workspace_id=workspace_id,
            workspace_root=workspace_root,
            loader_func=load_file,
            file_patterns=patterns
        )

        print(f"Warmed cache with {files_cached} files for {workspace_id}")

    def _detect_workspace_patterns(self, workspace_root: str) -> list[str]:
        """Detect workspace type and return appropriate file patterns."""
        # Check for common project files
        patterns = []

        root_path = Path(workspace_root)

        if (root_path / "package.json").exists():
            # Node.js project
            patterns.extend(["*.js", "*.ts", "*.jsx", "*.tsx"])
        elif (root_path / "requirements.txt").exists() or (root_path / "pyproject.toml").exists():
            # Python project
            patterns.extend(["*.py"])
        elif (root_path / "Cargo.toml").exists():
            # Rust project
            patterns.extend(["*.rs"])
        elif (root_path / "go.mod").exists():
            # Go project
            patterns.extend(["*.go"])

        # Always include common files
        patterns.extend(["*.md", "*.json", "*.yaml", "*.yml"])

        return patterns


# ============================================================================
# Integration 5: Chat Memory with LLM Context Caching
# ============================================================================


class CachedChatMemoryService:
    """
    Chat memory service with LLM context caching.

    Caches:
    - Conversation summaries
    - Referenced file contents
    - LLM context windows
    """

    def __init__(self):
        from api.services.chat_memory import ChatMemoryService

        self.memory = ChatMemoryService()
        self.cache = get_smart_cache()

    async def initialize(self):
        """Initialize cache."""
        await self.cache.initialize()

    async def get_conversation_context(
        self, conversation_id: str, workspace_id: str
    ) -> dict:
        """
        Get conversation context with caching.

        Args:
            conversation_id: Conversation identifier
            workspace_id: Workspace identifier

        Returns:
            Conversation context
        """
        cache_key = f"context:{conversation_id}"

        # Check cache
        context = await self.cache.get(cache_key, context=workspace_id)
        if context:
            return context

        # Build context
        context = await self.memory.get_conversation_context(conversation_id)

        # Cache context (shorter TTL as conversations are active)
        await self.cache.set(cache_key, context, ttl=180, context=workspace_id)

        return context

    async def prefetch_referenced_files(
        self, conversation_id: str, workspace_id: str
    ):
        """Prefetch files referenced in conversation."""
        from api.services.file_operations import FileOperationsService

        file_ops = FileOperationsService()

        # Get referenced files from conversation
        context = await self.get_conversation_context(conversation_id, workspace_id)
        referenced_files = context.get("referenced_files", [])

        if not referenced_files:
            return

        # Prefetch file contents
        async def load_file(key: str) -> str:
            file_path = key.replace("file:", "")
            try:
                return await file_ops.read_file(file_path)
            except Exception:
                return None

        await self.cache.prefetch(
            keys=[f"file:{f}" for f in referenced_files],
            loader_func=load_file,
            context=workspace_id,
            ttl=600
        )


# ============================================================================
# Example: Complete Integration
# ============================================================================


async def example_complete_integration():
    """Example showing complete integration of SmartCache."""

    # Initialize all cached services
    file_service = CachedFileOperationsService()
    search_service = CachedSemanticSearchService()
    agent_service = CachedAgentExecutor()
    workspace_service = CachedWorkspaceSessionManager()

    await file_service.initialize()
    await search_service.initialize()
    await agent_service.initialize()
    await workspace_service.initialize()

    workspace_id = "ws_myproject"
    workspace_root = "/path/to/myproject"
    user_id = "user_123"

    # 1. Open workspace (automatically warms cache)
    session = await workspace_service.open_workspace(
        user_id, workspace_root, workspace_id
    )
    print(f"Opened workspace: {session}")

    # 2. Read a file (caches and predicts next files)
    content = await file_service.read_file(
        f"{workspace_root}/main.py",
        workspace_id
    )
    print(f"Read file, length: {len(content)}")

    # 3. Search for code (caches results and embeddings)
    results = await search_service.search(
        "authentication implementation",
        workspace_id
    )
    print(f"Search found {len(results)} results")

    # 4. Execute agent task (prefetches context)
    result = await agent_service.execute_task(
        "Refactor the login function in auth/login.py",
        workspace_id
    )
    print(f"Agent result: {result}")

    # 5. Check cache statistics
    cache = get_smart_cache()
    stats = cache.get_stats()
    print(f"\nCache Statistics:")
    print(f"  Hit Rate: {stats.hit_rate:.2f}%")
    print(f"  Size: {stats.size} entries")
    print(f"  Predictions: {stats.predictions}")

    # Save prediction model for next session
    cache.save_model()


if __name__ == "__main__":
    asyncio.run(example_complete_integration())
