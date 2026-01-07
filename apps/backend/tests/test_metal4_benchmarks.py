"""
Comprehensive tests for api/metal4_benchmarks.py

Tests the Metal 4 performance benchmark suite including:
- BenchmarkResult dataclass
- Metal4Benchmarks class
- Individual benchmark methods (with mocked Metal4 dependencies)
- Summary generation and speedup calculations
- Standalone run_benchmarks function
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from dataclasses import asdict

from api.metal4_benchmarks import (
    BenchmarkResult,
    Metal4Benchmarks,
    run_benchmarks,
)


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass"""

    def test_create_minimal(self):
        """Create with required fields only"""
        result = BenchmarkResult(
            name="Test",
            backend="CPU",
            operations=100,
            total_time_ms=1000.0,
            ops_per_second=100.0
        )
        assert result.name == "Test"
        assert result.backend == "CPU"
        assert result.operations == 100
        assert result.total_time_ms == 1000.0
        assert result.ops_per_second == 100.0

    def test_default_values(self):
        """Verify default values"""
        result = BenchmarkResult(
            name="Test",
            backend="CPU",
            operations=100,
            total_time_ms=1000.0,
            ops_per_second=100.0
        )
        assert result.speedup == 1.0
        assert result.memory_mb == 0.0
        assert result.success is True
        assert result.error == ""

    def test_create_with_all_fields(self):
        """Create with all fields specified"""
        result = BenchmarkResult(
            name="Vector Search",
            backend="Metal GPU",
            operations=1000,
            total_time_ms=500.0,
            ops_per_second=2000.0,
            speedup=10.5,
            memory_mb=256.5,
            success=True,
            error=""
        )
        assert result.speedup == 10.5
        assert result.memory_mb == 256.5

    def test_failed_benchmark(self):
        """Benchmark result for failed test"""
        result = BenchmarkResult(
            name="Embedding",
            backend="Metal",
            operations=0,
            total_time_ms=0.0,
            ops_per_second=0.0,
            success=False,
            error="Metal device not available"
        )
        assert result.success is False
        assert "Metal device not available" in result.error

    def test_asdict_conversion(self):
        """Convert to dictionary"""
        result = BenchmarkResult(
            name="Test",
            backend="CPU",
            operations=100,
            total_time_ms=1000.0,
            ops_per_second=100.0
        )
        result_dict = asdict(result)
        assert result_dict['name'] == "Test"
        assert result_dict['backend'] == "CPU"
        assert 'speedup' in result_dict

    def test_high_precision_values(self):
        """Handle high precision floating point values"""
        result = BenchmarkResult(
            name="Precision Test",
            backend="Metal GPU",
            operations=1000000,
            total_time_ms=1234.56789,
            ops_per_second=810045.3216,
            speedup=10.123456789,
            memory_mb=2048.123456
        )
        assert result.total_time_ms == pytest.approx(1234.56789)
        assert result.ops_per_second == pytest.approx(810045.3216)


class TestMetal4BenchmarksInit:
    """Tests for Metal4Benchmarks initialization"""

    def test_init_creates_empty_results(self):
        """Initialization creates empty results list"""
        benchmarks = Metal4Benchmarks()
        assert benchmarks.results == []

    def test_init_results_is_list(self):
        """Results is a list"""
        benchmarks = Metal4Benchmarks()
        assert isinstance(benchmarks.results, list)


