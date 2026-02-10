"""
Agent Orchestration - Plan Application

Plan application via Aider/Continue/Codex engines:
- Engine iteration (tries engines in order until success)
- Patch generation via engines
- Dry run (preview only) vs real application
- PatchBus integration for applying changes
- Unified context integration for persistence
- Workspace session management

Extracted from orchestrator.py during Phase 6.3d modularization.

AUTH-P5: Agent auto-apply operations now audited for security accountability.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from ..patchbus import PatchBus
from .models import ApplyRequest, FilePatch
from .config import get_agent_config
from api.utils import get_user_id

logger = logging.getLogger(__name__)


def apply_plan_logic(
    body: ApplyRequest,
    current_user: Dict
) -> Tuple[List[FilePatch], Optional[str], str]:
    """
    Apply a plan via Aider/Continue/Codex and return patches.

    Tries engines in order (from config) until one succeeds in generating a diff.
    If dry_run=True, returns unified patch without applying.
    If dry_run=False, applies via PatchBus and integrates with unified_context.

    Args:
        body: ApplyRequest with input, repo_root, files, session_id, model, dry_run
        current_user: User dict with user_id

    Returns:
        Tuple of (patches, patch_id, engine_used):
        - patches: List of FilePatch objects
        - patch_id: Patch ID if applied (None for dry_run)
        - engine_used: Name of engine that generated the diff

    Raises:
        Exception if no engine generates a diff
        Exception if patch application fails
    """
    # Get config
    cfg = get_agent_config()
    engines = cfg.get("engine_order", ["aider"])
    coder_model = body.model or cfg["models"]["coder"]

    # Get paths
    project_root = Path(os.getcwd()).parent.parent.parent
    venv_path = project_root / "venv"
    if not venv_path.exists():
        venv_path = Path.home() / ".virtualenvs" / "medstationos"

    repo_root = Path(body.repo_root) if body.repo_root else project_root

    # Get files and context
    files = body.files or []
    context_snippets = []

    # Try engines in order until one succeeds
    proposal = None
    engine_used = None

    for engine_name in engines:
        try:
            logger.info(f"Trying engine: {engine_name}")

            if engine_name == "aider":
                from ..engines.aider_engine import AiderEngine

                engine = AiderEngine(
                    model=coder_model,
                    venv_path=venv_path,
                    repo_root=repo_root
                )
                proposal = engine.propose(body.input, files, context_snippets)

            elif engine_name == "continue":
                from ..engines.continue_engine import ContinueEngine

                engine = ContinueEngine(model=coder_model)
                proposal = engine.propose(body.input, files, context_snippets)

            else:
                logger.warning(f"Unknown engine: {engine_name}")
                continue

            # Check if we got a valid diff
            if proposal and proposal.diff.strip():
                engine_used = engine_name
                logger.info(f"✓ {engine_name} generated diff ({len(proposal.diff)} chars)")
                break
            else:
                logger.warning(f"✗ {engine_name} returned empty diff")

        except Exception as e:
            logger.warning(f"✗ {engine_name} failed: {e}")
            continue

    # If no engine succeeded, fail
    if not proposal or not proposal.diff.strip():
        raise Exception("No engine generated a diff. Check logs for details.")

    # If dry run, just preview the diff
    if body.dry_run:
        patches = [FilePatch(
            path='<unified>',
            patch_text=proposal.diff,
            summary=proposal.description
        )]
        patch_id = None
    else:
        # Apply via PatchBus with repo_root
        apply_result = PatchBus.apply(proposal, repo_root=body.repo_root)

        if not apply_result.get('success'):
            raise Exception(f"Patch application failed: {apply_result.get('message')}")

        patch_id = apply_result.get('patch_id')

        # Convert to patches for response
        patches = [FilePatch(
            path=f,
            patch_text=proposal.diff,
            summary=f"Applied changes to {f}"
        ) for f in apply_result.get('files', [])]

        # AUTH-P5: Audit agent auto-apply operation
        try:
            from api.audit_helper import record_audit_event
            from api.audit_logger import AuditAction

            files_changed = apply_result.get('files', [])
            record_audit_event(
                user_id=current_user.get('user_id', 'system'),
                action=AuditAction.AGENT_AUTO_APPLY,
                resource='repository',
                resource_id=str(repo_root),
                details={
                    'engine': engine_used,
                    'files_changed': len(files_changed),
                    'files': files_changed[:10],  # First 10 files only
                    'patch_id': patch_id,
                    'session_id': body.session_id
                }
            )
        except Exception as audit_err:
            # Log but don't fail the apply operation
            logger.warning(f"Failed to audit agent auto-apply: {audit_err}")

        # Add to unified context for persistence
        try:
            from api.unified_context import get_unified_context
            from api.workspace_session import get_workspace_session_manager

            context_mgr = get_unified_context()
            ws_mgr = get_workspace_session_manager()

            # Get or create workspace session for this repo
            workspace_session_id = body.session_id
            if not workspace_session_id and body.repo_root:
                workspace_session_id = ws_mgr.get_or_create_for_workspace(
                    user_id=get_user_id(current_user),
                    workspace_root=body.repo_root
                )

            if workspace_session_id:
                context_mgr.add_entry(
                    user_id=get_user_id(current_user),
                    session_id=workspace_session_id,
                    source='agent',
                    entry_type='patch',
                    content=proposal.description,
                    metadata={
                        'patch_id': patch_id,
                        'files': apply_result.get('files', []),
                        'lines': apply_result.get('lines', 0),
                        'repo_root': body.repo_root
                    }
                )
            else:
                logger.warning("No session_id or repo_root provided, skipping unified context")
        except Exception as e:
            logger.warning(f"Failed to add patch to unified context: {e}")

        # Phase E: Trigger workflow events for successful agent apply
        try:
            from api.services.workflow_triggers import handle_agent_event
            from api.workflow_storage import WorkflowStorage

            # Build agent event
            agent_event = {
                "type": "agent.apply.success",
                "user_id": get_user_id(current_user),
                "repo_root": body.repo_root or str(repo_root),
                "files": apply_result.get('files', []),
                "patch_id": patch_id,
                "summary": proposal.description,
                "session_id": body.session_id,
                "engine_used": engine_used,
            }

            # Fire workflow triggers
            workflow_storage = WorkflowStorage()
            handle_agent_event(
                event=agent_event,
                storage=workflow_storage,
                user_id=get_user_id(current_user),
            )
            logger.debug(f"🔔 Fired agent event: agent.apply.success")

        except Exception as e:
            # Graceful degradation - don't break apply on workflow trigger errors
            logger.warning(f"Failed to fire agent event for workflow triggers: {e}")

    return (patches, patch_id, engine_used)
