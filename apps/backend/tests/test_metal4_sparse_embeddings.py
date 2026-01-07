"""
Comprehensive tests for api/metal4_sparse_embeddings.py

Tests Metal 4 sparse embedding storage:
- Initialization and configuration
- Memory-mapped backing store
- Embedding CRUD operations (single and batch)
- LRU cache management (page in, evict)
- GPU cache statistics
- Metadata persistence
- Singleton pattern
- Validation function

Total: ~50 tests covering all functionality.
"""

import pytest
import numpy as np
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


# ===== Test Initialization =====

class TestMetal4SparseEmbeddingsInit:
    """Tests for Metal4SparseEmbeddings initialization"""

    def test_initialization_with_defaults(self, tmp_path):
        """Initialize with default parameters"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test_embeddings.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=384,
                max_vectors=1000,
                backing_file=backing_file,
                gpu_cache_size_mb=16
            )

        assert store.embed_dim == 384
        assert store.max_vectors == 1000
        assert store.backing_file == backing_file
        assert store._initialized is True

        store.close()

    def test_initialization_creates_backing_file(self, tmp_path):
        """Initialization creates backing file if not exists"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "new_embeddings.mmap")
        assert not Path(backing_file).exists()

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        assert Path(backing_file).exists()
        store.close()

    def test_initialization_calculates_max_gpu_vectors(self, tmp_path):
        """Max GPU vectors calculated from cache size"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test_embeddings.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=384,
                max_vectors=1000,
                backing_file=backing_file,
                gpu_cache_size_mb=16
            )

        # 16 MB / (384 * 4 bytes) = ~10922 vectors
        expected = (16 * 1024 * 1024) // (384 * 4)
        assert store.max_gpu_vectors == expected

        store.close()

    def test_initialization_loads_existing_metadata(self, tmp_path):
        """Load vector count from existing metadata"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test_embeddings.mmap")
        meta_file = tmp_path / "test_embeddings.meta"

        # Create metadata
        meta_file.write_text(json.dumps({'total_vectors': 500}))

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=384,
                max_vectors=1000,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        assert store.stats['total_vectors'] == 500

        store.close()

    def test_default_backing_file_path(self):
        """Get default backing file path"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        # Create instance to test method
        store = object.__new__(Metal4SparseEmbeddings)
        store.embed_dim = 384

        path = store._get_default_backing_file()

        assert ".elohimos" in path
        assert "embedding_cache" in path
        assert "384d" in path


# ===== Test Backing Store =====

class TestBackingStore:
    """Tests for memory-mapped backing store"""

    def test_backing_store_creates_sparse_file(self, tmp_path):
        """Backing store creates sparse file of correct size"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "sparse.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=1000,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        # File should exist with correct size
        expected_size = 1000 * 128 * 4  # max_vectors * embed_dim * 4 bytes
        actual_size = Path(backing_file).stat().st_size
        assert actual_size == expected_size

        store.close()

    def test_backing_store_opens_existing_file(self, tmp_path):
        """Backing store opens existing file"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "existing.mmap")

        # Create first instance
        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store1 = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )
            store1.close()

        # Create second instance - should open existing
        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store2 = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        assert store2._initialized is True
        store2.close()


# ===== Test Sparse Resources Check =====

class TestSparseResourcesCheck:
    """Tests for Metal 4 sparse resources availability check"""

    def test_check_returns_false_when_metal_unavailable(self, tmp_path):
        """Returns False when Metal 4 not available"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        mock_engine = Mock()
        mock_engine.is_available.return_value = False

        # Import is local: from metal4_engine import get_metal4_engine
        with patch.dict('sys.modules', {'metal4_engine': Mock(get_metal4_engine=Mock(return_value=mock_engine))}):
            store = object.__new__(Metal4SparseEmbeddings)
            result = store._check_sparse_resources()

        assert result is False

    def test_check_returns_false_when_sparse_unsupported(self, tmp_path):
        """Returns False when sparse resources not supported"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.capabilities.supports_sparse_resources = False
        mock_engine.capabilities.version.value = "metal3"

        with patch.dict('sys.modules', {'metal4_engine': Mock(get_metal4_engine=Mock(return_value=mock_engine))}):
            store = object.__new__(Metal4SparseEmbeddings)
            result = store._check_sparse_resources()

        assert result is False

    def test_check_returns_true_when_available(self, tmp_path):
        """Returns True when sparse resources available"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.capabilities.supports_sparse_resources = True

        with patch.dict('sys.modules', {'metal4_engine': Mock(get_metal4_engine=Mock(return_value=mock_engine))}):
            store = object.__new__(Metal4SparseEmbeddings)
            result = store._check_sparse_resources()

        assert result is True

    def test_check_handles_import_error(self, tmp_path):
        """Handles ImportError gracefully"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings
        import sys

        # Remove metal4_engine from modules to force import to fail
        original_modules = sys.modules.copy()

        # Clear any cached import
        for key in list(sys.modules.keys()):
            if 'metal4' in key:
                del sys.modules[key]

        # Make import raise error
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'metal4_engine' or name.startswith('metal4_engine'):
                raise ImportError("No metal4_engine")
            return original_import(name, *args, **kwargs)

        store = object.__new__(Metal4SparseEmbeddings)

        with patch.object(builtins, '__import__', mock_import):
            result = store._check_sparse_resources()

        assert result is False


# ===== Test Add Embedding =====

class TestAddEmbedding:
    """Tests for add_embedding method"""

    def test_add_single_embedding(self, tmp_path):
        """Add single embedding"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        embedding = np.random.randn(128).astype(np.float32)
        store.add_embedding(0, embedding)

        assert store.stats['total_vectors'] == 1

        # Retrieve and verify
        retrieved = store.get_embedding(0)
        np.testing.assert_array_almost_equal(embedding, retrieved)

        store.close()

    def test_add_embedding_updates_count(self, tmp_path):
        """Add embedding updates total_vectors count"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        # Add at various indices
        embedding = np.random.randn(128).astype(np.float32)
        store.add_embedding(5, embedding)

        # Count should be highest index + 1
        assert store.stats['total_vectors'] == 6

        store.close()

    def test_add_embedding_invalid_vector_id(self, tmp_path):
        """Raise error for invalid vector ID"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        embedding = np.random.randn(128).astype(np.float32)

        with pytest.raises(ValueError, match="out of range"):
            store.add_embedding(100, embedding)  # max is 99

        with pytest.raises(ValueError, match="out of range"):
            store.add_embedding(-1, embedding)

        store.close()

    def test_add_embedding_wrong_dimension(self, tmp_path):
        """Raise error for wrong embedding dimension"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        wrong_embedding = np.random.randn(256).astype(np.float32)

        with pytest.raises(ValueError, match="dimension"):
            store.add_embedding(0, wrong_embedding)

        store.close()


# ===== Test Add Embeddings Batch =====

class TestAddEmbeddingsBatch:
    """Tests for add_embeddings_batch method"""

    def test_add_batch(self, tmp_path):
        """Add batch of embeddings"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        embeddings = np.random.randn(10, 128).astype(np.float32)
        vector_ids = list(range(10))

        store.add_embeddings_batch(vector_ids, embeddings)

        assert store.stats['total_vectors'] == 10

        # Verify retrieval
        retrieved = store.get_embeddings_batch(vector_ids)
        np.testing.assert_array_almost_equal(embeddings, retrieved)

        store.close()

    def test_add_batch_mismatched_lengths(self, tmp_path):
        """Raise error for mismatched ID and embedding counts"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        embeddings = np.random.randn(10, 128).astype(np.float32)
        vector_ids = list(range(5))  # Only 5 IDs

        with pytest.raises(ValueError, match="must match"):
            store.add_embeddings_batch(vector_ids, embeddings)

        store.close()


# ===== Test Get Embedding =====

class TestGetEmbedding:
    """Tests for get_embedding method"""

    def test_get_existing_embedding(self, tmp_path):
        """Get existing embedding"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        embedding = np.random.randn(128).astype(np.float32)
        store.add_embedding(5, embedding)

        retrieved = store.get_embedding(5)
        np.testing.assert_array_almost_equal(embedding, retrieved)

        store.close()

    def test_get_nonexistent_returns_none(self, tmp_path):
        """Get non-existent embedding returns None"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        result = store.get_embedding(99)  # No embeddings added
        assert result is None

        store.close()

    def test_get_embedding_cache_hit(self, tmp_path):
        """Get embedding updates cache hit stats"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        embedding = np.random.randn(128).astype(np.float32)
        store.add_embedding(0, embedding)

        # First access - cache miss
        store.gpu_cache[0] = 0  # Simulate cache hit
        store.get_embedding(0)

        assert store.stats['gpu_cache_hits'] == 1

        store.close()