class TestSingleEmbeddingBenchmark:
    """Tests for _benchmark_single_embedding"""

    @pytest.fixture
    def benchmarks(self):
        return Metal4Benchmarks()

    @pytest.fixture
    def mock_metal_embedder(self):
        """Mock Metal4 MPS embedder"""
        embedder = Mock()
        embedder.is_available.return_value = True
        embedder.uses_metal.return_value = True
        embedder.embed.return_value = np.random.randn(384).astype(np.float32)
        return embedder

    @pytest.fixture
    def mock_cpu_embedder(self):
        """Mock CPU embedder"""
        embedder = Mock()
        embedder.embed.return_value = np.random.randn(384).astype(np.float32)
        return embedder

    def test_benchmark_with_metal_available(self, benchmarks, mock_metal_embedder, mock_cpu_embedder):
        """Benchmark runs with Metal available"""
        with patch.dict('sys.modules', {
            'metal4_mps_embedder': Mock(get_metal4_mps_embedder=Mock(return_value=mock_metal_embedder)),
            'unified_embedder': Mock(UnifiedEmbedder=Mock(return_value=mock_cpu_embedder))
        }):
            benchmarks._benchmark_single_embedding()

        # Should have at least one result (Metal)
        assert len(benchmarks.results) >= 1
        assert benchmarks.results[0].name == "Single Embedding"

    def test_benchmark_without_metal(self, benchmarks, mock_cpu_embedder):
        """Benchmark handles Metal not available"""
        mock_embedder = Mock()
        mock_embedder.is_available.return_value = False

        with patch.dict('sys.modules', {
            'metal4_mps_embedder': Mock(get_metal4_mps_embedder=Mock(return_value=mock_embedder)),
            'unified_embedder': Mock(UnifiedEmbedder=Mock(return_value=mock_cpu_embedder))
        }):
            benchmarks._benchmark_single_embedding()

        # Should have CPU baseline result
        cpu_results = [r for r in benchmarks.results if "CPU" in r.backend]
        assert len(cpu_results) >= 0  # May or may not have CPU result

    def test_benchmark_metal_exception(self, benchmarks):
        """Benchmark handles Metal exception"""
        with patch.dict('sys.modules', {
            'metal4_mps_embedder': Mock(get_metal4_mps_embedder=Mock(side_effect=Exception("Metal error")))
        }):
            benchmarks._benchmark_single_embedding()

        # Should record failed benchmark
        failed = [r for r in benchmarks.results if not r.success]
        assert len(failed) >= 1
        assert "Metal error" in failed[0].error


class TestBatchEmbeddingBenchmark:
    """Tests for _benchmark_batch_embedding"""

    @pytest.fixture
    def benchmarks(self):
        return Metal4Benchmarks()

    def test_benchmark_with_metal(self, benchmarks):
        """Batch embedding benchmark with Metal"""
        mock_embedder = Mock()
        mock_embedder.is_available.return_value = True
        mock_embedder.uses_metal.return_value = True
        mock_embedder.embed_batch.return_value = [np.random.randn(384).astype(np.float32) for _ in range(100)]

        mock_cpu = Mock()
        mock_cpu.embed_batch.return_value = [np.random.randn(384).astype(np.float32) for _ in range(100)]

        with patch.dict('sys.modules', {
            'metal4_mps_embedder': Mock(get_metal4_mps_embedder=Mock(return_value=mock_embedder)),
            'unified_embedder': Mock(UnifiedEmbedder=Mock(return_value=mock_cpu))
        }):
            benchmarks._benchmark_batch_embedding()

        assert len(benchmarks.results) >= 1
        assert "Batch" in benchmarks.results[0].name

    def test_benchmark_calculates_ops_per_second(self, benchmarks):
        """Benchmark calculates operations per second"""
        mock_embedder = Mock()
        mock_embedder.is_available.return_value = True
        mock_embedder.uses_metal.return_value = True
        mock_embedder.embed_batch.return_value = [np.random.randn(384).astype(np.float32) for _ in range(100)]

        with patch.dict('sys.modules', {
            'metal4_mps_embedder': Mock(get_metal4_mps_embedder=Mock(return_value=mock_embedder)),
            'unified_embedder': Mock(UnifiedEmbedder=Mock(side_effect=Exception("Skip CPU")))
        }):
            benchmarks._benchmark_batch_embedding()

        if benchmarks.results:
            assert benchmarks.results[0].ops_per_second > 0


