#!/usr/bin/env python3
"""
AiderEngine: uses aider CLI to propose changes but never writes files.
Returns a ChangeProposal (UCPF) containing a unified diff.
"""

import os
import subprocess
from pathlib import Path
from typing import List

from ..patchbus import ChangeProposal

# Stub for tooling_integrations
def build_context_block(snippets) -> str:
    """Build context block from snippets"""
    if not snippets:
        return ""
    return "\n".join(f"# Context: {s}" for s in snippets)


class AiderEngine:
    def __init__(self, model: str, venv_path: Path, repo_root: Path = None):
        self.model = model
        self.venv_path = venv_path
        self.repo_root = repo_root or Path.cwd()

    def propose(self, description: str, files: List[str], context_snippets: List[str]) -> ChangeProposal:
        # Build a prompt that asks for unified diff without applying changes
        preamble = "\n\n[Instructions]\nPropose a unified diff for the requested change.\n"
        preamble += "Output ONLY the diff. Do NOT explain. Do NOT apply changes.\n"
        preamble += "Use paths relative to repo root.\n"
        context_block = build_context_block(context_snippets) if context_snippets else ""
        full_msg = preamble + context_block + "\n[Change]\n" + description

        # SECURITY FIX: Use direct subprocess without shell=True to avoid injection
        # Construct aider command directly with proper arguments
        aider_bin = self.venv_path / "bin" / "aider"

        # Fallback to PATH if aider not in venv
        import shutil
        if not aider_bin.exists():
            aider_path = shutil.which("aider")
            if aider_path:
                aider_bin = Path(aider_path)
            else:
                # Return empty proposal with clear error
                return ChangeProposal(
                    description=description,
                    diff="",
                    affected_files=[],
                    confidence=0.0,
                    rationale="Aider not found. Install via: pip install aider-chat"
                )

        # Handle model format - don't double-prefix with ollama/
        model_str = self.model if self.model.startswith('ollama/') else f'ollama/{self.model}'

        cmd = [
            str(aider_bin),
            "--yes",
            "--no-auto-commits",
            "--no-git",
            f"--model={model_str}",
            "--no-show-model-warnings",  # Suppress model warning pages
            f"--message={full_msg}"
        ]

        # Add file arguments if provided
        if files:
            cmd.extend(files)

        # Set environment variables
        env = os.environ.copy()
        env['AIDER_NO_BROWSER'] = '1'
        env['NO_COLOR'] = '1'
        env['AIDER_NO_SHOW_MODEL_WARNINGS'] = '1'

        try:
            p = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.repo_root),
                env=env
            )
            out = p.stdout + p.stderr
        except Exception as e:
            out = str(e)

        # Extract unified diff heuristically
        diff = self._extract_diff(out)
        return ChangeProposal(description=description, diff=diff or "", affected_files=[], confidence=0.6)

    def _extract_diff(self, text: str) -> str:
        # Try to grab unified diff chunks starting with ---/+++ or diff --git
        lines = text.splitlines()
        start_idx = None
        for i, ln in enumerate(lines):
            if ln.startswith('diff --git') or ln.startswith('--- '):
                start_idx = i
                break
        if start_idx is None:
            return ""
        # Return from first diff header to end
        return "\n".join(lines[start_idx:]) + "\n"
