"""Backward Compatibility Shim - use api.ml.metal4 instead."""

from api.ml.metal4.benchmarks import (
    Metal4Benchmarks,
    BenchmarkResult,
    run_benchmarks,
    logger,
)

__all__ = ["Metal4Benchmarks", "BenchmarkResult", "run_benchmarks", "logger"]
