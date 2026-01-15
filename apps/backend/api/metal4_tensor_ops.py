"""Backward Compatibility Shim - use api.ml.metal4 instead."""

from api.ml.metal4.tensor_ops import Metal4TensorOps, get_tensor_ops, validate_tensor_ops

__all__ = ["Metal4TensorOps", "get_tensor_ops", "validate_tensor_ops"]