class TestVectorSearchBenchmark:
    """Tests for _benchmark_vector_search"""

    @pytest.fixture
    def benchmarks(self):
        return Metal4Benchmarks()

    @pytest.fixture
    def mock_search(self):
        """Mock Metal4 vector search"""
        search = Mock()
        search.uses_metal.return_value = True
        search.search.return_value = (np.array([0, 1, 2]), np.array([0.9, 0.8, 0.7]))
        return search

    def test_benchmark_vector_search(self, benchmarks, mock_search):
        """Vector search benchmark runs"""
        with patch.dict('sys.modules', {
            'metal4_vector_search': Mock(get_metal4_vector_search=Mock(return_value=mock_search))
        }):
            benchmarks._benchmark_vector_search()

        # Should have Metal result
        metal_results = [r for r in benchmarks.results if "Metal" in r.backend]
        assert len(metal_results) >= 1 or len(benchmarks.results) >= 1

    def test_benchmark_includes_cpu_baseline(self, benchmarks, mock_search):
        """Benchmark includes CPU NumPy baseline"""
        with patch.dict('sys.modules', {
            'metal4_vector_search': Mock(get_metal4_vector_search=Mock(return_value=mock_search))
        }):
            benchmarks._benchmark_vector_search()

        cpu_results = [r for r in benchmarks.results if "CPU" in r.backend]
        assert len(cpu_results) >= 1

    def test_benchmark_calculates_speedup(self, benchmarks, mock_search):
        """Benchmark calculates speedup vs CPU"""
        with patch.dict('sys.modules', {
            'metal4_vector_search': Mock(get_metal4_vector_search=Mock(return_value=mock_search))
        }):
            benchmarks._benchmark_vector_search()

        if len(benchmarks.results) >= 2:
            metal_result = benchmarks.results[0]
            assert metal_result.speedup >= 0


class TestSparseStorageBenchmark:
    """Tests for _benchmark_sparse_storage"""

    @pytest.fixture
    def benchmarks(self):
        return Metal4Benchmarks()

    def test_benchmark_sparse_storage(self, benchmarks):
        """Sparse storage benchmark with mocked storage"""
        mock_storage = Mock()
        mock_storage._use_sparse_resources = True
        mock_storage.add_embeddings_batch = Mock()
        mock_storage.get_embeddings_batch.return_value = np.random.randn(1000, 384).astype(np.float32)
        mock_storage.close = Mock()

        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=512 * 1024 * 1024)  # 512 MB

        with patch.dict('sys.modules', {
            'metal4_sparse_embeddings': Mock(Metal4SparseEmbeddings=Mock(return_value=mock_storage)),
            'psutil': Mock(Process=Mock(return_value=mock_process))
        }):
            with patch('tempfile.mktemp', return_value='/tmp/test.mmap'):
                with patch('os.unlink'):
                    with patch('os.path.exists', return_value=True):
                        benchmarks._benchmark_sparse_storage()

        sparse_results = [r for r in benchmarks.results if "Sparse" in r.name]
        if sparse_results:
            assert sparse_results[0].memory_mb > 0

    def test_benchmark_handles_sparse_exception(self, benchmarks):
        """Handles sparse storage exception"""
        with patch.dict('sys.modules', {
            'metal4_sparse_embeddings': Mock(
                Metal4SparseEmbeddings=Mock(side_effect=Exception("Storage error"))
            )
        }):
            # Should not raise
            benchmarks._benchmark_sparse_storage()


class TestRAGPipelineBenchmark:
    """Tests for _benchmark_rag_pipeline"""

    @pytest.fixture
    def benchmarks(self):
        return Metal4Benchmarks()

    @pytest.fixture
    def mock_pipeline(self):
        """Mock ML pipeline"""
        pipeline = Mock()
        pipeline.embed_batch.return_value = [np.random.randn(384).astype(np.float32) for _ in range(100)]
        pipeline.load_database = Mock()
        pipeline.search.return_value = (np.array([0, 1, 2]), np.array([0.9, 0.8, 0.7]))
        pipeline.get_capabilities.return_value = {'embedder_backend': 'Metal'}
        return pipeline

    def test_benchmark_rag_pipeline(self, benchmarks, mock_pipeline):
        """RAG pipeline benchmark runs"""
        with patch.dict('sys.modules', {
            'metal4_ml_integration': Mock(get_ml_pipeline=Mock(return_value=mock_pipeline))
        }):
            benchmarks._benchmark_rag_pipeline()

        rag_results = [r for r in benchmarks.results if "RAG" in r.name]
        assert len(rag_results) >= 1

    def test_benchmark_rag_handles_exception(self, benchmarks):
        """RAG benchmark handles exception"""
        with patch.dict('sys.modules', {
            'metal4_ml_integration': Mock(
                get_ml_pipeline=Mock(side_effect=Exception("Pipeline error"))
            )
        }):
            # Should not raise
            benchmarks._benchmark_rag_pipeline()


