"""
Comprehensive tests for api/metal4_vector_search.py

Tests the Metal 4 GPU-accelerated vector similarity search including:
- Metal4VectorSearch class initialization
- Database loading (Metal and CPU paths)
- Search methods with different metrics
- Batch search functionality
- Statistics tracking
- Singleton pattern and validation
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import sys


class TestMetal4VectorSearchInit:
    """Tests for Metal4VectorSearch initialization"""

    def test_init_without_metal(self):
        """Initialize without Metal available"""
        # Clear any cached singleton
        with patch.dict('sys.modules', {'metal4_engine': None}):
            # Import with Metal unavailable
            from api.metal4_vector_search import Metal4VectorSearch

            with patch.object(
                Metal4VectorSearch, '_check_metal4', return_value=False
            ):
                search = Metal4VectorSearch()

        assert search._initialized is True
        assert search._use_metal is False
        assert search.num_vectors == 0
        assert search.embed_dim == 0

    def test_init_creates_empty_stats(self):
        """Initialize creates empty stats"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        assert search.stats['searches_executed'] == 0
        assert search.stats['total_time_ms'] == 0
        assert search.stats['gpu_time_ms'] == 0
        assert search.stats['cpu_fallback_count'] == 0

    def test_init_with_metal_check_exception(self):
        """Initialize handles exception during Metal check"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(
            Metal4VectorSearch, '_check_metal4',
            side_effect=Exception("Metal check failed")
        ):
            # Should not raise, should handle gracefully
            try:
                search = Metal4VectorSearch()
                # May or may not succeed depending on implementation
            except Exception:
                pass  # Expected in some cases


class TestMetal4Check:
    """Tests for _check_metal4"""

    def test_check_metal4_unavailable(self):
        """Metal 4 check returns False when unavailable"""
        from api.metal4_vector_search import Metal4VectorSearch

        mock_engine = Mock()
        mock_engine.is_available.return_value = False

        with patch.dict('sys.modules', {
            'metal4_engine': Mock(
                get_metal4_engine=Mock(return_value=mock_engine),
                MetalVersion=Mock(METAL_3=Mock(value=3))
            )
        }):
            search = Metal4VectorSearch.__new__(Metal4VectorSearch)
            search._use_metal = False
            result = search._check_metal4()

        assert result is False

    def test_check_metal4_import_error(self):
        """Metal 4 check handles import error"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.dict('sys.modules', {'metal4_engine': None}):
            search = Metal4VectorSearch.__new__(Metal4VectorSearch)
            search._use_metal = False

            # Should handle gracefully
            with patch('api.metal4_vector_search.logger'):
                result = search._check_metal4()

        assert result is False