# ===== Test Get Embeddings Batch =====

class TestGetEmbeddingsBatch:
    """Tests for get_embeddings_batch method"""

    def test_get_batch(self, tmp_path):
        """Get batch of embeddings"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        embeddings = np.random.randn(5, 128).astype(np.float32)
        store.add_embeddings_batch(list(range(5)), embeddings)

        retrieved = store.get_embeddings_batch([0, 2, 4])

        assert retrieved.shape == (3, 128)
        np.testing.assert_array_almost_equal(embeddings[0], retrieved[0])
        np.testing.assert_array_almost_equal(embeddings[2], retrieved[1])
        np.testing.assert_array_almost_equal(embeddings[4], retrieved[2])

        store.close()

    def test_get_batch_missing_returns_zeros(self, tmp_path):
        """Missing vectors return zeros"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        embedding = np.random.randn(128).astype(np.float32)
        store.add_embedding(0, embedding)

        # Request including non-existent
        retrieved = store.get_embeddings_batch([0, 99])

        assert retrieved.shape == (2, 128)
        np.testing.assert_array_almost_equal(embedding, retrieved[0])
        np.testing.assert_array_equal(np.zeros(128), retrieved[1])

        store.close()


# ===== Test Get All Embeddings =====

class TestGetAllEmbeddings:
    """Tests for get_all_embeddings method"""

    def test_get_all_embeddings(self, tmp_path):
        """Get all stored embeddings"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        embeddings = np.random.randn(10, 128).astype(np.float32)
        store.add_embeddings_batch(list(range(10)), embeddings)

        all_retrieved = store.get_all_embeddings()

        assert all_retrieved.shape == (10, 128)
        np.testing.assert_array_almost_equal(embeddings, all_retrieved)

        store.close()

    def test_get_all_empty_store(self, tmp_path):
        """Get all from empty store"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        all_retrieved = store.get_all_embeddings()

        assert all_retrieved.shape == (0, 128)

        store.close()


