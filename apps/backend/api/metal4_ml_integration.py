"""Backward Compatibility Shim - use api.ml.metal4 instead."""

from api.ml.metal4.ml_integration import Metal4MLPipeline, get_ml_pipeline, validate_ml_pipeline

__all__ = ["Metal4MLPipeline", "get_ml_pipeline", "validate_ml_pipeline"]