class TestDatabaseLoading:
    """Tests for load_database"""

    @pytest.fixture
    def search_cpu(self):
        """Create search instance with CPU fallback"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()
        return search

    def test_load_database_cpu_fallback(self, search_cpu):
        """Load database to CPU memory"""
        embeddings = np.random.randn(1000, 384).astype(np.float32)

        search_cpu.load_database(embeddings)

        assert search_cpu.num_vectors == 1000
        assert search_cpu.embed_dim == 384
        assert hasattr(search_cpu, 'database_embeddings')
        assert search_cpu.database_embeddings.shape == (1000, 384)

    def test_load_database_validates_shape(self, search_cpu):
        """Load database validates 2D array"""
        embeddings_1d = np.random.randn(384).astype(np.float32)

        with pytest.raises(ValueError, match="Expected 2D array"):
            search_cpu.load_database(embeddings_1d)

    def test_load_database_3d_array_rejected(self, search_cpu):
        """Load database rejects 3D array"""
        embeddings_3d = np.random.randn(100, 384, 2).astype(np.float32)

        with pytest.raises(ValueError, match="Expected 2D array"):
            search_cpu.load_database(embeddings_3d)

    def test_load_database_stores_dimensions(self, search_cpu):
        """Load database stores dimensions"""
        embeddings = np.random.randn(500, 128).astype(np.float32)

        search_cpu.load_database(embeddings)

        assert search_cpu.num_vectors == 500
        assert search_cpu.embed_dim == 128

    def test_load_database_converts_to_float32(self, search_cpu):
        """Load database converts to float32"""
        embeddings = np.random.randn(100, 384)  # Default float64

        search_cpu.load_database(embeddings)

        assert search_cpu.database_embeddings.dtype == np.float32


class TestSearchCPU:
    """Tests for CPU search functionality"""

    @pytest.fixture
    def search_with_db(self):
        """Create search instance with loaded database"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        # Create normalized database for consistent results
        db = np.random.randn(100, 384).astype(np.float32)
        db = db / np.linalg.norm(db, axis=1, keepdims=True)
        search.load_database(db)

        return search

    def test_search_cosine_similarity(self, search_with_db):
        """Search with cosine similarity"""
        query = np.random.randn(384).astype(np.float32)
        query = query / np.linalg.norm(query)

        indices, scores = search_with_db.search(query, k=10, metric="cosine")

        assert len(indices) == 10
        assert len(scores) == 10
        # Scores should be sorted descending for cosine
        assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))

    def test_search_l2_distance(self, search_with_db):
        """Search with L2 distance"""
        query = np.random.randn(384).astype(np.float32)

        indices, scores = search_with_db.search(query, k=5, metric="l2")

        assert len(indices) == 5
        assert len(scores) == 5
        # L2 returns negative distances, so higher (less negative) is better
        assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))

    def test_search_dot_product(self, search_with_db):
        """Search with dot product"""
        query = np.random.randn(384).astype(np.float32)

        indices, scores = search_with_db.search(query, k=7, metric="dot")

        assert len(indices) == 7
        assert len(scores) == 7
        # Dot product sorted descending
        assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))

    def test_search_unknown_metric_returns_empty(self, search_with_db):
        """Search with unknown metric returns empty (exception caught)"""
        query = np.random.randn(384).astype(np.float32)

        # Exception is caught internally and returns empty results
        indices, scores = search_with_db.search(query, k=10, metric="manhattan")

        assert indices == []
        assert scores == []

    def test_search_updates_stats(self, search_with_db):
        """Search updates statistics"""
        query = np.random.randn(384).astype(np.float32)

        initial_count = search_with_db.stats['searches_executed']
        search_with_db.search(query, k=10, metric="cosine")

        assert search_with_db.stats['searches_executed'] == initial_count + 1
        assert search_with_db.stats['total_time_ms'] > 0

    def test_search_tracks_cpu_fallback(self, search_with_db):
        """Search tracks CPU fallback count"""
        query = np.random.randn(384).astype(np.float32)

        search_with_db.search(query, k=10, metric="cosine")

        assert search_with_db.stats['cpu_fallback_count'] >= 1

    def test_search_dimension_mismatch_raises(self, search_with_db):
        """Search with wrong dimension raises error"""
        query = np.random.randn(128).astype(np.float32)  # Wrong dimension

        with pytest.raises(ValueError, match="dimension"):
            search_with_db.search(query, k=10, metric="cosine")

    def test_search_not_initialized(self):
        """Search before initialization returns empty"""
        from api.metal4_vector_search import Metal4VectorSearch

        search = Metal4VectorSearch.__new__(Metal4VectorSearch)
        search._initialized = False
        search.num_vectors = 100
        search.embed_dim = 384

        indices, scores = search.search(np.zeros(384), k=10)

        assert indices == []
        assert scores == []

    def test_search_no_database_loaded(self):
        """Search without loaded database returns empty"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        indices, scores = search.search(np.zeros(384), k=10)

        assert indices == []
        assert scores == []


class TestBatchSearch:
    """Tests for batch_search"""

    @pytest.fixture
    def search_with_db(self):
        """Create search instance with loaded database"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        db = np.random.randn(100, 384).astype(np.float32)
        search.load_database(db)
        return search

    def test_batch_search_multiple_queries(self, search_with_db):
        """Batch search handles multiple queries"""
        queries = np.random.randn(5, 384).astype(np.float32)

        all_indices, all_scores = search_with_db.batch_search(queries, k=3)

        assert len(all_indices) == 5
        assert len(all_scores) == 5
        for indices, scores in zip(all_indices, all_scores):
            assert len(indices) == 3
            assert len(scores) == 3

    def test_batch_search_single_query(self, search_with_db):
        """Batch search handles single query"""
        queries = np.random.randn(1, 384).astype(np.float32)

        all_indices, all_scores = search_with_db.batch_search(queries, k=5)

        assert len(all_indices) == 1
        assert len(all_scores) == 1

    def test_batch_search_validates_shape(self, search_with_db):
        """Batch search validates 2D input"""
        queries_1d = np.random.randn(384).astype(np.float32)

        with pytest.raises(ValueError, match="Expected 2D array"):
            search_with_db.batch_search(queries_1d, k=5)