# ===== Test LRU Cache =====

class TestLRUCache:
    """Tests for LRU cache management"""

    def test_page_in_adds_to_cache(self, tmp_path):
        """_page_in adds vector to GPU cache"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        store._page_in(5)

        assert 5 in store.gpu_cache
        assert 5 in store.lru_queue
        assert store.stats['page_ins'] == 1

        store.close()

    def test_page_in_evicts_when_full(self, tmp_path):
        """_page_in evicts LRU when cache full"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        # Set small cache
        store.max_gpu_vectors = 3

        # Fill cache
        store._page_in(0)
        store._page_in(1)
        store._page_in(2)

        # One more should evict oldest (0)
        store._page_in(3)

        assert 0 not in store.gpu_cache
        assert 3 in store.gpu_cache
        assert store.stats['page_outs'] == 1

        store.close()

    def test_update_lru_moves_to_end(self, tmp_path):
        """_update_lru moves vector to end of queue"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        store.lru_queue = [1, 2, 3]
        store._update_lru(1)

        assert store.lru_queue == [2, 3, 1]

        store.close()

    def test_evict_lru_removes_oldest(self, tmp_path):
        """_evict_lru removes oldest from queue and cache"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        store.lru_queue = [1, 2, 3]
        store.gpu_cache = {1: 0, 2: 512, 3: 1024}

        store._evict_lru()

        assert 1 not in store.gpu_cache
        assert 1 not in store.lru_queue
        assert store.stats['page_outs'] == 1

        store.close()


# ===== Test Metadata =====

class TestMetadata:
    """Tests for metadata persistence"""

    def test_save_metadata(self, tmp_path):
        """Save metadata to file"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        embedding = np.random.randn(128).astype(np.float32)
        store.add_embedding(0, embedding)

        store.save_metadata()

        meta_path = tmp_path / "test.meta"
        assert meta_path.exists()

        metadata = json.loads(meta_path.read_text())
        assert metadata['total_vectors'] == 1
        assert metadata['embed_dim'] == 128

        store.close()

    def test_get_capacity_info(self, tmp_path):
        """Get capacity info string"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=1000,
                backing_file=backing_file,
                gpu_cache_size_mb=16
            )

        info = store._get_capacity_info()

        assert "GB" in info
        assert "/" in info

        store.close()


# ===== Test Statistics =====

