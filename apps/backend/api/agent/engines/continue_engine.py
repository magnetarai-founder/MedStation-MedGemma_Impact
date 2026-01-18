#!/usr/bin/env python3
"""
ContinueEngine: uses Continue CLI (cn) in headless mode to propose a unified diff.
Never writes files directly; returns ChangeProposal for PatchBus.
"""

import shutil
import subprocess
from typing import List

from ..patchbus import ChangeProposal


# Stub for tooling_integrations
def build_context_block(snippets) -> str:
    """Build context block from snippets"""
    if not snippets:
        return ""
    return "\n".join(f"# Context: {s}" for s in snippets)


class ContinueEngine:
    def __init__(self, binary: str = None):
        self.cn = binary or shutil.which("cn") or shutil.which("continue")

    def propose(self, description: str, files: List[str], context_snippets: List[str]) -> ChangeProposal:
        if not self.cn:
            return ChangeProposal(description=description, diff="", affected_files=[], confidence=0.0)

        ctx = build_context_block(context_snippets) if context_snippets else ""
        prompt = (
            "Propose a unified diff for the following change. Output ONLY the diff, no prose.\n"
            "Paths should be relative to repo root.\n\n"
            f"{ctx}"
            f"Change: {description}\n"
        )

        # Build command with files, send prompt via stdin to avoid argv length limits
        cmd = [self.cn]
        if files:
            cmd.extend(files)

        try:
            p = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=600
            )
            out = p.stdout
        except Exception as e:
            out = str(e)

        diff = self._extract_diff(out)
        return ChangeProposal(description=description, diff=diff or "", affected_files=[], confidence=0.6)

    def _extract_diff(self, text: str) -> str:
        lines = text.splitlines()
        start_idx = None
        for i, ln in enumerate(lines):
            if ln.startswith('diff --git') or ln.startswith('--- '):
                start_idx = i
                break
        if start_idx is None:
            return ""
        return "\n".join(lines[start_idx:]) + "\n"
