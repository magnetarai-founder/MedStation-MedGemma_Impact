"""Backward Compatibility Shim - use api.ml.mlx instead."""

from api.ml.mlx.distributed import (
    MLXDistributed,
    get_mlx_distributed,
    ComputeNode,
    DistributedJob,
)

__all__ = ["MLXDistributed", "get_mlx_distributed", "ComputeNode", "DistributedJob"]
