"""
Code Editor Filesystem Diff Operations
Generate unified diffs for file operations
"""

import difflib


def generate_unified_diff(original: str, modified: str, filepath: str) -> str:
    """
    Generate unified diff (Continue's streamDiff pattern)
    """
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
        lineterm=''
    )

    return ''.join(diff)
