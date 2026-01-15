"""Backward Compatibility Shim - use api.ml.metal4 instead."""

from api.ml.metal4.metalfx_renderer import Metal4MetalFXRenderer, get_metalfx_renderer, validate_metalfx_renderer, FrameMetrics

__all__ = ["Metal4MetalFXRenderer", "get_metalfx_renderer", "validate_metalfx_renderer", "FrameMetrics"]
