"""
Column Selection and Manipulation Utilities

Helpers for selecting, filtering, and transforming column names in flattened DataFrames.
"""
from typing import List, Optional
import re
import pandas as pd


def strip_indices(name: str) -> str:
    """
    Remove array index tokens like [0] from a column path.

    Args:
        name: Column name with potential indices

    Returns:
        Column name with indices removed
    """
    return re.sub(r"\[\d+\]", "", name)


def select_columns(df: pd.DataFrame,
                   patterns: Optional[List[str]],
                   preserve_indices: bool = False) -> List[str]:
    """
    Select columns from df using patterns with index-aware matching.

    Rules:
    - Supports exact names and simple prefix wildcard with trailing '*'.
    - If preserve_indices=True, patterns without indices (e.g., users.name)
      match columns that have indices (e.g., users[0].name). Matching is
      performed against an index-stripped view of column names and then
      mapped back to actual columns in original order.
    - Also accepts patterns containing explicit indices or [*]/[] which are
      treated as index-agnostic and match any numeric index.

    Args:
        df: DataFrame with columns to select from
        patterns: List of column patterns (with optional wildcards)
        preserve_indices: Whether to match columns ignoring array indices

    Returns:
        List of selected column names from df
    """
    if not patterns:
        return list(df.columns)

    cols = list(df.columns)
    deindexed = [strip_indices(c) for c in cols]

    selected: List[str] = []
    for pattern in patterns:
        # Normalize wildcard prefix patterns X*
        if pattern.endswith('*'):
            prefix = pattern[:-1]
            if preserve_indices:
                for c, d in zip(cols, deindexed):
                    if d.startswith(prefix):
                        selected.append(c)
            else:
                selected.extend([c for c in cols if c.startswith(prefix)])
            continue

        # Handle explicit [*] or [] in pattern as index-agnostic
        pat = pattern.replace('[*]', '').replace('[]', '')

        if preserve_indices:
            if pattern in cols:
                selected.append(pattern)
                continue
            for c, d in zip(cols, deindexed):
                if d == pat:
                    selected.append(c)
        else:
            if pattern in cols:
                selected.append(pattern)

    # Deduplicate while preserving order
    seen = set()
    return [c for c in selected if not (c in seen or seen.add(c))]


def adapt_patterns_for_array(patterns: List[str], array_path: Optional[str]) -> List[str]:
    """
    Expand patterns to also include variants relative to the array path.

    If a pattern starts with the array_path prefix, also include a version
    with that prefix removed so it can match columns flattened relative to
    the array root.

    Args:
        patterns: Original column patterns
        array_path: Array path prefix to adapt for (e.g., "users")

    Returns:
        Expanded list of patterns
    """
    if not array_path or array_path == '(root)':
        return patterns
    out: List[str] = []
    prefix = f"{array_path}."
    for p in patterns:
        out.append(p)
        if p.startswith(prefix):
            out.append(p[len(prefix):])
    # Deduplicate while preserving order
    seen = set()
    return [p for p in out if not (p in seen or seen.add(p))]


def sanitize_sheet_name(name: str) -> str:
    """
    Sanitize sheet name for Excel compatibility.

    Excel sheet names have restrictions:
    - Max 31 characters
    - Cannot contain: [ ] : * ? / \\
    - Cannot start or end with apostrophe

    Args:
        name: Raw sheet name

    Returns:
        Sanitized sheet name safe for Excel
    """
    # Remove invalid characters
    name = re.sub(r'[\[\]:*?/\\]', '_', name)
    # Remove leading/trailing apostrophes
    name = name.strip("'")
    # Truncate to 31 characters
    if len(name) > 31:
        name = name[:31]
    # Ensure not empty
    if not name:
        name = "Sheet1"
    return name
