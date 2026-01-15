"""Backward Compatibility Shim - use api.ml.metal instead."""

from api.ml.metal.sql_kernels import MetalSQLKernels, get_metal_sql_kernels

__all__ = ["MetalSQLKernels", "get_metal_sql_kernels"]
