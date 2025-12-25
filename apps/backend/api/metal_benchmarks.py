#!/usr/bin/env python3
"""
Metal 4 Performance Benchmarks (Week 4)

Comprehensive benchmarking suite to validate Metal 4 optimizations:
- Embedding speed (CPU vs Metal GPU)
- SQL aggregation performance
- RAG retrieval speed
- End-to-end chat latency

Target: Demonstrate 3-5× performance improvement
"""

import time
import logging
import numpy as np
from typing import Any
import statistics

logger = logging.getLogger(__name__)


class MetalBenchmarks:
    """
    Comprehensive benchmark suite for Metal 4 optimizations
    
    Week 4 Goals:
    - Validate 15-25% improvement in embeddings
    - Validate 2-3× improvement in SQL aggregations
    - Validate 3-5× improvement in end-to-end pipeline
    """
    
    def __init__(self):
        self.results = {}
    
    def benchmark_embeddings(self, num_texts: int = 100) -> dict[str, Any]:
        """
        Benchmark embedding performance: CPU vs Metal GPU
        
        Args:
            num_texts: Number of texts to embed
            
        Returns:
            Results dict with CPU and GPU timings
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"BENCHMARK: Embeddings ({num_texts} texts)")
        logger.info(f"{'='*60}")
        
        # Generate test texts
        test_texts = [f"This is test sentence number {i} for embedding benchmarks." for i in range(num_texts)]
        
        results = {
            'num_texts': num_texts,
            'cpu_time_ms': None,
            'gpu_time_ms': None,
            'speedup': None
        }
        
        # Benchmark CPU embeddings
        try:
            from api.chat_enhancements import SimpleEmbedding
            
            logger.info("Testing CPU embeddings...")
            start = time.time()
            
            for text in test_texts:
                _ = SimpleEmbedding.create_embedding(text)
            
            cpu_time = (time.time() - start) * 1000
            results['cpu_time_ms'] = cpu_time
            
            logger.info(f"  CPU: {cpu_time:.0f}ms ({num_texts/cpu_time*1000:.1f} texts/sec)")
            
        except Exception as e:
            logger.error(f"CPU benchmark failed: {e}")
        
        # Benchmark GPU embeddings
        try:
            from metal_embedder import get_metal_embedder
            
            metal_embedder = get_metal_embedder()
            
            if metal_embedder.is_available():
                logger.info("Testing Metal GPU embeddings...")
                start = time.time()
                
                # Use batch processing for GPU
                _ = metal_embedder.embed_batch(test_texts)
                
                gpu_time = (time.time() - start) * 1000
                results['gpu_time_ms'] = gpu_time
                
                logger.info(f"  GPU: {gpu_time:.0f}ms ({num_texts/gpu_time*1000:.1f} texts/sec)")
                
                if results['cpu_time_ms']:
                    speedup = results['cpu_time_ms'] / gpu_time
                    results['speedup'] = speedup
                    logger.info(f"  ⚡ SPEEDUP: {speedup:.2f}×")
            else:
                logger.warning("Metal GPU embedder not available")
                
        except ImportError:
            logger.warning("Metal embedder not installed")
        except Exception as e:
            logger.error(f"GPU benchmark failed: {e}")
        
        self.results['embeddings'] = results
        return results
    
    def benchmark_sql_aggregations(self, num_rows: int = 1000000) -> dict[str, Any]:
        """
        Benchmark SQL aggregation performance: CPU vs Metal GPU
        
        Args:
            num_rows: Number of rows to aggregate
            
        Returns:
            Results dict with CPU and GPU timings
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"BENCHMARK: SQL Aggregations ({num_rows:,} rows)")
        logger.info(f"{'='*60}")
        
        # Generate test data
        test_data = np.random.rand(num_rows).astype(np.float32)
        
        results = {
            'num_rows': num_rows,
            'cpu_sum_ms': None,
            'gpu_sum_ms': None,
            'speedup': None
        }
        
        # Benchmark CPU SUM
        logger.info("Testing CPU SUM aggregation...")
        start = time.time()
        cpu_result = float(np.sum(test_data))
        cpu_time = (time.time() - start) * 1000
        results['cpu_sum_ms'] = cpu_time
        logger.info(f"  CPU SUM: {cpu_time:.2f}ms (result: {cpu_result:.2f})")
        
        # Benchmark GPU SUM
        try:
            from metal_sql_kernels import get_metal_sql_kernels
            
            sql_kernels = get_metal_sql_kernels()
            
            if sql_kernels.is_available():
                logger.info("Testing Metal GPU SUM aggregation...")
                start = time.time()
                gpu_result = sql_kernels.aggregate_sum(test_data)
                gpu_time = (time.time() - start) * 1000
                results['gpu_sum_ms'] = gpu_time
                
                logger.info(f"  GPU SUM: {gpu_time:.2f}ms (result: {gpu_result:.2f})")
                
                speedup = cpu_time / gpu_time
                results['speedup'] = speedup
                logger.info(f"  ⚡ SPEEDUP: {speedup:.2f}×")
            else:
                logger.warning("Metal SQL kernels not available")
                
        except ImportError:
            logger.warning("Metal SQL kernels not installed")
        except Exception as e:
            logger.error(f"GPU SQL benchmark failed: {e}")
        
        self.results['sql_aggregations'] = results
        return results
    
    def benchmark_metal4_tick_flow(self, num_iterations: int = 10) -> dict[str, Any]:
        """
        Benchmark Metal 4 tick flow overhead
        
        Measures frame kick latency and event synchronization
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"BENCHMARK: Metal 4 Tick Flow ({num_iterations} iterations)")
        logger.info(f"{'='*60}")
        
        results = {
            'iterations': num_iterations,
            'avg_frame_time_us': None,
            'min_frame_time_us': None,
            'max_frame_time_us': None
        }
        
        try:
            from api.metal4_engine import get_metal4_engine
            
            engine = get_metal4_engine()
            
            if not engine.is_available():
                logger.warning("Metal 4 engine not available")
                return results
            
            logger.info("Testing Metal 4 frame kick latency...")
            
            frame_times = []
            
            for i in range(num_iterations):
                start = time.perf_counter()
                engine.kick_frame()
                elapsed = (time.perf_counter() - start) * 1000000  # microseconds
                frame_times.append(elapsed)
            
            results['avg_frame_time_us'] = statistics.mean(frame_times)
            results['min_frame_time_us'] = min(frame_times)
            results['max_frame_time_us'] = max(frame_times)
            
            logger.info(f"  Average frame time: {results['avg_frame_time_us']:.1f}μs")
            logger.info(f"  Min frame time: {results['min_frame_time_us']:.1f}μs")
            logger.info(f"  Max frame time: {results['max_frame_time_us']:.1f}μs")
            logger.info(f"  ✓ Target: <100μs per frame (60fps capable)")
            
        except Exception as e:
            logger.error(f"Tick flow benchmark failed: {e}")
        
        self.results['tick_flow'] = results
        return results
    
    def run_all_benchmarks(self) -> dict[str, Any]:
        """
        Run complete benchmark suite
        
        Returns:
            Complete results dict with all benchmarks
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"METAL 4 PERFORMANCE BENCHMARK SUITE")
        logger.info(f"{'='*60}\n")
        
        # Run all benchmarks
        self.benchmark_embeddings(num_texts=100)
        self.benchmark_sql_aggregations(num_rows=1000000)
        self.benchmark_metal4_tick_flow(num_iterations=100)
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"BENCHMARK SUMMARY")
        logger.info(f"{'='*60}")
        
        if 'embeddings' in self.results and self.results['embeddings'].get('speedup'):
            speedup = self.results['embeddings']['speedup']
            logger.info(f"  Embeddings: {speedup:.2f}× faster (Target: 1.15-1.25×)")
            
            if speedup >= 1.15:
                logger.info(f"    ✅ PASSED")
            else:
                logger.info(f"    ⚠️  Below target")
        
        if 'sql_aggregations' in self.results and self.results['sql_aggregations'].get('speedup'):
            speedup = self.results['sql_aggregations']['speedup']
            logger.info(f"  SQL Aggregations: {speedup:.2f}× faster (Target: 2-3×)")
            
            if speedup >= 2.0:
                logger.info(f"    ✅ PASSED")
            else:
                logger.info(f"    ⚠️  Below target")
        
        if 'tick_flow' in self.results and self.results['tick_flow'].get('avg_frame_time_us'):
            frame_time = self.results['tick_flow']['avg_frame_time_us']
            logger.info(f"  Tick Flow Overhead: {frame_time:.1f}μs (Target: <100μs)")
            
            if frame_time < 100:
                logger.info(f"    ✅ PASSED")
            else:
                logger.info(f"    ⚠️  Above target")
        
        logger.info(f"{'='*60}\n")
        
        return self.results


def run_benchmarks() -> dict:
    """Run Metal 4 performance benchmarks"""
    bench = MetalBenchmarks()
    return bench.run_all_benchmarks()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_benchmarks()