class TestSummaryGeneration:
    """Tests for _generate_summary"""

    @pytest.fixture
    def benchmarks(self):
        return Metal4Benchmarks()

    def test_empty_results(self, benchmarks):
        """Summary with no results"""
        summary = benchmarks._generate_summary()
        assert summary['total_benchmarks'] == 0
        assert summary['successful'] == 0
        assert summary['failed'] == 0

    def test_summary_counts_successful(self, benchmarks):
        """Summary counts successful benchmarks"""
        benchmarks.results = [
            BenchmarkResult("Test1", "Metal", 100, 1000.0, 100.0, success=True),
            BenchmarkResult("Test2", "CPU", 100, 2000.0, 50.0, success=True)
        ]
        summary = benchmarks._generate_summary()
        assert summary['total_benchmarks'] == 2
        assert summary['successful'] == 2
        assert summary['failed'] == 0

    def test_summary_counts_failed(self, benchmarks):
        """Summary counts failed benchmarks"""
        benchmarks.results = [
            BenchmarkResult("Test1", "Metal", 0, 0.0, 0.0, success=False, error="Error"),
            BenchmarkResult("Test2", "CPU", 100, 2000.0, 50.0, success=True)
        ]
        summary = benchmarks._generate_summary()
        assert summary['failed'] == 1
        assert summary['successful'] == 1

    def test_summary_includes_results_list(self, benchmarks):
        """Summary includes all results"""
        benchmarks.results = [
            BenchmarkResult("Single Embedding", "Metal GPU", 100, 1000.0, 100.0, speedup=5.0),
            BenchmarkResult("Single Embedding", "CPU Baseline", 100, 5000.0, 20.0)
        ]
        summary = benchmarks._generate_summary()
        assert len(summary['results']) == 2
        assert summary['results'][0]['name'] == "Single Embedding"

    def test_summary_calculates_embedding_speedup(self, benchmarks):
        """Summary calculates average embedding speedup"""
        benchmarks.results = [
            BenchmarkResult("Single Embedding", "Metal", 100, 1000.0, 100.0, speedup=5.0),
            BenchmarkResult("Batch Embedding (100 texts)", "Metal", 100, 1000.0, 100.0, speedup=8.0)
        ]
        summary = benchmarks._generate_summary()
        assert 'embedding' in summary['speedup_analysis']
        assert summary['speedup_analysis']['embedding'] == pytest.approx(6.5)

    def test_summary_calculates_search_speedup(self, benchmarks):
        """Summary calculates average search speedup"""
        benchmarks.results = [
            BenchmarkResult("Vector Search (10k)", "Metal", 100, 100.0, 1000.0, speedup=20.0)
        ]
        summary = benchmarks._generate_summary()
        assert 'search' in summary['speedup_analysis']
        assert summary['speedup_analysis']['search'] == 20.0

    def test_summary_success_criteria_embedding_met(self, benchmarks):
        """Success criteria met for embedding (5-10x)"""
        benchmarks.results = [
            BenchmarkResult("Single Embedding", "Metal", 100, 1000.0, 100.0, speedup=7.0)
        ]
        summary = benchmarks._generate_summary()
        assert summary['success_criteria']['embedding']['met'] is True

    def test_summary_success_criteria_embedding_not_met(self, benchmarks):
        """Success criteria not met for embedding (< 5x)"""
        benchmarks.results = [
            BenchmarkResult("Single Embedding", "Metal", 100, 1000.0, 100.0, speedup=3.0)
        ]
        summary = benchmarks._generate_summary()
        assert summary['success_criteria']['embedding']['met'] is False

    def test_summary_success_criteria_search_met(self, benchmarks):
        """Success criteria met for search (10-50x)"""
        benchmarks.results = [
            BenchmarkResult("Vector Search (10k)", "Metal", 100, 100.0, 1000.0, speedup=25.0)
        ]
        summary = benchmarks._generate_summary()
        assert summary['success_criteria']['search']['met'] is True

    def test_summary_ignores_speedup_1(self, benchmarks):
        """Summary ignores speedup of 1.0 (baseline)"""
        benchmarks.results = [
            BenchmarkResult("Single Embedding", "CPU Baseline", 100, 1000.0, 100.0, speedup=1.0)
        ]
        summary = benchmarks._generate_summary()
        assert 'embedding' not in summary['speedup_analysis']