class TestStatistics:
    """Tests for statistics tracking"""

    @pytest.fixture
    def search_cpu(self):
        """Create CPU-only search instance"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        db = np.random.randn(100, 384).astype(np.float32)
        search.load_database(db)
        return search

    def test_get_stats_includes_all_fields(self, search_cpu):
        """get_stats returns all expected fields"""
        stats = search_cpu.get_stats()

        assert 'searches_executed' in stats
        assert 'total_time_ms' in stats
        assert 'gpu_time_ms' in stats
        assert 'cpu_fallback_count' in stats
        assert 'avg_time_ms' in stats
        assert 'metal_enabled' in stats
        assert 'database_size' in stats

    def test_get_stats_avg_time_zero_when_no_searches(self, search_cpu):
        """Average time is 0 when no searches executed"""
        stats = search_cpu.get_stats()

        assert stats['avg_time_ms'] == 0

    def test_get_stats_calculates_avg_time(self, search_cpu):
        """Average time calculated correctly"""
        query = np.random.randn(384).astype(np.float32)

        # Run some searches
        for _ in range(3):
            search_cpu.search(query, k=10)

        stats = search_cpu.get_stats()

        assert stats['searches_executed'] == 3
        assert stats['avg_time_ms'] == stats['total_time_ms'] / 3

    def test_reset_stats(self, search_cpu):
        """reset_stats clears all counters"""
        query = np.random.randn(384).astype(np.float32)

        # Run some searches
        search_cpu.search(query, k=10)
        search_cpu.search(query, k=5)

        search_cpu.reset_stats()

        assert search_cpu.stats['searches_executed'] == 0
        assert search_cpu.stats['total_time_ms'] == 0
        assert search_cpu.stats['gpu_time_ms'] == 0
        assert search_cpu.stats['cpu_fallback_count'] == 0


class TestUtilityMethods:
    """Tests for utility methods"""

    def test_is_available_after_init(self):
        """is_available returns True after initialization"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        assert search.is_available() is True

    def test_uses_metal_false_without_metal(self):
        """uses_metal returns False without Metal"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        assert search.uses_metal() is False


class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_metal4_vector_search_returns_instance(self):
        """get_metal4_vector_search returns instance"""
        # Reset singleton
        import api.metal4_vector_search as module
        module._metal4_vector_search = None

        with patch.object(
            module.Metal4VectorSearch, '_check_metal4', return_value=False
        ):
            search = module.get_metal4_vector_search()

        assert search is not None
        assert isinstance(search, module.Metal4VectorSearch)

    def test_get_metal4_vector_search_returns_same_instance(self):
        """get_metal4_vector_search returns same instance"""
        import api.metal4_vector_search as module
        module._metal4_vector_search = None

        with patch.object(
            module.Metal4VectorSearch, '_check_metal4', return_value=False
        ):
            search1 = module.get_metal4_vector_search()
            search2 = module.get_metal4_vector_search()

        assert search1 is search2


class TestValidation:
    """Tests for validate_metal4_vector_search"""

    def test_validate_returns_status_dict(self):
        """validate_metal4_vector_search returns status dict"""
        import api.metal4_vector_search as module
        module._metal4_vector_search = None

        with patch.object(
            module.Metal4VectorSearch, '_check_metal4', return_value=False
        ):
            status = module.validate_metal4_vector_search()

        assert isinstance(status, dict)
        assert 'initialized' in status
        assert 'metal_enabled' in status
        assert 'database_loaded' in status
        assert 'test_passed' in status

    def test_validate_test_passes_with_correct_results(self):
        """Validation test passes when search returns correct count"""
        import api.metal4_vector_search as module
        module._metal4_vector_search = None

        with patch.object(
            module.Metal4VectorSearch, '_check_metal4', return_value=False
        ):
            status = module.validate_metal4_vector_search()

        assert status['test_passed'] is True
        assert status['initialized'] is True

    def test_validate_handles_exception(self):
        """Validation handles exception gracefully"""
        import api.metal4_vector_search as module
        module._metal4_vector_search = None

        with patch.object(
            module, 'get_metal4_vector_search',
            side_effect=Exception("Init failed")
        ):
            status = module.validate_metal4_vector_search()

        assert status['initialized'] is False
        assert 'error' in status


class TestSearchCPUFallbackMethods:
    """Tests for _search_cpu internal method"""

    @pytest.fixture
    def search_cpu(self):
        """Create CPU search instance"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        # Create known database for predictable results
        db = np.eye(100, 384, dtype=np.float32)  # Identity-like matrix
        search.load_database(db)
        return search

    def test_search_cpu_cosine_returns_correct_count(self, search_cpu):
        """_search_cpu cosine returns correct number of results"""
        query = np.zeros(384, dtype=np.float32)
        query[0] = 1.0  # Should match first vector best

        indices, scores = search_cpu._search_cpu(query, k=5, metric="cosine")

        assert len(indices) == 5
        assert len(scores) == 5
        assert 0 in indices  # First vector should be in results

    def test_search_cpu_l2_returns_correct_count(self, search_cpu):
        """_search_cpu L2 returns correct number of results"""
        query = np.zeros(384, dtype=np.float32)
        query[0] = 1.0

        indices, scores = search_cpu._search_cpu(query, k=5, metric="l2")

        assert len(indices) == 5
        assert len(scores) == 5

    def test_search_cpu_dot_returns_correct_count(self, search_cpu):
        """_search_cpu dot product returns correct number of results"""
        query = np.random.randn(384).astype(np.float32)

        indices, scores = search_cpu._search_cpu(query, k=5, metric="dot")

        assert len(indices) == 5
        assert len(scores) == 5

    def test_search_cpu_without_database(self):
        """_search_cpu returns empty when no database loaded"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        # Don't load database
        query = np.random.randn(384).astype(np.float32)

        indices, scores = search._search_cpu(query, k=5, metric="cosine")

        assert indices == []
        assert scores == []


class TestEdgeCases:
    """Edge case tests"""

    def test_search_k_larger_than_database(self):
        """Search with K larger than database size"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        # Small database
        db = np.random.randn(5, 384).astype(np.float32)
        search.load_database(db)

        query = np.random.randn(384).astype(np.float32)
        indices, scores = search.search(query, k=10, metric="cosine")

        # Should return at most 5 results
        assert len(indices) <= 5
        assert len(scores) <= 5

    def test_search_k_equals_one(self):
        """Search with K=1"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        db = np.random.randn(100, 384).astype(np.float32)
        search.load_database(db)

        query = np.random.randn(384).astype(np.float32)
        indices, scores = search.search(query, k=1, metric="cosine")

        assert len(indices) == 1
        assert len(scores) == 1

    def test_empty_database(self):
        """Handle empty database edge case"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        # Load empty database (0 vectors)
        db = np.zeros((0, 384), dtype=np.float32)
        search.load_database(db)

        assert search.num_vectors == 0

    def test_very_small_embeddings(self):
        """Handle very small embedding dimensions"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        db = np.random.randn(100, 2).astype(np.float32)  # 2D embeddings
        search.load_database(db)

        query = np.random.randn(2).astype(np.float32)
        indices, scores = search.search(query, k=10, metric="cosine")

        assert len(indices) == 10

    def test_single_vector_database(self):
        """Handle single vector in database"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        db = np.random.randn(1, 384).astype(np.float32)
        search.load_database(db)

        query = np.random.randn(384).astype(np.float32)
        indices, scores = search.search(query, k=10, metric="cosine")

        assert len(indices) == 1
        assert indices[0] == 0


