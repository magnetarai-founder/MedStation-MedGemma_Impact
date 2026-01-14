"""
Redshift SQL Processor Utilities

Pure utility functions for SQL processing.
"""

import re
from typing import Optional

from neutron_utils.sql_utils import ColumnNameCleaner


def clean_identifier(name: str) -> str:
    """Clean identifiers consistently using shared cleaner (preserve case)."""
    return ColumnNameCleaner.clean_sql_identifier(name, preserve_case=True)


def normalize_casts_text(text: str) -> str:
    """Collapse nested CAST-to-VARCHAR patterns conservatively.

    Handles forms like:
      CAST(CAST(x) AS VARCHAR) AS VARCHAR   -> CAST(x AS VARCHAR)
      CAST(TRY_CAST(x AS VARCHAR)) AS VARCHAR -> CAST(x AS VARCHAR)

    Uses a limited-depth matcher that tolerates simple nested parens
    (e.g., function calls) without greedy overreach. Runs a few passes
    until stable.
    """
    # Inner expression: allow balanced one-level parentheses
    inner = r"((?:[^()]|\([^()]*\))+?)"
    pat_nested = re.compile(rf"(?is)\bCAST\s*\(\s*CAST\s*\(\s*{inner}\s*\)\s*AS\s+VARCHAR\s*\)\s*AS\s+VARCHAR")
    pat_try_nested = re.compile(
        rf"(?is)\bCAST\s*\(\s*TRY_CAST\s*\(\s*{inner}\s*AS\s+VARCHAR\s*\)\s*\)\s*AS\s+VARCHAR"
    )
    for _ in range(4):
        prev = text
        text = pat_nested.sub(r"CAST(\1 AS VARCHAR)", text)
        text = pat_try_nested.sub(r"CAST(\1 AS VARCHAR)", text)
        if text == prev:
            break
    return text


def is_literal(text: str) -> bool:
    """Check if text is a SQL literal (string or dollar-quoted)."""
    t = text.strip()
    return t.startswith("'") or t.startswith("$$")


def already_cast(text: str) -> bool:
    """Check if text is already wrapped in CAST or TRY_CAST."""
    return re.match(r"(?is)^\s*\(*\s*(?:TRY_)?CAST\s*\(", text or "") is not None


def scan_left_boundary(expr: str, pos: int) -> int:
    """Scan left from pos to find start of the LHS expression at top level.

    Handles nested parentheses and quoted strings correctly.
    """
    i = pos - 1
    depth = 0
    in_s = False
    in_d = False
    while i >= 0:
        ch = expr[i]
        if in_s:
            if ch == "'" and not (i > 0 and expr[i - 1] == "'"):
                in_s = False
            i -= 1
            continue
        if in_d:
            if ch == '"' and not (i > 0 and expr[i - 1] == '"'):
                in_d = False
            i -= 1
            continue
        if ch == "'":
            in_s = True
            i -= 1
            continue
        if ch == '"':
            in_d = True
            i -= 1
            continue
        if ch == ")":
            depth += 1
            i -= 1
            continue
        if ch == "(" and depth > 0:
            depth -= 1
            i -= 1
            continue
        if depth == 0:
            # Check for top-level AND/OR separators
            low = expr[: i + 1].lower()
            if low.endswith(" and") or low.endswith(" or"):
                return i + 1
        i -= 1
    return 0


def scan_right_boundary(expr: str, pos: int) -> int:
    """Scan right from pos to find end of RHS expression at top level.

    Handles nested parentheses and quoted strings correctly.
    """
    i = pos
    n = len(expr)
    depth = 0
    in_s = False
    in_d = False
    while i < n:
        ch = expr[i]
        if in_s:
            if ch == "'" and not (i + 1 < n and expr[i + 1] == "'"):
                in_s = False
            i += 1
            continue
        if in_d:
            if ch == '"' and not (i + 1 < n and expr[i + 1] == '"'):
                in_d = False
            i += 1
            continue
        if ch == "'":
            in_s = True
            i += 1
            continue
        if ch == '"':
            in_d = True
            i += 1
            continue
        if ch == "(":
            depth += 1
            i += 1
            continue
        if ch == ")" and depth > 0:
            depth -= 1
            i += 1
            continue
        if depth == 0:
            low = expr[i:].lower()
            if low.startswith(" and ") or low.startswith(" or "):
                return i
        i += 1
    return n


def apply_column_mapping_to_sql(sql: str, mapping: dict) -> str:
    """Apply column name mapping to SQL query.

    Replaces original column names with their cleaned versions.
    """
    result = sql
    for orig, clean in mapping.items():
        # Use word boundaries to avoid partial replacements
        pattern = rf'\b{re.escape(orig)}\b'
        result = re.sub(pattern, clean, result, flags=re.IGNORECASE)
    return result


def escape_sheet_name(name: str) -> str:
    """Escape single quotes in sheet name for DuckDB st_read layer parameter."""
    if not name:
        return name
    # Escape single quotes by doubling them
    return name.replace("'", "''")
