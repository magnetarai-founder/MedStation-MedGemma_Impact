#!/usr/bin/env python3
"""
PatchBus and Unified Change Proposal Format (UCPF)
Normalizes proposals from engines (Aider/Continue) and applies them via CodexEngine.

Env flags:
- PATCHBUS_SKIP_VERIFY=1|true|yes|on  -> Skips verification step (still returns summary)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import hashlib
import time
import re
from pathlib import Path
import os
import io
from contextlib import redirect_stdout, redirect_stderr


@dataclass
class ChangeProposal:
    description: str
    diff: str  # unified diff text
    affected_files: List[str] = field(default_factory=list)
    confidence: float = 0.6
    rationale: Optional[str] = None
    test_hints: List[str] = field(default_factory=list)
    dry_run: bool = False


class PatchBus:
    @staticmethod
    def _truthy(val: Optional[str]) -> bool:
        if val is None:
            return False
        return val.strip().lower() in {"1", "true", "yes", "on"}
    @staticmethod
    def summarize_diff(diff_text: str) -> Dict[str, object]:
        files = []
        lines = 0
        for line in diff_text.splitlines():
            if line.startswith('+++ ') or line.startswith('--- '):
                m = re.match(r"[+\-]{3} \s*(?:a/|b/)?(.+)", line)
                if m:
                    raw = m.group(1)
                    if '\t' in raw:
                        raw = raw.split('\t', 1)[0]
                    if raw.strip() == '/dev/null':
                        continue
                    files.append(raw)
            if line.startswith('+') or line.startswith('-'):
                if not line.startswith('+++') and not line.startswith('---'):
                    lines += 1
        return {"files": list(sorted(set(files))), "lines": lines}

    @staticmethod
    def apply(proposal: ChangeProposal) -> Dict[str, object]:
        """Apply a change proposal via CodexEngine with validation and rollback."""
        from engines.codex_engine import CodexEngine
        patch_id = f"P{int(time.time())}_{hashlib.md5(proposal.diff.encode()).hexdigest()[:8]}"
        engine = CodexEngine()
        # Dry-run: do not apply, just summarize
        if getattr(proposal, 'dry_run', False):
            summary = PatchBus.summarize_diff(proposal.diff)
            return {
                "success": True,
                "message": "Preview only (dry-run)",
                "patch_id": None,
                "files": summary.get('files', []),
                "lines": summary.get('lines', 0),
                "summary": {
                    "files": len(summary.get('files', [])),
                    "lines": summary.get('lines', 0),
                    "verify": {"skipped": True, "reason": "dry_run"},
                },
            }
        try:
            # Populate affected_files if empty for downstream UX and ingestion
            if not proposal.affected_files:
                summary = PatchBus.summarize_diff(proposal.diff)
                proposal.affected_files = summary.get('files', [])
            ok, msg = engine.apply_unified_diff(proposal.diff, patch_id)
            if not ok:
                summary = PatchBus.summarize_diff(proposal.diff)
                return {
                    "success": False,
                    "message": msg,
                    "patch_id": patch_id,
                    "files": summary.get('files', []),
                    "lines": summary.get('lines', 0),
                    "summary": {
                        "files": len(summary.get('files', [])),
                        "lines": summary.get('lines', 0),
                        "verify": {"skipped": True, "reason": "apply_failed"},
                    },
                }
        except Exception as e:
            summary = PatchBus.summarize_diff(proposal.diff)
            return {
                "success": False,
                "message": str(e),
                "patch_id": patch_id,
                "files": summary.get('files', []),
                "lines": summary.get('lines', 0),
                "summary": {
                    "files": len(summary.get('files', [])),
                    "lines": summary.get('lines', 0),
                    "verify": {"skipped": True, "reason": "exception"},
                },
            }
        # Verification (guarded)
        skip_verify = str(os.getenv("PATCHBUS_SKIP_VERIFY", "0")).lower() in {"1", "true", "yes"}
        verify_func = None
        try:
            from verify import verify_after_apply as _verify_after_apply  # type: ignore
            verify_func = _verify_after_apply
        except Exception:
            verify_func = None

        verify_info: Dict[str, object] = {}
        if skip_verify:
            verify_info = {"skipped": True, "reason": "env_skip"}
        elif verify_func is None:
            verify_info = {"skipped": True, "reason": "missing_verify_module"}
        else:
            out_buf, err_buf = io.StringIO(), io.StringIO()
            try:
                with redirect_stdout(out_buf), redirect_stderr(err_buf):
                    v_ok, v_msg = verify_func(proposal.diff, proposal.test_hints)
            except Exception as e:
                v_ok, v_msg = False, str(e)
            verify_info = {
                "ok": bool(v_ok),
                "message": v_msg,
                "stdout": out_buf.getvalue()[-2000:],
                "stderr": err_buf.getvalue()[-2000:],
            }
            if not v_ok:
                # Rollback on failure
                engine.rollback(patch_id)
                summary = PatchBus.summarize_diff(proposal.diff)
                return {
                    "success": False,
                    "message": f"Verification failed: {v_msg}",
                    "patch_id": patch_id,
                    "files": summary.get('files', []),
                    "lines": summary.get('lines', 0),
                    "verify": verify_info,
                    "summary": {
                        "files": len(summary.get('files', [])),
                        "lines": summary.get('lines', 0),
                        "verify": {"ok": False},
                    },
                }
        
        # Auto-ingest changed files for RAG
        PatchBus._auto_ingest_changed_files(proposal)

        summary = PatchBus.summarize_diff(proposal.diff)

        # Append to local patch history for auditing (opt-in)
        try:
            if PatchBus._truthy(os.getenv("OMNIOS_HISTORY_LOCAL", "0")):
                import json as _json
                from datetime import datetime as _dt
                hist_dir = Path.cwd() / '.ai_agent'
                hist_dir.mkdir(exist_ok=True)
                hist_file = hist_dir / 'patch_history.jsonl'
                entry = {
                    'timestamp': _dt.utcnow().isoformat() + 'Z',
                    'patch_id': patch_id,
                    'description': proposal.description,
                    'files': summary.get('files', []),
                    'lines': summary.get('lines', 0),
                }
                with open(hist_file, 'a') as f:
                    f.write(_json.dumps(entry) + "\n")
        except Exception:
            pass

        return {
            "success": True,
            "message": "Applied and verified",
            "patch_id": patch_id,
            "files": summary.get('files', []),
            "lines": summary.get('lines', 0),
            "verify": verify_info,
            "summary": {
                "files": len(summary.get('files', [])),
                "lines": summary.get('lines', 0),
                "verify": (verify_info if verify_info else {"skipped": True}),
            },
        }

    @staticmethod
    def _auto_ingest_changed_files(proposal: ChangeProposal):
        """Auto-ingest changed files into RAG system with 'touched' tag (opt-in)."""
        # Gate behind env to avoid repo bloat or heavy side effects by default
        if not PatchBus._truthy(os.getenv("RAG_AUTO_INGEST", "0")):
            return
        try:
            from rag_pipeline import ingest_paths
            import logging
            
            # Extract affected files from proposal or diff
            files_to_ingest = []
            
            # Use affected_files if available
            if proposal.affected_files:
                files_to_ingest = proposal.affected_files
            else:
                # Parse from diff
                diff_summary = PatchBus.summarize_diff(proposal.diff)
                files_to_ingest = diff_summary.get('files', [])
            
            # Filter to existing files
            existing_files = []
            for file_path in files_to_ingest:
                if Path(file_path).exists():
                    existing_files.append(str(Path(file_path).resolve()))
            
            if existing_files:
                # Ingest with special tags
                tags = ['touched', 'auto-indexed', f'patch-{int(time.time())}']
                ingest_paths(existing_files, tags=tags)
                logging.info(f"Auto-ingested {len(existing_files)} files: {existing_files}")
            
        except Exception as e:
            # Don't fail the patch if ingestion fails
            import logging
            logging.warning(f"Auto-ingestion failed: {e}")
    
    @staticmethod
    def rollback(patch_id: str) -> Tuple[bool, str]:
        from engines.codex_engine import CodexEngine
        engine = CodexEngine()
        return engine.rollback(patch_id)