class TestStatistics:
    """Tests for statistics tracking"""

    def test_get_stats(self, tmp_path):
        """Get statistics dict"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        stats = store.get_stats()

        assert 'total_vectors' in stats
        assert 'gpu_cache_hits' in stats
        assert 'gpu_cache_misses' in stats
        assert 'cache_hit_rate' in stats
        assert 'gpu_cache_size' in stats
        assert 'sparse_resources_enabled' in stats
        assert 'capacity_info' in stats

        store.close()

    def test_cache_hit_rate_calculation(self, tmp_path):
        """Cache hit rate calculated correctly"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        store.stats['gpu_cache_hits'] = 75
        store.stats['gpu_cache_misses'] = 25

        stats = store.get_stats()

        assert stats['cache_hit_rate'] == 0.75

        store.close()


# ===== Test Close =====

class TestClose:
    """Tests for close method"""

    def test_close_saves_and_flushes(self, tmp_path):
        """Close saves metadata and flushes mmap"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "test.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file,
                gpu_cache_size_mb=1
            )

        embedding = np.random.randn(128).astype(np.float32)
        store.add_embedding(0, embedding)

        store.close()

        # Verify metadata saved
        meta_path = tmp_path / "test.meta"
        assert meta_path.exists()


# ===== Test Singleton =====

class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_sparse_embeddings_returns_singleton(self, tmp_path):
        """get_sparse_embeddings returns same instance"""
        import api.metal4_sparse_embeddings as module

        # Reset singleton
        module._sparse_embeddings = None

        backing_file = str(tmp_path / "singleton.mmap")

        with patch.object(module.Metal4SparseEmbeddings, '_check_sparse_resources', return_value=False):
            store1 = module.get_sparse_embeddings(
                embed_dim=128,
                max_vectors=100,
                backing_file=backing_file
            )
            store2 = module.get_sparse_embeddings()

        assert store1 is store2

        store1.close()
        module._sparse_embeddings = None


# ===== Test Validation =====

class TestValidation:
    """Tests for validate_sparse_embeddings function"""

    def test_validate_sparse_embeddings_success(self):
        """Validation succeeds with working storage"""
        from api.metal4_sparse_embeddings import validate_sparse_embeddings

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            result = validate_sparse_embeddings()

        assert result['initialized'] is True
        assert result['test_passed'] is True
        assert 'stats' in result

    def test_validate_sparse_embeddings_handles_error(self):
        """Validation handles errors gracefully"""
        from api.metal4_sparse_embeddings import validate_sparse_embeddings

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings.__init__', side_effect=Exception("Init failed")):
            result = validate_sparse_embeddings()

        assert result['initialized'] is False
        assert 'error' in result


# ===== Integration Tests =====

class TestIntegration:
    """Integration tests"""

    def test_full_workflow(self, tmp_path):
        """Full workflow: create, add, retrieve, close"""
        from api.metal4_sparse_embeddings import Metal4SparseEmbeddings

        backing_file = str(tmp_path / "workflow.mmap")

        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store = Metal4SparseEmbeddings(
                embed_dim=256,
                max_vectors=1000,
                backing_file=backing_file,
                gpu_cache_size_mb=8
            )

        # Add batch
        embeddings = np.random.randn(100, 256).astype(np.float32)
        store.add_embeddings_batch(list(range(100)), embeddings)

        # Get individual
        retrieved = store.get_embedding(50)
        np.testing.assert_array_almost_equal(embeddings[50], retrieved)

        # Get batch
        batch = store.get_embeddings_batch([10, 20, 30])
        np.testing.assert_array_almost_equal(embeddings[10], batch[0])

        # Get all
        all_embeddings = store.get_all_embeddings()
        assert all_embeddings.shape == (100, 256)

        # Get stats
        stats = store.get_stats()
        assert stats['total_vectors'] == 100

        # Close
        store.close()

        # Reopen and verify persistence
        with patch('api.metal4_sparse_embeddings.Metal4SparseEmbeddings._check_sparse_resources', return_value=False):
            store2 = Metal4SparseEmbeddings(
                embed_dim=256,
                max_vectors=1000,
                backing_file=backing_file,
                gpu_cache_size_mb=8
            )

        assert store2.stats['total_vectors'] == 100
        retrieved2 = store2.get_embedding(50)
        np.testing.assert_array_almost_equal(embeddings[50], retrieved2)

        store2.close()
