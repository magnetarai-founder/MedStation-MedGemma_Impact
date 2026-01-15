"""
Legacy Metal Performance Shaders integration.

Note: For Metal 4 features, use api.ml.metal4 instead.

Provides:
- MetalBenchmarks: GPU benchmark suite
- MetalEmbedder: Metal-accelerated embeddings
- MetalSQLKernels: SQL acceleration kernels
"""

from api.ml.metal.benchmarks import MetalBenchmarks, run_benchmarks
from api.ml.metal.embedder import MetalEmbedder, get_metal_embedder
from api.ml.metal.sql_kernels import MetalSQLKernels, get_metal_sql_kernels

__all__ = [
    "MetalBenchmarks",
    "run_benchmarks",
    "MetalEmbedder",
    "get_metal_embedder",
    "MetalSQLKernels",
    "get_metal_sql_kernels",
]