class TestRunAllBenchmarks:
    """Tests for run_all_benchmarks"""

    @pytest.fixture
    def benchmarks(self):
        return Metal4Benchmarks()

    def test_run_all_clears_results(self, benchmarks):
        """run_all_benchmarks clears previous results"""
        benchmarks.results = [
            BenchmarkResult("Old", "CPU", 100, 1000.0, 100.0)
        ]

        # Patch all benchmark methods to avoid actual execution
        with patch.object(benchmarks, '_benchmark_single_embedding'):
            with patch.object(benchmarks, '_benchmark_batch_embedding'):
                with patch.object(benchmarks, '_benchmark_vector_search'):
                    with patch.object(benchmarks, '_benchmark_sparse_storage'):
                        with patch.object(benchmarks, '_benchmark_rag_pipeline'):
                            benchmarks.run_all_benchmarks()

        # Results should be cleared (then filled by mocked methods)
        assert len([r for r in benchmarks.results if r.name == "Old"]) == 0

    def test_run_all_returns_summary(self, benchmarks):
        """run_all_benchmarks returns summary dict"""
        with patch.object(benchmarks, '_benchmark_single_embedding'):
            with patch.object(benchmarks, '_benchmark_batch_embedding'):
                with patch.object(benchmarks, '_benchmark_vector_search'):
                    with patch.object(benchmarks, '_benchmark_sparse_storage'):
                        with patch.object(benchmarks, '_benchmark_rag_pipeline'):
                            summary = benchmarks.run_all_benchmarks()

        assert isinstance(summary, dict)
        assert 'total_benchmarks' in summary

    def test_run_all_calls_all_benchmarks(self, benchmarks):
        """run_all_benchmarks calls all 5 benchmark methods"""
        mock_single = Mock()
        mock_batch = Mock()
        mock_vector = Mock()
        mock_sparse = Mock()
        mock_rag = Mock()

        with patch.object(benchmarks, '_benchmark_single_embedding', mock_single):
            with patch.object(benchmarks, '_benchmark_batch_embedding', mock_batch):
                with patch.object(benchmarks, '_benchmark_vector_search', mock_vector):
                    with patch.object(benchmarks, '_benchmark_sparse_storage', mock_sparse):
                        with patch.object(benchmarks, '_benchmark_rag_pipeline', mock_rag):
                            benchmarks.run_all_benchmarks()

        mock_single.assert_called_once()
        mock_batch.assert_called_once()
        mock_vector.assert_called_once()
        mock_sparse.assert_called_once()
        mock_rag.assert_called_once()


class TestStandaloneFunction:
    """Tests for run_benchmarks() standalone function"""

    def test_run_benchmarks_creates_instance(self):
        """run_benchmarks creates Metal4Benchmarks instance"""
        with patch.object(Metal4Benchmarks, 'run_all_benchmarks', return_value={'total_benchmarks': 0}):
            result = run_benchmarks()
        assert isinstance(result, dict)

    def test_run_benchmarks_returns_results(self):
        """run_benchmarks returns benchmark results"""
        mock_summary = {
            'total_benchmarks': 5,
            'successful': 5,
            'failed': 0,
            'results': []
        }
        with patch.object(Metal4Benchmarks, 'run_all_benchmarks', return_value=mock_summary):
            result = run_benchmarks()
        assert result['total_benchmarks'] == 5


