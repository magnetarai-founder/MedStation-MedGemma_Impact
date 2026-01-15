"""Backward Compatibility Shim - use api.ml.metal4 instead."""

from api.ml.metal4.mps_embedder import Metal4MPSEmbedder, get_metal4_mps_embedder, validate_metal4_mps_setup

__all__ = ["Metal4MPSEmbedder", "get_metal4_mps_embedder", "validate_metal4_mps_setup"]
