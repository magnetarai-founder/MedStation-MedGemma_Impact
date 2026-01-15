"""Backward Compatibility Shim - use api.ml.metal4 instead."""

from api.ml.metal4.resources import Metal4ResourceManager, get_resource_manager, BufferType

__all__ = ["Metal4ResourceManager", "get_resource_manager", "BufferType"]
