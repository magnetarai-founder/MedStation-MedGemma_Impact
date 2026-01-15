"""Backward Compatibility Shim - use api.ml.metal instead."""

from api.ml.metal.embedder import MetalEmbedder, get_metal_embedder

__all__ = ["MetalEmbedder", "get_metal_embedder"]