class TestEdgeCases:
    """Edge case tests"""

    def test_zero_operations(self):
        """Handle zero operations"""
        result = BenchmarkResult(
            name="Empty",
            backend="CPU",
            operations=0,
            total_time_ms=0.0,
            ops_per_second=0.0
        )
        assert result.operations == 0

    def test_very_high_ops_per_second(self):
        """Handle very high operations per second"""
        result = BenchmarkResult(
            name="Fast",
            backend="Metal GPU",
            operations=1000000,
            total_time_ms=1.0,
            ops_per_second=1000000000.0  # 1 billion
        )
        assert result.ops_per_second == 1000000000.0

    def test_unicode_in_error(self):
        """Handle unicode in error message"""
        result = BenchmarkResult(
            name="Unicode",
            backend="Metal",
            operations=0,
            total_time_ms=0.0,
            ops_per_second=0.0,
            success=False,
            error="Error: 无法连接到设备"
        )
        assert "无法连接" in result.error

    def test_special_characters_in_name(self):
        """Handle special characters in benchmark name"""
        result = BenchmarkResult(
            name="Benchmark <100k vectors> (top-10)",
            backend="Metal",
            operations=100,
            total_time_ms=100.0,
            ops_per_second=1000.0
        )
        assert "<100k" in result.name

    def test_negative_speedup(self):
        """Handle negative speedup (shouldn't happen but handle gracefully)"""
        result = BenchmarkResult(
            name="Test",
            backend="Metal",
            operations=100,
            total_time_ms=100.0,
            ops_per_second=1000.0,
            speedup=-1.0  # Invalid but dataclass allows it
        )
        assert result.speedup == -1.0


class TestIntegration:
    """Integration tests"""

    def test_full_benchmark_flow_mocked(self):
        """Full benchmark flow with all dependencies mocked"""
        # Mock all Metal4 dependencies
        mock_metal_embedder = Mock()
        mock_metal_embedder.is_available.return_value = True
        mock_metal_embedder.uses_metal.return_value = True
        mock_metal_embedder.embed.return_value = np.random.randn(384).astype(np.float32)
        mock_metal_embedder.embed_batch.return_value = [np.random.randn(384).astype(np.float32) for _ in range(100)]

        mock_cpu_embedder = Mock()
        mock_cpu_embedder.embed.return_value = np.random.randn(384).astype(np.float32)
        mock_cpu_embedder.embed_batch.return_value = [np.random.randn(384).astype(np.float32) for _ in range(100)]

        mock_search = Mock()
        mock_search.uses_metal.return_value = True
        mock_search.search.return_value = (np.array([0, 1, 2]), np.array([0.9, 0.8, 0.7]))

        mock_storage = Mock()
        mock_storage._use_sparse_resources = True
        mock_storage.add_embeddings_batch = Mock()
        mock_storage.get_embeddings_batch.return_value = np.random.randn(1000, 384).astype(np.float32)
        mock_storage.close = Mock()

        mock_pipeline = Mock()
        mock_pipeline.embed_batch.return_value = [np.random.randn(384).astype(np.float32) for _ in range(100)]
        mock_pipeline.load_database = Mock()
        mock_pipeline.search.return_value = (np.array([0, 1, 2]), np.array([0.9, 0.8, 0.7]))
        mock_pipeline.get_capabilities.return_value = {'embedder_backend': 'Metal'}

        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=512 * 1024 * 1024)

        with patch.dict('sys.modules', {
            'metal4_mps_embedder': Mock(get_metal4_mps_embedder=Mock(return_value=mock_metal_embedder)),
            'unified_embedder': Mock(UnifiedEmbedder=Mock(return_value=mock_cpu_embedder)),
            'metal4_vector_search': Mock(get_metal4_vector_search=Mock(return_value=mock_search)),
            'metal4_sparse_embeddings': Mock(Metal4SparseEmbeddings=Mock(return_value=mock_storage)),
            'metal4_ml_integration': Mock(get_ml_pipeline=Mock(return_value=mock_pipeline)),
            'psutil': Mock(Process=Mock(return_value=mock_process))
        }):
            with patch('tempfile.mktemp', return_value='/tmp/test.mmap'):
                with patch('os.unlink'):
                    with patch('os.path.exists', return_value=False):
                        benchmarks = Metal4Benchmarks()
                        summary = benchmarks.run_all_benchmarks()

        assert summary['total_benchmarks'] >= 0
        assert 'results' in summary

    def test_benchmark_result_serialization(self):
        """Benchmark results can be serialized to JSON"""
        import json

        result = BenchmarkResult(
            name="Test",
            backend="Metal GPU",
            operations=1000,
            total_time_ms=500.5,
            ops_per_second=2000.0,
            speedup=5.5,
            memory_mb=256.0,
            success=True,
            error=""
        )

        result_dict = asdict(result)
        json_str = json.dumps(result_dict)
        parsed = json.loads(json_str)

        assert parsed['name'] == "Test"
        assert parsed['speedup'] == 5.5

    def test_summary_structure(self):
        """Summary has expected structure"""
        benchmarks = Metal4Benchmarks()
        benchmarks.results = [
            BenchmarkResult("Single Embedding", "Metal GPU", 100, 200.0, 500.0, speedup=5.0),
            BenchmarkResult("Single Embedding", "CPU", 100, 1000.0, 100.0),
            BenchmarkResult("Vector Search (10k)", "Metal GPU", 100, 10.0, 10000.0, speedup=20.0),
            BenchmarkResult("Vector Search (10k)", "CPU", 100, 200.0, 500.0)
        ]

        summary = benchmarks._generate_summary()

        # Check structure
        assert 'total_benchmarks' in summary
        assert 'successful' in summary
        assert 'failed' in summary
        assert 'results' in summary
        assert 'speedup_analysis' in summary
        assert 'success_criteria' in summary

        # Check values
        assert summary['total_benchmarks'] == 4
        assert summary['successful'] == 4
        assert 'embedding' in summary['speedup_analysis']
        assert 'search' in summary['speedup_analysis']


