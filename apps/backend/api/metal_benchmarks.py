"""Backward Compatibility Shim - use api.ml.metal instead."""

from api.ml.metal.benchmarks import MetalBenchmarks, run_benchmarks

__all__ = ["MetalBenchmarks", "run_benchmarks"]
