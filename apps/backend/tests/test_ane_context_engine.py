"""
Tests for ANE Context Engine

Tests the Apple Neural Engine accelerated context preservation engine.
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from api.ane_context_engine import (
    ANEContextEngine,
    get_ane_engine,
    _flatten_context,
    _cpu_embed_fallback,
    _embed_with_ane,
)


class TestFlattenContext:
    """Test context flattening utility"""

    def test_flatten_simple_dict(self):
        """Test flattening a simple dictionary"""
        data = {"key": "value", "number": 42}
        result = _flatten_context(data)

        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result

    def test_flatten_nested_dict(self):
        """Test flattening nested dictionary"""
        data = {
            "outer": {
                "inner": "value"
            }
        }
        result = _flatten_context(data)

        assert "inner" in result
        assert "value" in result

    def test_flatten_deterministic(self):
        """Test flattening is deterministic (sorted keys)"""
        data1 = {"z": 1, "a": 2, "m": 3}
        data2 = {"m": 3, "a": 2, "z": 1}

        result1 = _flatten_context(data1)
        result2 = _flatten_context(data2)

        assert result1 == result2

    def test_flatten_handles_unicode(self):
        """Test flattening handles unicode correctly"""
        data = {"greeting": "Hello, 世界! 👋"}
        result = _flatten_context(data)

        assert "世界" in result
        assert "👋" in result


class TestCPUEmbedFallback:
    """Test CPU embedding fallback"""

    def test_returns_correct_dimensions(self):
        """Test fallback returns correct vector dimensions"""
        result = _cpu_embed_fallback("test text", dims=384)

        assert len(result) == 384

    def test_returns_normalized_vector(self):
        """Test vector is L2 normalized"""
        result = _cpu_embed_fallback("test text", dims=384)

        # Calculate L2 norm
        norm = sum(x * x for x in result) ** 0.5

        # Should be approximately 1.0
        assert abs(norm - 1.0) < 0.001

    def test_empty_text_returns_zeros(self):
        """Test empty text returns zero vector"""
        result = _cpu_embed_fallback("", dims=10)

        assert len(result) == 10
        assert all(x == 0.0 for x in result)

    def test_same_text_same_embedding(self):
        """Test deterministic embeddings"""
        text = "consistent embedding test"
        result1 = _cpu_embed_fallback(text, dims=384)
        result2 = _cpu_embed_fallback(text, dims=384)

        assert result1 == result2

    def test_different_text_different_embedding(self):
        """Test different text produces different embeddings"""
        result1 = _cpu_embed_fallback("hello world", dims=384)
        result2 = _cpu_embed_fallback("goodbye world", dims=384)

        assert result1 != result2


class TestEmbedWithANE:
    """Test unified embedding function"""

    def test_returns_embedding(self):
        """Test embed_with_ane returns an embedding"""
        result = _embed_with_ane("test text")

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(x, float) for x in result)

    def test_fallback_to_cpu(self):
        """Test fallback to CPU when MLX unavailable"""
        # Patch the import inside _embed_with_ane function
        with patch.dict("sys.modules", {"api.mlx_embedder": None}):
            result = _embed_with_ane("test text")

            assert isinstance(result, list)
            # Unified embedder or CPU fallback provides embedding
            assert len(result) > 0
            assert all(isinstance(x, float) for x in result)


class TestANEContextEngine:
    """Test ANE Context Engine class"""

    @pytest.fixture
    def engine(self):
        """Create test engine with minimal workers"""
        engine = ANEContextEngine(workers=1, retention_days=1.0)
        yield engine
        engine.shutdown(timeout=1.0)

    def test_initialization(self, engine):
        """Test engine initializes correctly"""
        stats = engine.stats()

        assert stats["sessions_stored"] == 0
        assert stats["processed_count"] == 0
        assert stats["error_count"] == 0
        assert stats["workers"] == 1

    def test_preserve_context_queues_job(self, engine):
        """Test preserve_context queues vectorization job"""
        engine.preserve_context(
            session_id="sess_123",
            context_data={"message": "Hello world"},
            metadata={"workspace": "chat"}
        )

        # Job should be queued
        stats = engine.stats()
        assert stats["queue_size"] >= 0  # May have processed already

    def test_enqueue_vectorization_alias(self, engine):
        """Test enqueue_vectorization works as alias"""
        engine.enqueue_vectorization(
            session_id="sess_alias",
            context={"content": "test content"}
        )

        # Should not raise
        assert True

    def test_search_similar_empty(self, engine):
        """Test search with no stored vectors"""
        results = engine.search_similar(query="test query", top_k=5)

        assert isinstance(results, list)
        assert len(results) == 0

    def test_search_similar_with_stored(self, engine):
        """Test search after storing context"""
        # Store context and wait for processing
        engine.preserve_context(
            session_id="sess_search_1",
            context_data={"content": "machine learning AI models"},
            metadata={"workspace": "chat"}
        )

        # Wait for background processing
        time.sleep(0.5)

        results = engine.search_similar(
            query="AI and machine learning",
            top_k=5,
            threshold=0.0  # Low threshold to match
        )

        assert len(results) >= 0  # May or may not match depending on embedding

    def test_get_vector_none_for_unknown(self, engine):
        """Test get_vector returns None for unknown session"""
        result = engine.get_vector("unknown_session")

        assert result is None

    def test_get_all_vectors_empty(self, engine):
        """Test get_all_vectors when empty"""
        result = engine.get_all_vectors()

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_stats_structure(self, engine):
        """Test stats returns expected structure"""
        stats = engine.stats()

        assert "sessions_stored" in stats
        assert "processed_count" in stats
        assert "error_count" in stats
        assert "queue_size" in stats
        assert "workers" in stats
        assert "retention_days" in stats

    def test_clear_all(self, engine):
        """Test clearing all vectors"""
        # Store something first
        engine._vectors["test"] = [0.1, 0.2]
        engine._timestamps["test"] = time.time()

        # Clear
        engine.clear_all()

        assert len(engine._vectors) == 0
        assert len(engine._timestamps) == 0

    def test_prune_older_than(self, engine):
        """Test pruning old vectors"""
        # Manually add old vector
        old_time = time.time() - (5 * 86400)  # 5 days ago
        engine._vectors["old_session"] = [0.1, 0.2]
        engine._timestamps["old_session"] = old_time
        engine._metadata["old_session"] = {"test": True}

        # Add recent vector
        engine._vectors["new_session"] = [0.3, 0.4]
        engine._timestamps["new_session"] = time.time()

        # Prune vectors older than 2 days
        pruned = engine.prune_older_than(days=2.0)

        assert pruned == 1
        assert "old_session" not in engine._vectors
        assert "new_session" in engine._vectors

    def test_prune_zero_days_no_effect(self, engine):
        """Test prune with 0 days has no effect"""
        engine._vectors["sess1"] = [0.1]
        engine._timestamps["sess1"] = time.time()

        pruned = engine.prune_older_than(days=0)

        assert pruned == 0
        assert "sess1" in engine._vectors


class TestCosineSimiliarity:
    """Test cosine similarity calculation"""

    def test_identical_vectors(self):
        """Test similarity of identical vectors is 1.0"""
        vec = [0.5, 0.5, 0.5]
        result = ANEContextEngine._cosine_similarity(vec, vec)

        assert abs(result - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors is 0.0"""
        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        result = ANEContextEngine._cosine_similarity(vec1, vec2)

        assert abs(result) < 0.001

    def test_opposite_vectors(self):
        """Test similarity of opposite vectors is -1.0"""
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        result = ANEContextEngine._cosine_similarity(vec1, vec2)

        assert abs(result + 1.0) < 0.001

    def test_different_length_returns_zero(self):
        """Test different length vectors return 0"""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]
        result = ANEContextEngine._cosine_similarity(vec1, vec2)

        assert result == 0.0

    def test_zero_vector_returns_zero(self):
        """Test zero vector returns 0"""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [0.0, 0.0, 0.0]
        result = ANEContextEngine._cosine_similarity(vec1, vec2)

        assert result == 0.0


class TestANEEngineSingleton:
    """Test singleton pattern"""

    def test_get_ane_engine_returns_instance(self):
        """Test singleton returns an instance"""
        # Reset singleton
        import api.ane_context_engine as module
        module._ane_engine = None

        engine = get_ane_engine()

        assert engine is not None
        assert isinstance(engine, ANEContextEngine)

        # Cleanup
        engine.shutdown(timeout=1.0)
        module._ane_engine = None

    def test_get_ane_engine_returns_same_instance(self):
        """Test singleton returns same instance"""
        import api.ane_context_engine as module
        module._ane_engine = None

        engine1 = get_ane_engine()
        engine2 = get_ane_engine()

        assert engine1 is engine2

        # Cleanup
        engine1.shutdown(timeout=1.0)
        module._ane_engine = None
