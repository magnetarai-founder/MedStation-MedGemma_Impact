#!/usr/bin/env python3
"""
AiderEngine: uses aider CLI to propose changes but never writes files.
Returns a ChangeProposal (UCPF) containing a unified diff.
"""

import subprocess
from pathlib import Path
from typing import List

try:
    from ..patchbus import ChangeProposal
except ImportError:
    from patchbus import ChangeProposal

# Stub for tooling_integrations
def build_context_block(snippets):
    """Build context block from snippets"""
    if not snippets:
        return ""
    return "\n".join(f"# Context: {s}" for s in snippets)


class AiderEngine:
    def __init__(self, model: str, venv_path: Path):
        self.model = model
        self.venv_path = venv_path

    def propose(self, description: str, files: List[str], context_snippets: List[str]) -> ChangeProposal:
        # Build a prompt that asks for unified diff without applying changes
        preamble = "\n\n[Instructions]\nPropose a unified diff for the requested change.\n"
        preamble += "Output ONLY the diff. Do NOT explain. Do NOT apply changes.\n"
        preamble += "Use paths relative to repo root.\n"
        context_block = build_context_block(context_snippets) if context_snippets else ""
        full_msg = preamble + context_block + "\n[Change]\n" + description

        escaped = full_msg.replace("'", "'\"'\"'")
        cmd = [
            "bash",
            "-c",
            f"source {self.venv_path}/bin/activate && export AIDER_NO_BROWSER=1 && export NO_COLOR=1 && "
            f"aider --yes --no-auto-commits --no-git --model ollama/{self.model} --message '{escaped}'"
            + (" " + " ".join(files) if files else "")
        ]

        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
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
