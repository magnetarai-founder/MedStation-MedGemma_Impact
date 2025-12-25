#!/usr/bin/env python3
"""
Metal 4 Performance Benchmarks and Validation Tests

"Test me, Lord, and try me, examine my heart and my mind" - Psalm 26:2

Comprehensive benchmarking suite for Metal 4 ML acceleration:
- Embedding performance (Metal vs CPU)
- Vector search performance (Metal vs CPU)
- Sparse storage performance
- End-to-end RAG pipeline benchmarks

Success Criteria (from Phase 1 roadmap):
- Embeddings: 5-10x faster on Metal vs CPU
- Vector search: 10-50x faster on Metal vs CPU
- Memory usage: <2GB for 1M vectors with sparse resources
"""

import time
import logging
from typing import Any
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result from a single benchmark"""
    name: str
    backend: str
    operations: int
    total_time_ms: float
    ops_per_second: float
    speedup: float = 1.0
    memory_mb: float = 0.0
    success: bool = True
    error: str = ""


class Metal4Benchmarks:
    """
    Comprehensive benchmark suite for Metal 4 ML acceleration

    Tests:
    1. Single embedding (Metal vs CPU)
    2. Batch embedding (Metal vs CPU)
    3. Vector similarity search (Metal vs CPU)
    4. Sparse storage (load/retrieve performance)
    5. End-to-end RAG pipeline
    """

    def __init__(self):
        """Initialize benchmark suite"""
        self.results: list[BenchmarkResult] = []

    def run_all_benchmarks(self) -> dict[str, Any]:
        """
        Run complete benchmark suite

        Returns:
            Benchmark summary with all results
        """
        logger.info("\n" + "=" * 70)
        logger.info("METAL 4 ML ACCELERATION BENCHMARKS")
        logger.info("=" * 70)

        self.results = []

        # Benchmark 1: Single Embedding Performance
        self._benchmark_single_embedding()

        # Benchmark 2: Batch Embedding Performance
        self._benchmark_batch_embedding()

        # Benchmark 3: Vector Search Performance
        self._benchmark_vector_search()

        # Benchmark 4: Sparse Storage Performance
        self._benchmark_sparse_storage()

        # Benchmark 5: End-to-End RAG Pipeline
        self._benchmark_rag_pipeline()

        # Generate summary
        summary = self._generate_summary()

        logger.info("\n" + "=" * 70)
        logger.info("BENCHMARK COMPLETE")
        logger.info("=" * 70)

        return summary

    def _benchmark_single_embedding(self) -> None:
        """Benchmark single text embedding"""
        logger.info("\n--- Benchmark 1: Single Embedding Performance ---")

        test_text = "The Lord is my shepherd, I shall not want. He makes me lie down in green pastures."

        # Test Metal 4 MPS Embedder
        try:
            from metal4_mps_embedder import get_metal4_mps_embedder

            embedder = get_metal4_mps_embedder()

            if embedder.is_available():
                # Warmup
                for _ in range(5):
                    _ = embedder.embed(test_text)

                # Benchmark
                num_ops = 100
                start = time.time()
                for _ in range(num_ops):
                    _ = embedder.embed(test_text)
                elapsed_ms = (time.time() - start) * 1000

                backend = "Metal GPU" if embedder.uses_metal() else "CPU"
                ops_per_sec = num_ops / (elapsed_ms / 1000)

                result = BenchmarkResult(
                    name="Single Embedding",
                    backend=backend,
                    operations=num_ops,
                    total_time_ms=elapsed_ms,
                    ops_per_second=ops_per_sec
                )

                self.results.append(result)
                logger.info(f"✓ {backend}: {ops_per_sec:.1f} embeddings/sec ({elapsed_ms/num_ops:.2f}ms per embedding)")

        except Exception as e:
            logger.error(f"Metal embedding benchmark failed: {e}")
            self.results.append(BenchmarkResult(
                name="Single Embedding",
                backend="Metal",
                operations=0,
                total_time_ms=0,
                ops_per_second=0,
                success=False,
                error=str(e)
            ))

        # CPU Baseline (using unified embedder with hash fallback)
        try:
            from unified_embedder import UnifiedEmbedder

            cpu_embedder = UnifiedEmbedder()
            cpu_embedder.backend = 'hash'  # Force hash fallback for fair comparison
            cpu_embedder.initialize()

            # Warmup
            for _ in range(5):
                _ = cpu_embedder.embed(test_text)

            # Benchmark
            num_ops = 100
            start = time.time()
            for _ in range(num_ops):
                _ = cpu_embedder.embed(test_text)
            elapsed_ms = (time.time() - start) * 1000

            ops_per_sec = num_ops / (elapsed_ms / 1000)

            result = BenchmarkResult(
                name="Single Embedding",
                backend="CPU Baseline",
                operations=num_ops,
                total_time_ms=elapsed_ms,
                ops_per_second=ops_per_sec
            )

            self.results.append(result)
            logger.info(f"✓ CPU: {ops_per_sec:.1f} embeddings/sec ({elapsed_ms/num_ops:.2f}ms per embedding)")

            # Calculate speedup
            if len(self.results) >= 2:
                metal_result = self.results[-2]
                cpu_result = self.results[-1]
                speedup = metal_result.ops_per_second / cpu_result.ops_per_second
                metal_result.speedup = speedup
                logger.info(f"📊 Speedup: {speedup:.2f}x (Target: 5-10x)")

        except Exception as e:
            logger.error(f"CPU baseline failed: {e}")

    def _benchmark_batch_embedding(self) -> None:
        """Benchmark batch embedding performance"""
        logger.info("\n--- Benchmark 2: Batch Embedding Performance ---")

        # Generate test data
        test_texts = [
            f"This is test sentence number {i} for batch embedding benchmark."
            for i in range(100)
        ]

        # Test Metal 4 MPS Embedder
        try:
            from metal4_mps_embedder import get_metal4_mps_embedder

            embedder = get_metal4_mps_embedder()

            if embedder.is_available():
                # Warmup
                _ = embedder.embed_batch(test_texts[:10])

                # Benchmark
                start = time.time()
                _ = embedder.embed_batch(test_texts)
                elapsed_ms = (time.time() - start) * 1000

                backend = "Metal GPU" if embedder.uses_metal() else "CPU"
                ops_per_sec = len(test_texts) / (elapsed_ms / 1000)

                result = BenchmarkResult(
                    name="Batch Embedding (100 texts)",
                    backend=backend,
                    operations=len(test_texts),
                    total_time_ms=elapsed_ms,
                    ops_per_second=ops_per_sec
                )

                self.results.append(result)
                logger.info(f"✓ {backend}: {ops_per_sec:.1f} texts/sec ({elapsed_ms:.1f}ms total)")

        except Exception as e:
            logger.error(f"Metal batch embedding failed: {e}")

        # CPU Baseline
        try:
            from unified_embedder import UnifiedEmbedder

            cpu_embedder = UnifiedEmbedder()
            cpu_embedder.backend = 'hash'
            cpu_embedder.initialize()

            # Warmup
            _ = cpu_embedder.embed_batch(test_texts[:10])

            # Benchmark
            start = time.time()
            _ = cpu_embedder.embed_batch(test_texts)
            elapsed_ms = (time.time() - start) * 1000

            ops_per_sec = len(test_texts) / (elapsed_ms / 1000)

            result = BenchmarkResult(
                name="Batch Embedding (100 texts)",
                backend="CPU Baseline",
                operations=len(test_texts),
                total_time_ms=elapsed_ms,
                ops_per_second=ops_per_sec
            )

            self.results.append(result)
            logger.info(f"✓ CPU: {ops_per_sec:.1f} texts/sec ({elapsed_ms:.1f}ms total)")

            # Calculate speedup
            if len(self.results) >= 2:
                metal_idx = -2
                cpu_idx = -1
                speedup = self.results[metal_idx].ops_per_second / self.results[cpu_idx].ops_per_second
                self.results[metal_idx].speedup = speedup
                logger.info(f"📊 Speedup: {speedup:.2f}x (Target: 5-10x)")

        except Exception as e:
            logger.error(f"CPU batch baseline failed: {e}")

    def _benchmark_vector_search(self) -> None:
        """Benchmark vector similarity search"""
        logger.info("\n--- Benchmark 3: Vector Similarity Search ---")

        # Generate test database
        num_vectors = 10000
        embed_dim = 384
        database = np.random.randn(num_vectors, embed_dim).astype(np.float32)
        query = np.random.randn(embed_dim).astype(np.float32)

        # Normalize for fair comparison
        database = database / np.linalg.norm(database, axis=1, keepdims=True)
        query = query / np.linalg.norm(query)

        # Test Metal 4 Vector Search
        try:
            from metal4_vector_search import get_metal4_vector_search

            search = get_metal4_vector_search()
            search.load_database(database)

            # Warmup
            for _ in range(5):
                _ = search.search(query, k=10, metric="dot")

            # Benchmark
            num_queries = 100
            start = time.time()
            for _ in range(num_queries):
                _ = search.search(query, k=10, metric="dot")
            elapsed_ms = (time.time() - start) * 1000

            backend = "Metal GPU" if search.uses_metal() else "CPU"
            ops_per_sec = num_queries / (elapsed_ms / 1000)

            result = BenchmarkResult(
                name=f"Vector Search (10k vectors, top-10)",
                backend=backend,
                operations=num_queries,
                total_time_ms=elapsed_ms,
                ops_per_second=ops_per_sec
            )

            self.results.append(result)
            logger.info(f"✓ {backend}: {ops_per_sec:.1f} searches/sec ({elapsed_ms/num_queries:.2f}ms per search)")

        except Exception as e:
            logger.error(f"Metal vector search failed: {e}")
            import traceback
            traceback.print_exc()

        # CPU Baseline (NumPy)
        try:
            # Warmup
            for _ in range(5):
                scores = np.dot(database, query)
                _ = np.argsort(scores)[::-1][:10]

            # Benchmark
            num_queries = 100
            start = time.time()
            for _ in range(num_queries):
                scores = np.dot(database, query)
                _ = np.argsort(scores)[::-1][:10]
            elapsed_ms = (time.time() - start) * 1000

            ops_per_sec = num_queries / (elapsed_ms / 1000)

            result = BenchmarkResult(
                name=f"Vector Search (10k vectors, top-10)",
                backend="CPU Baseline (NumPy)",
                operations=num_queries,
                total_time_ms=elapsed_ms,
                ops_per_second=ops_per_sec
            )

            self.results.append(result)
            logger.info(f"✓ CPU: {ops_per_sec:.1f} searches/sec ({elapsed_ms/num_queries:.2f}ms per search)")

            # Calculate speedup
            if len(self.results) >= 2:
                metal_idx = -2
                cpu_idx = -1
                speedup = self.results[metal_idx].ops_per_second / self.results[cpu_idx].ops_per_second
                self.results[metal_idx].speedup = speedup
                logger.info(f"📊 Speedup: {speedup:.2f}x (Target: 10-50x)")

        except Exception as e:
            logger.error(f"CPU search baseline failed: {e}")

    def _benchmark_sparse_storage(self) -> None:
        """Benchmark sparse embedding storage"""
        logger.info("\n--- Benchmark 4: Sparse Storage Performance ---")

        try:
            from metal4_sparse_embeddings import Metal4SparseEmbeddings
            import tempfile
            import os

            # Create temporary storage
            temp_file = tempfile.mktemp(suffix='.mmap')

            storage = Metal4SparseEmbeddings(
                embed_dim=384,
                max_vectors=100000,
                backing_file=temp_file,
                gpu_cache_size_mb=512
            )

            # Benchmark: Write performance
            num_vectors = 1000
            test_embeddings = np.random.randn(num_vectors, 384).astype(np.float32)
            vector_ids = list(range(num_vectors))

            start = time.time()
            storage.add_embeddings_batch(vector_ids, test_embeddings)
            write_time_ms = (time.time() - start) * 1000

            write_ops_per_sec = num_vectors / (write_time_ms / 1000)

            logger.info(f"✓ Write: {write_ops_per_sec:.1f} vectors/sec ({write_time_ms:.1f}ms for {num_vectors} vectors)")

            # Benchmark: Read performance
            start = time.time()
            _ = storage.get_embeddings_batch(vector_ids)
            read_time_ms = (time.time() - start) * 1000

            read_ops_per_sec = num_vectors / (read_time_ms / 1000)

            logger.info(f"✓ Read: {read_ops_per_sec:.1f} vectors/sec ({read_time_ms:.1f}ms for {num_vectors} vectors)")

            # Check memory usage
            import psutil
            import os as os_module
            process = psutil.Process(os_module.getpid())
            memory_mb = process.memory_info().rss / (1024 * 1024)

            backend = "Metal 4 Sparse" if storage._use_sparse_resources else "Memory-mapped"

            result = BenchmarkResult(
                name="Sparse Storage (1k vectors)",
                backend=backend,
                operations=num_vectors * 2,  # Read + write
                total_time_ms=write_time_ms + read_time_ms,
                ops_per_second=(num_vectors * 2) / ((write_time_ms + read_time_ms) / 1000),
                memory_mb=memory_mb
            )

            self.results.append(result)
            logger.info(f"📊 Backend: {backend}, Memory: {memory_mb:.1f} MB")

            # Cleanup
            storage.close()
            os.unlink(temp_file)
            meta_file = temp_file.replace('.mmap', '.meta')
            if os.path.exists(meta_file):
                os.unlink(meta_file)

        except Exception as e:
            logger.error(f"Sparse storage benchmark failed: {e}")
            import traceback
            traceback.print_exc()

    def _benchmark_rag_pipeline(self) -> None:
        """Benchmark end-to-end RAG pipeline"""
        logger.info("\n--- Benchmark 5: End-to-End RAG Pipeline ---")

        try:
            from metal4_ml_integration import get_ml_pipeline

            pipeline = get_ml_pipeline()

            # Create knowledge base
            knowledge_base = [
                "The Lord is my shepherd, I shall not want.",
                "He makes me lie down in green pastures.",
                "He leads me beside quiet waters.",
                "He refreshes my soul.",
                "He guides me along the right paths for his name's sake."
            ] * 20  # 100 documents

            # Build index
            logger.info(f"Building index with {len(knowledge_base)} documents...")
            start = time.time()

            # Embed all documents
            embeddings = pipeline.embed_batch(knowledge_base)
            embeddings_array = np.array(embeddings, dtype=np.float32)

            # Load into search index
            pipeline.load_database(embeddings_array)

            index_time_ms = (time.time() - start) * 1000
            logger.info(f"✓ Index built in {index_time_ms:.1f}ms")

            # Benchmark queries
            queries = [
                "What does the Lord do?",
                "Where does he lead me?",
                "What happens to my soul?"
            ]

            # Warmup
            for query in queries:
                _ = pipeline.search(query, k=3)

            # Benchmark
            num_iterations = 10
            start = time.time()

            for _ in range(num_iterations):
                for query in queries:
                    indices, scores = pipeline.search(query, k=3)

            elapsed_ms = (time.time() - start) * 1000
            total_queries = num_iterations * len(queries)
            queries_per_sec = total_queries / (elapsed_ms / 1000)

            result = BenchmarkResult(
                name="RAG Pipeline (100 docs, 3 queries)",
                backend=f"Metal {pipeline.get_capabilities()['embedder_backend']}",
                operations=total_queries,
                total_time_ms=elapsed_ms,
                ops_per_second=queries_per_sec
            )

            self.results.append(result)
            logger.info(f"✓ RAG Pipeline: {queries_per_sec:.1f} queries/sec ({elapsed_ms/total_queries:.2f}ms per query)")

        except Exception as e:
            logger.error(f"RAG pipeline benchmark failed: {e}")
            import traceback
            traceback.print_exc()

    def _generate_summary(self) -> dict[str, Any]:
        """Generate benchmark summary and print results"""
        summary = {
            'total_benchmarks': len(self.results),
            'successful': sum(1 for r in self.results if r.success),
            'failed': sum(1 for r in self.results if not r.success),
            'results': [],
            'speedup_analysis': {},
            'success_criteria': {}
        }

        # Organize results
        for result in self.results:
            summary['results'].append({
                'name': result.name,
                'backend': result.backend,
                'operations': result.operations,
                'total_time_ms': result.total_time_ms,
                'ops_per_second': result.ops_per_second,
                'speedup': result.speedup,
                'memory_mb': result.memory_mb,
                'success': result.success,
                'error': result.error
            })

        # Calculate average speedups
        embedding_speedups = [r.speedup for r in self.results if 'Embedding' in r.name and r.speedup > 1]
        search_speedups = [r.speedup for r in self.results if 'Search' in r.name and r.speedup > 1]

        if embedding_speedups:
            avg_embedding_speedup = sum(embedding_speedups) / len(embedding_speedups)
            summary['speedup_analysis']['embedding'] = avg_embedding_speedup
            summary['success_criteria']['embedding'] = {
                'target': '5-10x',
                'actual': f'{avg_embedding_speedup:.2f}x',
                'met': 5.0 <= avg_embedding_speedup <= 10.0
            }

        if search_speedups:
            avg_search_speedup = sum(search_speedups) / len(search_speedups)
            summary['speedup_analysis']['search'] = avg_search_speedup
            summary['success_criteria']['search'] = {
                'target': '10-50x',
                'actual': f'{avg_search_speedup:.2f}x',
                'met': 10.0 <= avg_search_speedup <= 50.0
            }

        # Print summary
        logger.info("\n📊 BENCHMARK SUMMARY")
        logger.info(f"   Total benchmarks: {summary['total_benchmarks']}")
        logger.info(f"   Successful: {summary['successful']}")
        logger.info(f"   Failed: {summary['failed']}")

        if 'embedding' in summary['speedup_analysis']:
            logger.info(f"\n   Embedding Speedup: {summary['speedup_analysis']['embedding']:.2f}x")
            logger.info(f"   Target: 5-10x | Met: {summary['success_criteria']['embedding']['met']}")

        if 'search' in summary['speedup_analysis']:
            logger.info(f"\n   Search Speedup: {summary['speedup_analysis']['search']:.2f}x")
            logger.info(f"   Target: 10-50x | Met: {summary['success_criteria']['search']['met']}")

        return summary


# ===== Standalone Execution =====

def run_benchmarks() -> dict[str, Any]:
    """Run all benchmarks and return results"""
    benchmarks = Metal4Benchmarks()
    return benchmarks.run_all_benchmarks()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )

    results = run_benchmarks()

    # Save results
    import json
    from pathlib import Path

    results_file = Path.home() / "Desktop" / "metal4_benchmark_results.json"
    results_file.write_text(json.dumps(results, indent=2))

    print(f"\n✅ Benchmark results saved to: {results_file}")


# Export
__all__ = [
    'Metal4Benchmarks',
    'BenchmarkResult',
    'run_benchmarks'
]
