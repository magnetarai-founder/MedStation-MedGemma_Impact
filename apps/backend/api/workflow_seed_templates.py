"""Backward Compatibility Shim - use api.workflows.seed_templates instead."""

from api.workflows.seed_templates import (
    seed_global_workflow_templates,
    logger,
)

__all__ = [
    "seed_global_workflow_templates",
    "logger",
]