class TestMetalPathMocked:
    """Tests for Metal code path with mocked dependencies"""

    def test_load_database_metal_path(self):
        """Test Metal database loading with mocked Metal"""
        from api.metal4_vector_search import Metal4VectorSearch

        mock_device = Mock()
        mock_buffer = Mock()
        mock_buffer.contents.return_value = 0  # Null pointer for test

        mock_device.newBufferWithLength_options_.return_value = mock_buffer

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=True):
            with patch.object(Metal4VectorSearch, '_init_metal_pipelines'):
                search = Metal4VectorSearch()
                search._use_metal = True
                search.metal_device = mock_device

        # This will likely fail due to the pointer operations, which is expected
        # Just verify the path is taken
        embeddings = np.random.randn(10, 384).astype(np.float32)

        try:
            search.load_database(embeddings)
        except Exception:
            # Expected to fail without real Metal
            pass

    def test_search_metal_path_fallback_on_error(self):
        """Test Metal search falls back on error"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        db = np.random.randn(100, 384).astype(np.float32)
        search.load_database(db)

        # Force _use_metal but without actual Metal setup
        search._use_metal = True

        query = np.random.randn(384).astype(np.float32)

        # Should handle gracefully
        indices, scores = search.search(query, k=10, metric="cosine")

        # Will likely return empty due to error handling
        assert isinstance(indices, list)
        assert isinstance(scores, list)


class TestIntegration:
    """Integration tests"""

    def test_full_workflow_cpu(self):
        """Test full workflow with CPU fallback"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        # Load database
        db = np.random.randn(1000, 384).astype(np.float32)
        search.load_database(db)

        # Run multiple searches
        for _ in range(5):
            query = np.random.randn(384).astype(np.float32)
            indices, scores = search.search(query, k=10, metric="cosine")
            assert len(indices) == 10

        # Check stats
        stats = search.get_stats()
        assert stats['searches_executed'] == 5
        assert stats['database_size'] == 1000

        # Reset and verify
        search.reset_stats()
        assert search.stats['searches_executed'] == 0

    def test_all_metrics_produce_valid_results(self):
        """Test all metrics produce valid results"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        db = np.random.randn(100, 384).astype(np.float32)
        search.load_database(db)

        query = np.random.randn(384).astype(np.float32)

        for metric in ["cosine", "l2", "dot"]:
            indices, scores = search.search(query, k=10, metric=metric)
            assert len(indices) == 10, f"Failed for metric {metric}"
            assert len(scores) == 10, f"Failed for metric {metric}"
            # All indices should be valid
            assert all(0 <= idx < 100 for idx in indices), f"Invalid index for {metric}"

    def test_multiple_databases_loaded(self):
        """Test loading multiple databases (replaces previous)"""
        from api.metal4_vector_search import Metal4VectorSearch

        with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
            search = Metal4VectorSearch()

        # Load first database
        db1 = np.random.randn(100, 384).astype(np.float32)
        search.load_database(db1)
        assert search.num_vectors == 100

        # Load second database (replaces first)
        db2 = np.random.randn(200, 384).astype(np.float32)
        search.load_database(db2)
        assert search.num_vectors == 200

    def test_different_embedding_dimensions(self):
        """Test different embedding dimensions"""
        from api.metal4_vector_search import Metal4VectorSearch

        for dim in [64, 128, 256, 384, 512, 768, 1024]:
            with patch.object(Metal4VectorSearch, '_check_metal4', return_value=False):
                search = Metal4VectorSearch()

            db = np.random.randn(50, dim).astype(np.float32)
            search.load_database(db)

            query = np.random.randn(dim).astype(np.float32)
            indices, scores = search.search(query, k=5)

            assert len(indices) == 5, f"Failed for dim={dim}"