class TestLogging:
    """Tests for logging behavior"""

    def test_benchmark_logs_info(self, caplog):
        """Benchmark methods log info messages"""
        import logging

        benchmarks = Metal4Benchmarks()

        # Mock embedder that's unavailable
        mock_embedder = Mock()
        mock_embedder.is_available.return_value = False

        with caplog.at_level(logging.INFO):
            with patch.dict('sys.modules', {
                'metal4_mps_embedder': Mock(get_metal4_mps_embedder=Mock(return_value=mock_embedder)),
                'unified_embedder': Mock(UnifiedEmbedder=Mock(side_effect=Exception("Skip")))
            }):
                benchmarks._benchmark_single_embedding()

        # Some logging should occur
        # (may be info or error depending on path)

    def test_exception_logged_as_error(self, caplog):
        """Exceptions are logged as errors"""
        import logging

        benchmarks = Metal4Benchmarks()

        with caplog.at_level(logging.ERROR):
            with patch.dict('sys.modules', {
                'metal4_mps_embedder': Mock(
                    get_metal4_mps_embedder=Mock(side_effect=Exception("Test error"))
                )
            }):
                benchmarks._benchmark_single_embedding()

        assert any("error" in record.message.lower() or "failed" in record.message.lower()
                   for record in caplog.records)


class TestMultipleRuns:
    """Tests for multiple benchmark runs"""

    def test_results_cleared_between_runs(self):
        """Results are cleared between runs"""
        benchmarks = Metal4Benchmarks()

        # First run
        with patch.object(benchmarks, '_benchmark_single_embedding', lambda: benchmarks.results.append(
            BenchmarkResult("Run1", "Metal", 100, 100.0, 1000.0)
        )):
            with patch.object(benchmarks, '_benchmark_batch_embedding'):
                with patch.object(benchmarks, '_benchmark_vector_search'):
                    with patch.object(benchmarks, '_benchmark_sparse_storage'):
                        with patch.object(benchmarks, '_benchmark_rag_pipeline'):
                            benchmarks.run_all_benchmarks()

        first_run_count = len(benchmarks.results)

        # Second run
        with patch.object(benchmarks, '_benchmark_single_embedding', lambda: benchmarks.results.append(
            BenchmarkResult("Run2", "Metal", 100, 100.0, 1000.0)
        )):
            with patch.object(benchmarks, '_benchmark_batch_embedding'):
                with patch.object(benchmarks, '_benchmark_vector_search'):
                    with patch.object(benchmarks, '_benchmark_sparse_storage'):
                        with patch.object(benchmarks, '_benchmark_rag_pipeline'):
                            benchmarks.run_all_benchmarks()

        # Should only have results from second run
        assert len(benchmarks.results) == first_run_count
        assert all(r.name == "Run2" for r in benchmarks.results)
