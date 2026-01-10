"""
Codex Search Utilities - Code search and pattern matching

Provides:
- Regex-based code search using ripgrep or Python fallback
- Code search across file globs

Extracted from codex_engine.py during P2 decomposition.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional


def search_code(
    pattern: str,
    repo_root: Path,
    globs: Optional[List[str]] = None,
    max_results: int = 200
) -> List[Tuple[str, int, str]]:
    """
    Search code for a regex pattern.

    Uses ripgrep (rg) if available for performance, falls back to Python.

    Args:
        pattern: Regex pattern to search for
        repo_root: Root directory to search in
        globs: File globs to search (default: ['**/*.py', '**/*.js', '**/*.ts'])
        max_results: Maximum number of results to return

    Returns:
        List of (relative_path, line_number, line_content) tuples
    """
    globs = globs or ['**/*.py', '**/*.js', '**/*.ts']
    results = []

    # Try ripgrep first (faster)
    if shutil.which('rg'):
        results = _search_with_ripgrep(pattern, repo_root, globs, max_results)
        if results:
            return results[:max_results]

    # Fallback: Python implementation
    return _search_with_python(pattern, repo_root, globs, max_results)


def _search_with_ripgrep(
    pattern: str,
    repo_root: Path,
    globs: List[str],
    max_results: int
) -> List[Tuple[str, int, str]]:
    """
    Search using ripgrep (rg) command.

    Args:
        pattern: Regex pattern
        repo_root: Search root
        globs: File globs
        max_results: Max results

    Returns:
        List of (path, line_no, content) tuples
    """
    results = []

    # Convert glob patterns to ripgrep glob syntax
    rg_globs = []
    for g in globs:
        if g.startswith('**/'):
            # **/*.py -> -g '*.py'
            rg_globs.extend(['-g', g[3:]])
        else:
            # *.py -> -g '*.py'
            rg_globs.extend(['-g', g])

    cmd = ['rg', '-n', '--no-heading', '-e', pattern] + rg_globs

    try:
        p = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        if p.returncode in (0, 1):  # 1 = no matches
            for line in p.stdout.strip().splitlines():
                if not line:
                    continue
                try:
                    path, lno, content = line.split(':', 2)
                    results.append((path, int(lno), content))
                except ValueError:
                    continue
                if len(results) >= max_results:
                    return results[:max_results]
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass  # Fall through to Python implementation

    return results


def _search_with_python(
    pattern: str,
    repo_root: Path,
    globs: List[str],
    max_results: int
) -> List[Tuple[str, int, str]]:
    """
    Search using pure Python (fallback).

    Args:
        pattern: Regex pattern
        repo_root: Search root
        globs: File globs
        max_results: Max results

    Returns:
        List of (path, line_no, content) tuples
    """
    results = []
    rx = re.compile(pattern)

    for g in globs:
        # Handle **/ prefix
        glob_pattern = g.replace('**/', '') if g.startswith('**/') else g

        for p in repo_root.rglob(glob_pattern):
            if not p.is_file():
                continue
            try:
                text = p.read_text(errors='ignore')
            except Exception:
                continue

            for idx, ln in enumerate(text.splitlines(), 1):
                if rx.search(ln):
                    rel_path = str(p.relative_to(repo_root))
                    results.append((rel_path, idx, ln))
                    if len(results) >= max_results:
                        return results

    return results


__all__ = [
    "search_code",
]
