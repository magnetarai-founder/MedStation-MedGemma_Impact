"""
Workflow Orchestrator Engine - Compatibility Shim

BACKWARDS COMPATIBILITY LAYER
This module maintains backwards compatibility for existing imports.

The WorkflowOrchestrator class implementation has been moved to
api/services/workflow_orchestrator.py during Phase 6.3e modularization.

This module re-exports WorkflowOrchestrator for backwards compatibility.

All existing imports like:
    from api.workflow_orchestrator import WorkflowOrchestrator
    from workflow_orchestrator import WorkflowOrchestrator

will continue to work unchanged.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from api.services.workflow_orchestrator import WorkflowOrchestrator
except ImportError:
    from services.workflow_orchestrator import WorkflowOrchestrator

__all__ = ["WorkflowOrchestrator"]
