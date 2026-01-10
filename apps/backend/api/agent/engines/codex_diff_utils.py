"""
Codex Diff Utilities - Pure functions for diff parsing and manipulation

Provides:
- Patch level detection (-p0 vs -p1)
- Path validation (security checks for traversal attacks)
- Diff reversal for rollback
- Target extraction from diff headers
- Multi-file diff splitting
- Unified diff generation

Extracted from codex_engine.py during P2 decomposition.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import List, Tuple


# ===== Patch Level Detection =====

def detect_patch_level(diff: str) -> int:
    """
    Detect whether diff uses -p0 or -p1 format by checking path prefixes.

    Args:
        diff: Unified diff text

    Returns:
        0 for -p0 (no prefix), 1 for -p1 (a/ b/ prefix)
    """
    for ln in diff.splitlines():
        if ln.startswith('--- ') or ln.startswith('+++ '):
            path = ln.split(' ', 1)[1].strip()
            if '\t' in path:
                path = path.split('\t', 1)[0]

            # Check for a/ or b/ prefix (git format)
            if path.startswith('a/') or path.startswith('b/'):
                return 1

            # If no prefix and not /dev/null, assume -p0
            if path != '/dev/null':
                return 0

    # Default to -p1 for git-style diffs
    return 1


# ===== Path Validation (Security) =====

def validate_diff_paths(diff: str, repo_root: Path) -> Tuple[bool, str]:
    """
    Validate diff paths to prevent path traversal attacks.

    Security checks:
    - Rejects absolute paths (starting with /)
    - Rejects parent directory traversal (../)
    - Rejects paths outside repo_root after resolution
    - Allows /dev/null (standard for new/deleted files)

    Args:
        diff: Unified diff text
        repo_root: Repository root path for containment check

    Returns:
        (is_safe, error_message) tuple
    """
    for ln in diff.splitlines():
        if not (ln.startswith('--- ') or ln.startswith('+++ ')):
            continue

        # Extract path from diff header
        path = ln.split(' ', 1)[1].strip()
        if '\t' in path:
            path = path.split('\t', 1)[0]

        # Strip a/ b/ prefixes if present
        if path.startswith('a/') or path.startswith('b/'):
            path = path[2:]

        # Allow /dev/null (standard for new/deleted files)
        if path == '/dev/null':
            continue

        # REJECT: Absolute paths
        if path.startswith('/'):
            return False, f"Absolute path not allowed: {path}"

        # REJECT: Parent directory traversal
        if '../' in path or path.startswith('..'):
            return False, f"Path traversal not allowed: {path}"

        # REJECT: Paths that resolve outside repo_root
        try:
            resolved = (repo_root / path).resolve()
            if not resolved.is_relative_to(repo_root.resolve()):
                return False, f"Path escapes repo root: {path}"
        except (ValueError, RuntimeError):
            return False, f"Invalid path: {path}"

    return True, ""


# ===== Diff Reversal =====

def reverse_unified_diff(diff: str) -> str:
    """
    Reverse a unified diff for rollback.

    Swaps:
    - --- and +++ headers
    - + and - line prefixes

    Args:
        diff: Original unified diff

    Returns:
        Reversed diff text
    """
    lines = []
    for ln in diff.splitlines():
        if ln.startswith('--- '):
            lines.append('+++ ' + ln[4:])
        elif ln.startswith('+++ '):
            lines.append('--- ' + ln[4:])
        elif ln.startswith('+') and not ln.startswith('+++'):
            lines.append('-' + ln[1:])
        elif ln.startswith('-') and not ln.startswith('---'):
            lines.append('+' + ln[1:])
        else:
            lines.append(ln)
    return "\n".join(lines) + "\n"


# ===== Target Extraction =====

def extract_targets(diff: str) -> List[str]:
    """
    Extract unique file paths from diff headers.

    Handles:
    - Timestamps in headers (tab-separated)
    - a/ and b/ prefixes

    Args:
        diff: Unified diff text

    Returns:
        List of unique relative file paths
    """
    targets = []
    for ln in diff.splitlines():
        if ln.startswith('+++ '):
            f = ln.split(' ', 1)[1].strip()
            # Strip timestamp if present
            if '\t' in f:
                f = f.split('\t', 1)[0]
            if f.startswith('b/'):
                f = f[2:]
            targets.append(f)
        elif ln.startswith('--- '):
            f = ln.split(' ', 1)[1].strip()
            if '\t' in f:
                f = f.split('\t', 1)[0]
            if f.startswith('a/'):
                f = f[2:]
            targets.append(f)

    # Return unique paths preserving order
    seen = set()
    unique = []
    for t in targets:
        if t not in seen:
            unique.append(t)
            seen.add(t)
    return unique


# ===== Diff Splitting =====

def split_unified_diff(diff: str) -> List[str]:
    """
    Split a multi-file unified diff into a list of per-file diffs.

    Splits on 'diff --git' or '--- ' headers.

    Args:
        diff: Multi-file unified diff

    Returns:
        List of single-file diffs
    """
    files = []
    current = []
    for ln in diff.splitlines():
        if ln.startswith('diff --git') or ln.startswith('--- '):
            if current:
                files.append('\n'.join(current) + '\n')
                current = []
        current.append(ln)
    if current:
        files.append('\n'.join(current) + '\n')

    # Filter out empty shards (must have both --- and +++ headers)
    return [d for d in files if '--- ' in d and '+++ ' in d]


# ===== Diff Generation =====

def unified_text_diff(old_path: str, new_path: str, before: str, after: str) -> str:
    """
    Generate a unified diff between two text contents.

    Adds timestamps to guard against spaces in filenames.

    Args:
        old_path: Original file path (or '/dev/null' for new files)
        new_path: New file path (or '/dev/null' for deleted files)
        before: Original content
        after: New content

    Returns:
        Unified diff string
    """
    a = before.splitlines(keepends=True)
    b = after.splitlines(keepends=True)

    # Add tab and timestamp to guard spaces in filenames
    ts = '\t1970-01-01 00:00:00 +0000'
    fromfile = old_path if old_path == '/dev/null' else f"{old_path}{ts}"
    tofile = new_path if new_path == '/dev/null' else f"{new_path}{ts}"

    ud = difflib.unified_diff(a, b, fromfile=fromfile, tofile=tofile)
    return ''.join(ud)


def unified_add_file(new_path: str, content: str) -> str:
    """
    Generate a unified diff for adding a new file.

    Args:
        new_path: Path for the new file
        content: Content of the new file

    Returns:
        Unified diff with --- /dev/null header
    """
    return unified_text_diff('/dev/null', new_path, '', content)


def unified_delete_file(old_path: str, content: str) -> str:
    """
    Generate a unified diff for deleting a file.

    Args:
        old_path: Path of the file to delete
        content: Current content of the file

    Returns:
        Unified diff with +++ /dev/null header
    """
    return unified_text_diff(old_path, '/dev/null', content, '')


__all__ = [
    # Patch level
    "detect_patch_level",
    # Security
    "validate_diff_paths",
    # Reversal
    "reverse_unified_diff",
    # Extraction
    "extract_targets",
    "split_unified_diff",
    # Generation
    "unified_text_diff",
    "unified_add_file",
    "unified_delete_file",
]
