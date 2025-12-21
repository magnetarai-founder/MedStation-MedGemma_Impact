"""
Redshift SQL Processor using DuckDB for full SQL compatibility
Provides robust SQL processing that mimics Redshift/DataCentral behavior
"""

import re
import logging
import pandas as pd
import duckdb
from typing import Optional, List
from difflib import get_close_matches

# Import utilities
from neutron_utils.sql_utils import ColumnNameCleaner
from neutron_utils.config import config, bootstrap_logging

# SQL safety - Excel sheet names can contain special chars, must escape single quotes
def _escape_sheet_name(name: str) -> str:
    """Escape single quotes in sheet name for DuckDB st_read layer parameter"""
    if not name:
        return name
    # Escape single quotes by doubling them
    return name.replace("'", "''")

logger = logging.getLogger(__name__)

_RESERVED_WORDS = {
    "select",
    "from",
    "where",
    "group",
    "order",
    "by",
    "limit",
    "offset",
    "join",
    "left",
    "right",
    "full",
    "inner",
    "outer",
    "on",
    "using",
    "as",
    "case",
    "when",
    "then",
    "else",
    "end",
    "not",
    "and",
    "or",
    "like",
    "ilike",
    "in",
    "is",
    "null",
    "table",
    "column",
    "columns",
    "view",
    "with",
    "recursive",
    "union",
    "all",
    "distinct",
    "having",
    "top",
}


class RedshiftSQLProcessor:
    """
    Processes SQL queries with full Redshift compatibility using DuckDB.
    Supports window functions, Redshift-specific functions, and casting.

    Type handling modes:
    - permissive (default True):
      Attempts to auto-harmonize mixed-type CASE branches (casts THEN/ELSE to VARCHAR)
      and rewrites certain UNIONs to align schemas as VARCHAR when needed.
    - broader_casting: widens string/numeric contexts (e.g., ORDER BY or comparisons) by
      inserting safe CASTs to DOUBLE/VARCHAR heuristically when mixed dtypes are detected.
    - preserve_nulls (default True): keeps NaN/None as SQL NULLs; when False, fills
      strings with '' and numerics with 0 for broader compatibility.
    - strict_strings (default False): prevents auto-conversion of string columns with
      numeric-looking values to numeric types; when False, may convert based on content ratio.
    """

    # Pre-compiled regex patterns for better performance
    _REGEX_PATTERNS = {
        "null_numeric": re.compile(r"null::numeric\b", re.IGNORECASE),
        "null_decimal": re.compile(r"null::decimal\((\d+),(\d+)\)", re.IGNORECASE),
        "null_int": re.compile(r"null::int\b", re.IGNORECASE),
        "null_text": re.compile(r"null::text\b", re.IGNORECASE),
        "null_varchar": re.compile(r"null::varchar\b", re.IGNORECASE),
        "regex_op": re.compile(r"(\w+)\s*~\s*'([^']+)'", re.IGNORECASE),
        "not_regex_op": re.compile(r"(\w+)\s*!~\s*'([^']+)'", re.IGNORECASE),
        "from_clause": re.compile(r"\bFROM\s+(\w+)", re.IGNORECASE),
        "double_colon_cast": re.compile(r"::(\w+)\b", re.IGNORECASE),
        "table_name": re.compile(r"\b{table_name}\b", re.IGNORECASE),
    }

    def __init__(
        self,
        db_path: Optional[str] = None,
        temp_dir: Optional[str] = None,
        memory_limit: Optional[str] = None,
        permissive: bool = True,
        broader_casting: bool = False,
        preserve_nulls: bool = True,
        strict_strings: bool = False,
        autofix_recursive_cte: bool = True,
        autocast_like: bool = True,
        strict_types: Optional[bool] = None,
        strict_types_exclude: Optional[list] = None,
    ):
        """Initialize the processor.

        Args:
            db_path: If provided, uses a file-backed DuckDB database for persistence.
            temp_dir: Optional path for DuckDB temp spill directory to better handle large queries.
            memory_limit: Optional DuckDB memory limit (e.g., '8GB').
        """
        self.conn = None
        try:
            bootstrap_logging()
            # Use file-backed DB when db_path is provided; otherwise in-memory
            self.conn = duckdb.connect(db_path or ":memory:")
            self.permissive = permissive
            self.broader_casting = broader_casting
            self.preserve_nulls = preserve_nulls
            self.strict_strings = strict_strings
            self.autofix_recursive_cte = autofix_recursive_cte
            self.autocast_like = autocast_like
            # Optional type strictness (defaults from config if not provided)
            try:
                self.strict_types = (
                    strict_types if strict_types is not None else bool(config.get("strict_types", False))
                )
            except Exception:
                self.strict_types = bool(strict_types) if strict_types is not None else False
            # Exclusion lists for strict types
            try:
                cfg_excl = config.get("strict_types_exclude", []) or []
                if isinstance(cfg_excl, str):
                    cfg_excl = [x.strip() for x in cfg_excl.split(",") if x.strip()]
            except Exception:
                cfg_excl = []
            self.strict_types_exclude = set([str(x).strip() for x in (strict_types_exclude or [])] + cfg_excl)
            try:
                self.strict_types_exclude_patterns = [
                    s.lower() for s in (config.get("strict_types_exclude_patterns", []) or [])
                ]
            except Exception:
                self.strict_types_exclude_patterns = []
            # Quiet telemetry counters
            self._like_rewrite_pre = 0
            self._like_rewrite_retry = 0

            # Configure resource settings for larger datasets if provided
            if temp_dir:
                try:
                    self.conn.execute(f"SET temp_directory='{temp_dir}'")
                except Exception:
                    pass
            if memory_limit:
                try:
                    self.conn.execute(f"SET memory_limit='{memory_limit}'")
                except Exception:
                    pass
            try:
                self.conn.execute("PRAGMA threads=system_threads();")
            except Exception:
                pass

            self._setup_redshift_compatibility()
            self._setup_excel_extension()
            try:
                logger.info(
                    "DuckDB configured • memory=%s temp_dir=%s threads=auto",
                    memory_limit or config.get("memory_limit_mb"),
                    temp_dir or "default",
                )
            except Exception:
                pass
        except Exception as e:
            if self.conn:
                self.conn.close()
            raise e

    @staticmethod
    def _clean_identifier(name: str) -> str:
        """Clean identifiers consistently using shared cleaner (preserve case)."""
        return ColumnNameCleaner.clean_sql_identifier(name, preserve_case=True)

    @staticmethod
    def _normalize_casts_text(text: str) -> str:
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

    @staticmethod
    def _is_literal(text: str) -> bool:
        t = text.strip()
        return t.startswith("'") or t.startswith("$$")

    @staticmethod
    def _already_cast(text: str) -> bool:
        return re.match(r"(?is)^\s*\(*\s*(?:TRY_)?CAST\s*\(", text or "") is not None

    @staticmethod
    def _scan_left_boundary(expr: str, pos: int) -> int:
        """Scan left from pos to find start of the LHS expression at top level."""
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

    @staticmethod
    def _scan_right_boundary(expr: str, pos: int) -> int:
        """Scan right from pos to find end of RHS expression at top level."""
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

    def _rewrite_like_tokenized(self, sql: str) -> str:
        bounds = self._find_where_bounds(sql)
        if not bounds:
            return sql
        prefix, body, suffix = bounds
        # Iteratively process each LIKE/ILIKE token left to right
        out = body
        changed = False
        while True:
            m = re.search(r"(?is)\b(?:NOT\s+)?(?:I)?LIKE\b", out)
            if not m:
                break
            op_start = m.start()
            op_end = m.end()
            # Compute LHS span
            lhs_start = self._scan_left_boundary(out, op_start)
            lhs = out[lhs_start:op_start].strip()
            # Compute RHS span
            rhs_end = self._scan_right_boundary(out, op_end)
            rhs = out[op_end:rhs_end].strip()
            # Decide which side to cast
            new_lhs, new_rhs = lhs, rhs
            try:
                if self._is_literal(rhs) and not self._already_cast(lhs):
                    new_lhs = f"TRY_CAST(({lhs}) AS VARCHAR)"
                elif self._is_literal(lhs) and not self._already_cast(rhs):
                    new_rhs = f"TRY_CAST(({rhs}) AS VARCHAR)"
                elif not self._is_literal(lhs) and not self._is_literal(rhs):
                    if not self._already_cast(lhs):
                        new_lhs = f"TRY_CAST(({lhs}) AS VARCHAR)"
                    if not self._already_cast(rhs):
                        new_rhs = f"TRY_CAST(({rhs}) AS VARCHAR)"
            except Exception:
                pass
            if new_lhs != lhs or new_rhs != rhs:
                changed = True
                out = f"{out[:lhs_start]}{new_lhs} {out[op_start:op_end]} {new_rhs}{out[rhs_end:]}"
            else:
                # Skip this LIKE occurrence to avoid infinite loop
                out = out[:op_end] + "/*NS_KEEP*/" + out[op_end:]
        out = out.replace("/*NS_KEEP*/", "")
        if not changed:
            return sql
        new_sql = f"{prefix}WHERE{out}{suffix}"
        return self._normalize_casts_text(new_sql)

    @staticmethod
    def _find_where_bounds(sql: str) -> Optional[tuple]:
        """Return (prefix, where_body, suffix) if a top‑level WHERE is found.
        Attempts to respect parentheses and quotes.
        """
        i = 0
        n = len(sql)
        depth = 0
        in_s = False
        in_d = False
        where_start = -1
        # find WHERE
        while i < n:
            ch = sql[i]
            if in_s:
                if ch == "'":
                    if i + 1 < n and sql[i + 1] == "'":
                        i += 2
                        continue
                    in_s = False
                i += 1
                continue
            if in_d:
                if ch == '"':
                    if i + 1 < n and sql[i + 1] == '"':
                        i += 2
                        continue
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
            if ch == ")":
                depth = max(0, depth - 1)
                i += 1
                continue
            if (
                depth == 0
                and sql[i : i + 5].lower() == "where"
                and (i == 0 or not sql[i - 1].isalnum())
                and (i + 5 == n or not sql[i + 5].isalnum())
            ):
                where_start = i
                break
            i += 1
        if where_start < 0:
            return None
        # find end keyword after WHERE body at top level
        i = where_start + 5
        depth = 0
        in_s = False
        in_d = False
        stop = n
        end_keywords = [
            "group by",
            "order by",
            "limit",
            "offset",
            "fetch",
            "union",
            "intersect",
            "except",
            "returning",
            "having",
            "qualify",
        ]
        while i < n:
            ch = sql[i]
            if in_s:
                if ch == "'" and not (i + 1 < n and sql[i + 1] == "'"):
                    in_s = False
                i += 1
                continue
            if in_d:
                if ch == '"' and not (i + 1 < n and sql[i + 1] == '"'):
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
            if ch == ")":
                depth = max(0, depth - 1)
                i += 1
                continue
            if depth == 0:
                low = sql[i:].lower()
                for kw in end_keywords:
                    if low.startswith(kw) and (i == 0 or not sql[i - 1].isalnum()):
                        stop = i
                        i = n
                        break
            i += 1
        prefix = sql[:where_start]
        where_body = sql[where_start + 5 : stop]
        suffix = sql[stop:]
        return (prefix, where_body, suffix)

    @staticmethod
    def _split_top_level_bool(expr: str) -> list:
        """Split on top‑level AND/OR while respecting parentheses/quotes.
        Returns a list of (segment, separator) where separator is the token that followed the segment ('' for last).
        """
        out = []
        i = 0
        n = len(expr)
        depth = 0
        in_s = False
        in_d = False
        start = 0
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
            if ch == ")":
                depth = max(0, depth - 1)
                i += 1
                continue
            if depth == 0:
                low = expr[i:].lower()
                if low.startswith(" and ") or low.startswith(" or "):
                    sep = "AND" if low.startswith(" and ") else "OR"
                    seg = expr[start:i]
                    out.append((seg, sep))
                    i += 5 if sep == "AND" else 4
                    start = i
                    continue
            i += 1
        out.append((expr[start:], ""))
        return out

    def _rewrite_like_structured(self, sql: str) -> str:
        """Retry helper: rewrite LIKE per top‑level boolean segment of WHERE.
        Keeps changes bounded and avoids cross‑segment backtracking.
        """
        bounds = self._find_where_bounds(sql)
        if not bounds:
            return sql
        prefix, body, suffix = bounds
        segments = self._split_top_level_bool(body)
        rewritten = []
        changed = False
        for seg, sep in segments:
            if re.search(r"(?is)\b(?:NOT\s+)?(?:I)?LIKE\b", seg):
                new_seg = self._rewrite_like_any(seg)
                new_seg = RedshiftSQLProcessor._normalize_casts_text(new_seg)
                if new_seg != seg:
                    changed = True
                rewritten.append(new_seg)
            else:
                rewritten.append(seg)
            if sep:
                rewritten.append(f" {sep} ")
        if not changed:
            return sql
        new_body = "".join(rewritten)
        return f"{prefix}WHERE{new_body}{suffix}"

    @staticmethod
    def _apply_column_mapping_to_sql(sql: str, mapping: dict) -> str:
        """Replace quoted original identifiers in SQL with their cleaned names.

        - Matches only double-quoted identifiers (not string literals).
        - Preserves surrounding SQL while replacing the entire quoted token.
        - Handles escaped quotes inside identifiers ("" → ").
        """
        if not mapping:
            return sql

        # Build a lookup with normalized original identifier text
        norm_map = {k: v for k, v in mapping.items()}

        def repl(m: re.Match) -> str:
            inner = m.group(1)
            # Unescape doubled quotes to compare with original header
            ident = inner.replace('""', '"')
            if ident in norm_map:
                cleaned = norm_map[ident]
                # Quote cleaned name if not a simple safe identifier or reserved word
                if not re.match(r"^[A-Za-z_][\w]*$", cleaned) or cleaned.lower() in _RESERVED_WORDS:
                    return f'"{cleaned}"'
                return cleaned
            return m.group(0)

        # Replace only double-quoted identifiers — pattern does not touch single-quoted string literals
        return re.sub(r'"((?:[^"]|"")+)"', repl, sql)

    def __del__(self):
        """Clean up connection on deletion"""
        self.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure connection is closed"""
        self.close()
        return False

    def close(self):
        """Close the DuckDB connection"""
        if hasattr(self, "conn") and self.conn:
            try:
                self.conn.close()
            except Exception as e:
                logger.error(f"Error closing DuckDB connection: {e}")
            finally:
                self.conn = None

    def interrupt(self):
        """Attempt to interrupt a running DuckDB query gracefully."""
        try:
            if hasattr(self, "conn") and self.conn and hasattr(self.conn, "interrupt"):
                # Available in modern DuckDB versions
                self.conn.interrupt()
        except Exception:
            # Best-effort; ignore failures
            pass

    def _rewrite_single_union_to_varchar(self, sql: str) -> Optional[str]:
        """Heuristic: rewrite a single top-level UNION/UNION ALL by casting both sides to VARCHAR.
        Returns rewritten SQL or None if not applicable.
        """
        # Split on the first top-level UNION/UNION ALL (no parentheses awareness; heuristic only)
        m = re.search(r"(?i)\bUNION(?:\s+ALL)?\b", sql)
        if not m:
            return None
        op = m.group(0)
        left = sql[: m.start()].strip()
        right = sql[m.end() :].strip()
        if not left.lower().startswith("select") or not right.lower().startswith("select"):
            return None

        def cols_for(subq: str) -> Optional[list[str]]:
            try:
                df0 = self.conn.execute(f"SELECT * FROM ({subq}) AS sub LIMIT 0").fetchdf()
                return list(df0.columns)
            except Exception as e:
                logger.debug(f"UNION schema inspection failed: {e}")
                return None

        left_cols = cols_for(left)
        right_cols = cols_for(right)
        if not left_cols or not right_cols or len(left_cols) != len(right_cols):
            return None

        def q(ident: str) -> str:
            # Quote identifier safely for DuckDB
            ident = str(ident).replace('"', '""')
            return f'"{ident}"'

        left_select = ", ".join([f"CAST({q(c)} AS VARCHAR) AS {q(c)}" for c in left_cols])
        right_select = ", ".join([f"CAST({q(rc)} AS VARCHAR) AS {q(lc)}" for rc, lc in zip(right_cols, left_cols)])

        rewritten = f"SELECT {left_select} FROM ({left}) AS l\n" f"{op}\n" f"SELECT {right_select} FROM ({right}) AS r"
        return rewritten

    def _rewrite_all_unions_to_varchar(self, sql: str) -> Optional[str]:
        """Apply the single-union rewrite repeatedly until no more changes or failure."""
        prev = None
        current = sql
        for _ in range(5):  # guard against runaway loops
            if prev == current:
                break
            prev = current
            rewritten = self._rewrite_single_union_to_varchar(current)
            if not rewritten or rewritten == current:
                break
            current = rewritten
        return current if current != sql else None

    def _harmonize_case_blocks_robust(self, sql: str) -> str:
        """Find CASE...END blocks and cast THEN/ELSE branch results to VARCHAR when needed.
        Uses a simple scanner to respect quotes and nested CASE depth.
        """
        s = sql
        blocks = []

        def is_word_boundary(text, pos, word):
            n = len(word)
            before = pos == 0 or not (text[pos - 1].isalnum() or text[pos - 1] == "_")
            after = pos + n >= len(text) or not (text[pos + n].isalnum() or text[pos + n] == "_")
            return before and after

        i = 0
        L = len(s)
        while i < L:
            ch = s[i]
            if ch == "'":
                # Skip string literal (single quotes doubled)
                i += 1
                while i < L:
                    if s[i] == "'":
                        i += 1
                        if i < L and s[i] == "'":
                            i += 1
                            continue
                        break
                    else:
                        i += 1
                continue
            # Look for CASE (ci) at word boundary
            if s[i : i + 4].lower() == "case" and is_word_boundary(s, i, "case"):
                # Find matching END
                depth = 1
                j = i + 4
                while j < L and depth > 0:
                    if s[j] == "'":
                        # skip string
                        j += 1
                        while j < L:
                            if s[j] == "'":
                                j += 1
                                if j < L and s[j] == "'":
                                    j += 1
                                    continue
                                break
                            else:
                                j += 1
                        continue
                    # nested CASE
                    if s[j : j + 4].lower() == "case" and is_word_boundary(s, j, "case"):
                        depth += 1
                        j += 4
                        continue
                    if s[j : j + 3].lower() == "end" and is_word_boundary(s, j, "end"):
                        depth -= 1
                        j += 3
                        continue
                    j += 1
                end_pos = j
                if end_pos > i:
                    blocks.append((i, end_pos))
                    i = end_pos
                    continue
            i += 1

        if not blocks:
            return sql

        def needs_cast(expr: str) -> bool:
            t = expr.strip()
            if not t:
                return False
            if t.startswith("'"):
                return False
            if re.match(r"(?i)^CAST\s*\(", t):
                return False
            return True

        # Replace from the end to keep indices stable
        out = []
        last_idx = len(s)
        for start, end in reversed(blocks):
            out.append(s[end:last_idx])
            block = s[start:end]
            # Prepare block text
            b = block
            # Determine if this CASE block contains any string literal at top-level (heuristic):
            block_has_string = "'" in b
            # Process THEN/ELSE at depth 1 inside block
            res = []
            k = 0
            depth = 0
            while k < len(b):
                if b[k] == "'":
                    # copy string
                    m = k + 1
                    while m < len(b):
                        if b[m] == "'":
                            m += 1
                            if m < len(b) and b[m] == "'":
                                m += 1
                                continue
                            break
                        else:
                            m += 1
                    res.append(b[k:m])
                    k = m
                    continue
                if b[k : k + 4].lower() == "case" and is_word_boundary(b, k, "case"):
                    depth += 1
                    res.append(b[k : k + 4])
                    k += 4
                    continue
                if b[k : k + 3].lower() == "end" and is_word_boundary(b, k, "end"):
                    depth = max(0, depth - 1)
                    res.append(b[k : k + 3])
                    k += 3
                    continue
                # At depth 1, handle THEN/ELSE expressions
                if depth == 1 and b[k : k + 4].lower() == "then" and is_word_boundary(b, k, "then"):
                    # emit 'THEN'
                    res.append(b[k : k + 4])
                    res.append(" ")
                    k += 4
                    # capture expression until WHEN/ELSE/END at depth 1
                    # skip spaces
                    m = k
                    while m < len(b) and b[m].isspace():
                        m += 1
                    expr_start = m
                    # scan forward
                    while m < len(b):
                        if b[m] == "'":
                            # skip string
                            m += 1
                            while m < len(b):
                                if b[m] == "'":
                                    m += 1
                                    if m < len(b) and b[m] == "'":
                                        m += 1
                                        continue
                                    break
                                else:
                                    m += 1
                            continue
                        if b[m : m + 4].lower() == "case" and is_word_boundary(b, m, "case"):
                            depth += 1
                            m += 4
                            continue
                        if b[m : m + 3].lower() == "end" and is_word_boundary(b, m, "end"):
                            depth -= 1
                            if depth == 0:
                                break
                            m += 3
                            continue
                        if depth == 1 and (
                            (b[m : m + 4].lower() == "when" and is_word_boundary(b, m, "when"))
                            or (b[m : m + 4].lower() == "else" and is_word_boundary(b, m, "else"))
                            or (b[m : m + 3].lower() == "end" and is_word_boundary(b, m, "end"))
                        ):
                            break
                        m += 1
                    expr_end = m
                    expr = b[expr_start:expr_end]
                    # Cast policy: if any branch in the block likely returns string (heuristic),
                    # cast all branches that aren't quoted/CASTed to VARCHAR to harmonize types.
                    if block_has_string and needs_cast(expr):
                        res.append(f"CAST({expr.strip()} AS VARCHAR)")
                        res.append(" ")
                    else:
                        # ensure at least one space between THEN and expr
                        if not b[expr_start:expr_end].startswith(" "):
                            res.append(" ")
                        res.append(b[expr_start:expr_end])
                    k = expr_end
                    continue
                if depth == 1 and b[k : k + 4].lower() == "else" and is_word_boundary(b, k, "else"):
                    res.append(b[k : k + 4])
                    res.append(" ")
                    k += 4
                    m = k
                    while m < len(b) and b[m].isspace():
                        m += 1
                    expr_start = m
                    while m < len(b):
                        if b[m] == "'":
                            m += 1
                            while m < len(b):
                                if b[m] == "'":
                                    m += 1
                                    if m < len(b) and b[m] == "'":
                                        m += 1
                                        continue
                                    break
                                else:
                                    m += 1
                            continue
                        if b[m : m + 4].lower() == "case" and is_word_boundary(b, m, "case"):
                            depth += 1
                            m += 4
                            continue
                        if b[m : m + 3].lower() == "end" and is_word_boundary(b, m, "end"):
                            depth -= 1
                            if depth == 0:
                                break
                            m += 3
                            continue
                        if depth == 1 and b[m : m + 3].lower() == "end" and is_word_boundary(b, m, "end"):
                            break
                        m += 1
                    expr_end = m
                    expr = b[expr_start:expr_end]
                    if block_has_string and needs_cast(expr):
                        res.append(f"CAST({expr.strip()} AS VARCHAR)")
                        res.append(" ")
                    else:
                        if not b[expr_start:expr_end].startswith(" "):
                            res.append(" ")
                        res.append(b[expr_start:expr_end])
                    k = expr_end
                    continue
                # default copy
                res.append(b[k])
                k += 1

            new_block = "".join(res)
            # Final spacing normalization to avoid THENCAST/ELSECAST or )END
            new_block = re.sub(r"(?i)\bTHEN\s*CAST", "THEN CAST", new_block)
            new_block = re.sub(r"(?i)\bELSE\s*CAST", "ELSE CAST", new_block)
            new_block = re.sub(r"(?i)\)\s*END", ") END", new_block)
            out.append(new_block)
            last_idx = start

        out.append(s[:last_idx])
        return "".join(reversed(out))

    def _setup_excel_extension(self):
        """Setup DuckDB spatial extension for direct Excel reading"""
        try:
            # Install and load spatial extension which includes Excel support
            self.conn.execute("INSTALL spatial")
            self.conn.execute("LOAD spatial")
        except Exception as e:
            logger.debug(f"Could not load spatial extension: {e}")
            # Fall back to pandas if extension not available

    def _setup_redshift_compatibility(self):
        """Setup DuckDB to mimic Redshift SQL behavior"""

        # Install and load PostgreSQL extension for better compatibility
        try:
            self.conn.execute("INSTALL postgres")
            self.conn.execute("LOAD postgres")
        except Exception:
            pass  # Continue without if extension not available

        # Create Redshift-compatible functions
        self._create_redshift_functions()

        # Set SQL dialect options for better compatibility
        self.conn.execute("SET enable_progress_bar=false")
        self.conn.execute("SET preserve_insertion_order=false")

    def _create_redshift_functions(self):
        """Create Redshift-compatible function aliases and implementations"""

        # NVL function (Oracle/Redshift style COALESCE)
        self.conn.execute(
            """
            CREATE OR REPLACE FUNCTION nvl(val1, val2) AS COALESCE(val1, val2)
        """
        )

        # NULLIF function (should already exist but ensure compatibility)
        try:
            self.conn.execute("SELECT NULLIF(1, 1)")
        except Exception:
            self.conn.execute(
                """
                CREATE OR REPLACE FUNCTION nullif(val1, val2) AS 
                CASE WHEN val1 = val2 THEN NULL ELSE val1 END
            """
            )

        # REGEXP_SUBSTR function for pattern extraction
        self.conn.execute(
            """
            CREATE OR REPLACE FUNCTION regexp_substr(text, pattern) AS 
            regexp_extract(text, pattern, 0)
        """
        )

        # Note: DuckDB already has regexp_extract built-in, we just need to handle the calls properly

    def _preprocess_sql(self, sql: str, table_name: str = "catalog_data") -> str:
        """
        Preprocess SQL to make it DuckDB compatible while preserving Redshift semantics
        """

        # Handle null::numeric and null::type patterns first using pre-compiled patterns
        # Convert null::numeric to CAST(NULL AS DECIMAL)
        sql = self._REGEX_PATTERNS["null_numeric"].sub("CAST(NULL AS DECIMAL)", sql)
        sql = self._REGEX_PATTERNS["null_decimal"].sub(r"CAST(NULL AS DECIMAL(\1,\2))", sql)
        sql = self._REGEX_PATTERNS["null_int"].sub("CAST(NULL AS INTEGER)", sql)
        sql = self._REGEX_PATTERNS["null_text"].sub("CAST(NULL AS VARCHAR)", sql)
        sql = self._REGEX_PATTERNS["null_varchar"].sub("CAST(NULL AS VARCHAR)", sql)

        # Handle regex operator ~ by converting to regexp_matches (DuckDB's partial match function)
        # Use pre-compiled patterns for better performance
        sql = self._REGEX_PATTERNS["regex_op"].sub(r"regexp_matches(CAST(\1 AS VARCHAR), '\2')", sql)

        # Handle specific casting patterns that might be problematic
        # Replace Redshift decimal types with DuckDB equivalents
        sql = re.sub(r"::decimal\((\d+),(\d+)\)", r"::DECIMAL(\1,\2)", sql, flags=re.IGNORECASE)
        sql = re.sub(r"::numeric", r"::DECIMAL", sql, flags=re.IGNORECASE)
        sql = re.sub(r"::text", r"::VARCHAR", sql, flags=re.IGNORECASE)
        sql = re.sub(r"::int\b", r"::INTEGER", sql, flags=re.IGNORECASE)

        # Replace table references with our standard table name
        # Handle schema.table references like andes."af-ais-intl".se
        sql = re.sub(r'\bandes\."[^"]+"\.\w+\b', table_name, sql, flags=re.IGNORECASE)

        # Handle simple table references in initial FROM clause only (not CTEs)
        # Be more careful - only replace the first FROM that references a single table
        # Look for FROM followed by a single word that's not a CTE name

        # Find all CTE names first
        cte_names = re.findall(r"(\w+)\s+AS\s*\(", sql, re.IGNORECASE)

        # Also handle column alias references that might not exist as source columns
        # This is a common pattern in SQL where people reference aliases in the same SELECT
        # DuckDB is stricter about this than some other databases
        # For now, we'll let DuckDB handle it and provide better error messages

        def replace_from_table(match):
            table_ref = match.group(1)
            # Don't replace if it's a CTE name
            if table_ref.lower() in [cte.lower() for cte in cte_names]:
                return match.group(0)
            else:
                return f"FROM {table_name}{match.group(2)}"

        # Only replace FROM clauses that don't reference CTEs
        sql = re.sub(r"\bfrom\s+(\w+)(\s)", replace_from_table, sql, flags=re.IGNORECASE)

        # Replace CURRENT_DATE with standardized form
        sql = re.sub(r"\bcurrent_date\b", "CURRENT_DATE", sql, flags=re.IGNORECASE)

        # Redshift-style GETDATE() -> DuckDB CURRENT_TIMESTAMP
        sql = re.sub(r"\bGETDATE\s*\(\s*\)", "CURRENT_TIMESTAMP", sql, flags=re.IGNORECASE)

        # Add RECURSIVE to CTEs when a self-referencing CTE is detected but RECURSIVE is missing
        try:
            if (
                self.autofix_recursive_cte
                and re.search(r"(?i)\bwith\b", sql)
                and not re.search(r"(?i)\bwith\s+recursive\b", sql)
            ):
                text = sql
                m = re.search(r"(?i)\bwith\b", text)
                start = m.start() if m else -1
                if start >= 0:
                    i = start + len(m.group(0))
                    depth = 0
                    in_s = None  # current string quote
                    names_and_bodies = []
                    name = ""
                    body_start = -1
                    # Simple state parser for WITH name AS ( ... ) [, name2 AS ( ... )]
                    while i < len(text):
                        ch = text[i]
                        # handle strings
                        if in_s:
                            if ch == in_s:
                                in_s = None
                            i += 1
                            continue
                        if ch in ("'", '"'):
                            in_s = ch
                            i += 1
                            continue
                        # capture name
                        nm = re.match(r'\s*("?[A-Za-z_][\w]*"?)\s+AS\s*\(', text[i:], re.IGNORECASE)
                        if nm and depth == 0:
                            name = nm.group(1)
                            i += nm.end(0)
                            depth = 1
                            body_start = i
                            # parse body until balanced parens back to 0
                            while i < len(text) and depth > 0:
                                c2 = text[i]
                                if in_s:
                                    if c2 == in_s:
                                        in_s = None
                                else:
                                    if c2 in ("'", '"'):
                                        in_s = c2
                                    elif c2 == "(":
                                        depth += 1
                                    elif c2 == ")":
                                        depth -= 1
                                i += 1
                            body = text[body_start : i - 1] if body_start >= 0 else ""
                            names_and_bodies.append((name, body))
                            # skip optional comma between CTEs
                            cm = re.match(r"\s*,\s*", text[i:])
                            if cm:
                                i += cm.end(0)
                                continue
                            else:
                                break
                        else:
                            # reached main SELECT or something else
                            break
                    # Determine recursion
                    recursive_needed = False
                    for nm, body in names_and_bodies:
                        nm_unquoted = nm.strip('"')
                        if re.search(rf"(?i)\b{re.escape(nm_unquoted)}\b", body):
                            recursive_needed = True
                            break
                    if recursive_needed:
                        logger.info("Auto‑fix: added WITH RECURSIVE for self‑referencing CTE")
                        sql = re.sub(r"(?i)\bwith\b", "WITH RECURSIVE", sql, count=1)
        except Exception:
            # Non-fatal; if detection fails we leave SQL as-is
            pass

        # Fix REGEXP_SUBSTR patterns - DuckDB uses different regex syntax
        # Replace \\b word boundaries with DuckDB-compatible version
        sql = re.sub(r"\\\\b\[0-9\]\+\\\\b", r"[0-9]+", sql)

        # Handle TRIM(LEADING '0' FROM col) syntax
        sql = re.sub(r"trim\s*\(\s*leading\s+\'0\'\s+from\s+(\w+)\s*\)", r"LTRIM(\1, '0')", sql, flags=re.IGNORECASE)

        # Handle REGEXP_EXTRACT calls - ensure text is cast to VARCHAR
        sql = re.sub(
            r"REGEXP_EXTRACT\s*\(\s*(\w+)\s*,", r"REGEXP_EXTRACT(CAST(\1 AS VARCHAR),", sql, flags=re.IGNORECASE
        )

        # Handle case when referencing string columns that might be numeric
        # Generic handling is applied later in _handle_string_functions_on_numeric

        # Fix CASE expressions that mix numeric and string results
        # When we see patterns like (expression)::text, ensure all branches return text
        # This is a common Redshift pattern that DuckDB is strict about

        # First, let's handle the specific pattern where numeric calculations are cast to text
        sql = re.sub(
            r"\(([^)]+)::decimal\s*\*\s*(\d+)\)::text",
            r"CAST(CAST(\1 AS DECIMAL) * \2 AS VARCHAR)",
            sql,
            flags=re.IGNORECASE,
        )

        # Permissive mode: harmonize CASE branches so THEN/ELSE return consistent types (robust parser)
        if getattr(self, "permissive", True) and re.search(r"\bCASE\b", sql, re.IGNORECASE):
            # Run harmonization up to 3 times to catch deep nesting safely
            prev_sql = None
            iterations = 0
            while prev_sql != sql and iterations < 3:
                prev_sql = sql
                sql = self._harmonize_case_blocks_robust(sql)
                iterations += 1

        # Ensure trim operations that appear in ELSE clauses also return VARCHAR
        sql = re.sub(
            r"else\s+trim\s*\(\s*leading\s+\'0\'\s+from\s+(\w+)\s*\)",
            r"else CAST(LTRIM(CAST(\1 AS VARCHAR), '0') AS VARCHAR)",
            sql,
            flags=re.IGNORECASE,
        )

        return sql

    def _extract_column_references(self, sql: str) -> List[str]:
        """Extract potential column references from SQL query.
        Heuristic-only: ignores quoted strings and comments; collects bare identifiers
        and alias-qualified identifiers (alias.col). Filters out SQL keywords and
        common function names.
        """
        text = sql
        # Strip single-line and block comments
        text = re.sub(r"--.*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        # Remove single-quoted and double-quoted strings
        text = re.sub(r"'([^']|'')*'", "''", text)
        text = re.sub(r'"[^"]*"', '""', text)

        # Known SQL keywords and functions to exclude
        keywords = set(
            [
                "SELECT",
                "FROM",
                "WHERE",
                "GROUP",
                "BY",
                "ORDER",
                "HAVING",
                "LIMIT",
                "OFFSET",
                "FETCH",
                "UNION",
                "ALL",
                "DISTINCT",
                "JOIN",
                "LEFT",
                "RIGHT",
                "FULL",
                "INNER",
                "OUTER",
                "ON",
                "USING",
                "AS",
                "WITH",
                "CASE",
                "WHEN",
                "THEN",
                "ELSE",
                "END",
                "OVER",
                "PARTITION",
                "ROWS",
                "RANGE",
                "CURRENT",
                "BETWEEN",
                "AND",
                "OR",
                "NOT",
                "IN",
                "IS",
                "NULL",
                "LIKE",
                "EXISTS",
            ]
        )
        functions = set(
            [
                "NVL",
                "NULLIF",
                "COALESCE",
                "CAST",
                "TRY_CAST",
                "TRIM",
                "LTRIM",
                "RTRIM",
                "UPPER",
                "LOWER",
                "LENGTH",
                "SUBSTR",
                "SUBSTRING",
                "REPLACE",
                "REGEXP_MATCHES",
                "REGEXP_EXTRACT",
                "REGEXP_SUBSTR",
                "REGEXP_REPLACE",
                "CURRENT_DATE",
                "DATE",
                "EXTRACT",
                "DATE_PART",
                "COUNT",
                "SUM",
                "AVG",
                "MIN",
                "MAX",
                "STDDEV",
                "VARIANCE",
                "ROW_NUMBER",
                "RANK",
                "DENSE_RANK",
                "FIRST_VALUE",
                "LAST_VALUE",
                "LAG",
                "LEAD",
                "NTILE",
                "PERCENT_RANK",
                "ROUND",
                "CEIL",
                "FLOOR",
                "ABS",
                "SQRT",
                "POWER",
                "MOD",
                "SPLIT_PART",
                "CONCAT",
            ]
        )

        cols = set()
        # Capture alias.col and plain identifiers
        for m in re.finditer(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\b", text):
            col = m.group(2)
            if col.upper() not in keywords and col.upper() not in functions:
                cols.add(col)

        # Plain identifiers (avoid numbers)
        for m in re.finditer(r"\b([A-Za-z_][\w]*)\b", text):
            token = m.group(1)
            up = token.upper()
            if up in keywords or up in functions:
                continue
            # Skip common SQL literals/functions tokens
            if re.match(r"^\d+$", token):
                continue
            cols.add(token)

        return sorted(cols)

    # legacy analysis function removed

    def _handle_string_functions_on_numeric(self, sql: str, df: pd.DataFrame) -> str:
        """Replace string functions on numeric columns with string versions"""
        # Find LTRIM/TRIM operations on columns
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                # Escape column name for regex (in case it has special characters)
                col_escaped = re.escape(col)

                # Replace LTRIM(col, ...) with LTRIM(CAST(col AS VARCHAR), ...)
                sql = re.sub(
                    rf"\bLTRIM\s*\(\s*{col_escaped}\s*,", f"LTRIM(CAST({col} AS VARCHAR),", sql, flags=re.IGNORECASE
                )

                # Replace LTRIM(col) with LTRIM(CAST(col AS VARCHAR))
                sql = re.sub(
                    rf"\bLTRIM\s*\(\s*{col_escaped}\s*\)", f"LTRIM(CAST({col} AS VARCHAR))", sql, flags=re.IGNORECASE
                )

                # Replace TRIM operations
                sql = re.sub(
                    rf"\bTRIM\s*\(\s*{col_escaped}\s*\)", f"TRIM(CAST({col} AS VARCHAR))", sql, flags=re.IGNORECASE
                )

                # Replace RTRIM operations
                sql = re.sub(
                    rf"\bRTRIM\s*\(\s*{col_escaped}\s*,", f"RTRIM(CAST({col} AS VARCHAR),", sql, flags=re.IGNORECASE
                )
                sql = re.sub(
                    rf"\bRTRIM\s*\(\s*{col_escaped}\s*\)", f"RTRIM(CAST({col} AS VARCHAR))", sql, flags=re.IGNORECASE
                )

                # Handle TRIM with LEADING/TRAILING
                sql = re.sub(
                    rf"\btrim\s*\(\s*leading\s+'[^']*'\s+from\s+{col_escaped}\s*\)",
                    lambda m: m.group(0).replace(col, f"CAST({col} AS VARCHAR)"),
                    sql,
                    flags=re.IGNORECASE,
                )

                # Handle other string functions that might be used on numeric columns
                string_functions = ["UPPER", "LOWER", "LENGTH", "SUBSTR", "SUBSTRING", "REPLACE", "CONCAT"]
                for func in string_functions:
                    # Replace FUNC(col, ...) with FUNC(CAST(col AS VARCHAR), ...)
                    sql = re.sub(
                        rf"\b{func}\s*\(\s*{col_escaped}\s*([,)])",
                        f"{func}(CAST({col} AS VARCHAR)\1",
                        sql,
                        flags=re.IGNORECASE,
                    )

        # Broader casting phase 1 & 2: COALESCE/NVL, CONCAT, comparisons, aggregates, simple date literals
        if getattr(self, "broader_casting", False):
            # Heuristic EU-decimal detection per object column (e.g., '1,23')
            eu_decimal_cols = set()
            if not getattr(self, "strict_strings", False):
                for _col in df.columns:
                    if pd.api.types.is_object_dtype(df[_col]):
                        try:
                            ser = df[_col].dropna().astype(str)
                            if ser.str.contains(r"\d,\d", regex=True).any():
                                eu_decimal_cols.add(_col)
                        except Exception:
                            pass

            def cast_double_expr(col_name: str) -> str:
                return (
                    f"TRY_CAST(REPLACE({col_name}, ',', '.') AS DOUBLE)"
                    if col_name in eu_decimal_cols
                    else f"TRY_CAST({col_name} AS DOUBLE)"
                )

            # Handle COALESCE/NVL on numeric columns: cast args to DOUBLE where possible
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_escaped = re.escape(col)
                    # COALESCE(col, ...)
                    sql = re.sub(
                        rf"(?i)\bCOALESCE\s*\(\s*{col_escaped}\s*,", f"COALESCE(TRY_CAST({col} AS DOUBLE),", sql
                    )
                    # NVL(col, ...)
                    sql = re.sub(rf"(?i)\bNVL\s*\(\s*{col_escaped}\s*,", f"NVL(TRY_CAST({col} AS DOUBLE),", sql)

            # Handle CONCAT robustly: wrap each top-level argument to VARCHAR if it appears numeric-like
            def rewrite_concat_all(s: str) -> str:
                out = []
                i = 0
                L = len(s)
                while i < L:
                    if s[i] == "'":
                        # copy string literal
                        start = i
                        i += 1
                        while i < L:
                            if s[i] == "'":
                                i += 1
                                if i < L and s[i] == "'":
                                    i += 1
                                    continue
                                break
                            i += 1
                        out.append(s[start:i])
                        continue
                    if s[i : i + 6].lower() == "concat" and re.match(r"(?i)\bconcat\b", s[i : i + 6]):
                        j = i + 6
                        while j < L and s[j].isspace():
                            j += 1
                        if j >= L or s[j] != "(":
                            out.append(s[i])
                            i += 1
                            continue
                        # find matching )
                        depth = 1
                        k = j + 1
                        _arg_start = k  # kept for clarity in scans; not used directly
                        args = []
                        last = k
                        while k < L and depth > 0:
                            ch = s[k]
                            if ch == "'":
                                k += 1
                                while k < L:
                                    if s[k] == "'":
                                        k += 1
                                        if k < L and s[k] == "'":
                                            k += 1
                                            continue
                                        break
                                    k += 1
                                continue
                            if ch == "(":
                                depth += 1
                            elif ch == ")":
                                depth -= 1
                                if depth == 0:
                                    # push last arg
                                    args.append(s[last:k].strip())
                                    break
                            elif ch == "," and depth == 1:
                                args.append(s[last:k].strip())
                                last = k + 1
                            k += 1
                        # rewrite args
                        new_args = []
                        for a in args:
                            a_stripped = a.strip()
                            # If already quoted or CASTed, keep
                            if (a_stripped.startswith("'") and a_stripped.endswith("'")) or re.match(
                                r"(?i)^CAST\s*\(", a_stripped
                            ):
                                new_args.append(a)
                                continue
                            # If contains any known numeric column, wrap whole arg
                            contains_numeric_col = any(
                                pd.api.types.is_numeric_dtype(df[c])
                                and re.search(rf"(?i)\b{re.escape(c)}\b", a_stripped)
                                for c in df.columns
                            )
                            if contains_numeric_col:
                                new_args.append(f"CAST(({a}) AS VARCHAR)")
                            else:
                                new_args.append(a)
                        out.append("CONCAT(" + ", ".join(new_args) + ")")
                        i = k + 1
                        continue
                    out.append(s[i])
                    i += 1
                return "".join(out)

            sql = rewrite_concat_all(sql)

            # Comparisons: numeric text vs numeric literal → TRY_CAST(text AS DOUBLE)
            for col in df.columns:
                if pd.api.types.is_object_dtype(df[col]):
                    col_escaped = re.escape(col)
                    # col op number
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s*(=|<>|!=|>=|<=|>|<)\s*([-+]?\d+(?:\.\d+)?)",
                        lambda m: f"{cast_double_expr(col)}{m.group(1)}{m.group(2)}",
                        sql,
                    )
                    # number op col
                    sql = re.sub(
                        rf"(?i)([-+]?\d+(?:\.\d+)?)\s*(=|<>|!=|>=|<=|>|<)\s*{col_escaped}\b",
                        lambda m: f"{m.group(1)}{m.group(2)}{cast_double_expr(col)}",
                        sql,
                    )

            # Aggregates on text numerics: SUM/AVG/MIN/MAX(col) -> aggregate(TRY_CAST(col AS DOUBLE))
            for col in df.columns:
                if pd.api.types.is_object_dtype(df[col]):
                    col_escaped = re.escape(col)
                    sql = re.sub(rf"(?i)\bSUM\s*\(\s*{col_escaped}\s*\)", f"SUM({cast_double_expr(col)})", sql)
                    sql = re.sub(rf"(?i)\bAVG\s*\(\s*{col_escaped}\s*\)", f"AVG({cast_double_expr(col)})", sql)
                    sql = re.sub(rf"(?i)\bMIN\s*\(\s*{col_escaped}\s*\)", f"MIN({cast_double_expr(col)})", sql)
                    sql = re.sub(rf"(?i)\bMAX\s*\(\s*{col_escaped}\s*\)", f"MAX({cast_double_expr(col)})", sql)

            # Date comparisons: text date columns vs 'YYYY-MM-DD' literals
            date_lit_iso = r"'\d{4}-\d{2}-\d{2}'"
            # ISO dash single-digit variants (YYYY-M-D)
            date_lit_iso_single = r"'\d{4}-\d{1,2}-\d{1,2}'"
            # Support single- or double-digit month/day (e.g., '1/1/2024' or '01/01/2024')
            date_lit_slash = r"'\d{1,2}/\d{1,2}/\d{4}'"
            # Accept single-digit month/day for ISO-with-slashes
            date_lit_iso_slash = r"'\d{4}/\d{1,2}/\d{1,2}'"
            # Accept single-digit day/month for dotted formats
            date_lit_dot = r"'\d{1,2}\.\d{1,2}\.\d{4}'"
            # Month names (abbrev and full, optional comma)
            date_lit_mon_abbrev = r"'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}'"
            date_lit_mon_full = r"'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'"
            # Compact YYYYMMDD
            date_lit_compact = r"'\d{8}'"

            def choose_slash_format(lit_str: str) -> str:
                # lit_str includes quotes, like '06/30/2024'
                try:
                    core = lit_str.strip()[1:-1]
                    parts = core.split("/")
                    if len(parts) == 3:
                        a, b, y = parts
                        ai = int(a)
                        bi = int(b)
                        if ai > 12 and bi <= 12:
                            return "%d/%m/%Y"
                        if bi > 12 and ai <= 12:
                            return "%m/%d/%Y"
                except Exception:
                    pass
                # default to US
                return "%m/%d/%Y"

            def choose_month_format(lit_str: str, full: bool) -> str:
                fmt = "%B %d, %Y" if full else "%b %d, %Y"
                if "," not in lit_str:
                    fmt = fmt.replace(", ", " ")
                return fmt

            for col in df.columns:
                if pd.api.types.is_object_dtype(df[col]):
                    col_escaped = re.escape(col)
                    # col op ISO date
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s*(=|<>|!=|>=|<=|>|<)\s*({date_lit_iso})",
                        lambda m: f"TRY_CAST({col} AS DATE){m.group(1)}DATE {m.group(2)}",
                        sql,
                    )
                    # ISO date op col
                    sql = re.sub(
                        rf"(?i)({date_lit_iso})\s*(=|<>|!=|>=|<=|>|<)\s*{col_escaped}\b",
                        lambda m: f"DATE {m.group(1)}{m.group(2)}TRY_CAST({col} AS DATE)",
                        sql,
                    )
                    # BETWEEN ISO 'date1' AND 'date2'
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s+BETWEEN\s+({date_lit_iso})\s+AND\s+({date_lit_iso})",
                        lambda m: f"TRY_CAST({col} AS DATE) BETWEEN DATE {m.group(1)} AND DATE {m.group(2)}",
                        sql,
                    )

                    # ISO dash single-digit (use STRPTIME)
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s*(=|<>|!=|>=|<=|>|<)\s*({date_lit_iso_single})",
                        lambda m: f"TRY_CAST({col} AS DATE){m.group(1)}TRY_CAST(STRPTIME({m.group(2)}, '%Y-%m-%d') AS DATE)",
                        sql,
                    )
                    sql = re.sub(
                        rf"(?i)({date_lit_iso_single})\s*(=|<>|!=|>=|<=|>|<)\s*{col_escaped}\b",
                        lambda m: f"TRY_CAST(STRPTIME({m.group(1)}, '%Y-%m-%d') AS DATE){m.group(2)}TRY_CAST({col} AS DATE)",
                        sql,
                    )
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s+BETWEEN\s+({date_lit_iso_single})\s+AND\s+({date_lit_iso_single})",
                        lambda m: f"TRY_CAST({col} AS DATE) BETWEEN TRY_CAST(STRPTIME({m.group(1)}, '%Y-%m-%d') AS DATE) AND TRY_CAST(STRPTIME({m.group(2)}, '%Y-%m-%d') AS DATE)",
                        sql,
                    )

                    # col op 'MM/DD/YYYY' or 'DD/MM/YYYY' pick format by values
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s*(=|<>|!=|>=|<=|>|<)\s*({date_lit_slash})",
                        lambda m: f"TRY_CAST({col} AS DATE){m.group(1)}TRY_CAST(STRPTIME({m.group(2)}, '{choose_slash_format(m.group(2))}') AS DATE)",
                        sql,
                    )
                    # 'MM/DD/YYYY' or 'DD/MM/YYYY' op col
                    sql = re.sub(
                        rf"(?i)({date_lit_slash})\s*(=|<>|!=|>=|<=|>|<)\s*{col_escaped}\b",
                        lambda m: f"TRY_CAST(STRPTIME({m.group(1)}, '{choose_slash_format(m.group(1))}') AS DATE){m.group(2)}TRY_CAST({col} AS DATE)",
                        sql,
                    )

                    # BETWEEN ambiguous slashes
                    def between_slash_repl(m):
                        left = m.group(1)
                        right = m.group(2)
                        fmt_l = choose_slash_format(left)
                        fmt_r = choose_slash_format(right)
                        return (
                            f"TRY_CAST({col} AS DATE) BETWEEN "
                            f"TRY_CAST(STRPTIME({left}, '{fmt_l}') AS DATE) AND "
                            f"TRY_CAST(STRPTIME({right}, '{fmt_r}') AS DATE)"
                        )

                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s+BETWEEN\s+({date_lit_slash})\s+AND\s+({date_lit_slash})",
                        between_slash_repl,
                        sql,
                    )

                    # ISO with slashes YYYY/MM/DD
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s*(=|<>|!=|>=|<=|>|<)\s*({date_lit_iso_slash})",
                        lambda m: f"TRY_CAST({col} AS DATE){m.group(1)}TRY_CAST(STRPTIME({m.group(2)}, '%Y/%m/%d') AS DATE)",
                        sql,
                    )
                    sql = re.sub(
                        rf"(?i)({date_lit_iso_slash})\s*(=|<>|!=|>=|<=|>|<)\s*{col_escaped}\b",
                        lambda m: f"TRY_CAST(STRPTIME({m.group(1)}, '%Y/%m/%d') AS DATE){m.group(2)}TRY_CAST({col} AS DATE)",
                        sql,
                    )
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s+BETWEEN\s+({date_lit_iso_slash})\s+AND\s+({date_lit_iso_slash})",
                        lambda m: f"TRY_CAST({col} AS DATE) BETWEEN TRY_CAST(STRPTIME({m.group(1)}, '%Y/%m/%d') AS DATE) AND TRY_CAST(STRPTIME({m.group(2)}, '%Y/%m/%d') AS DATE)",
                        sql,
                    )

                    # Dot format DD.MM.YYYY
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s*(=|<>|!=|>=|<=|>|<)\s*({date_lit_dot})",
                        lambda m: f"TRY_CAST({col} AS DATE){m.group(1)}TRY_CAST(STRPTIME({m.group(2)}, '%d.%m.%Y') AS DATE)",
                        sql,
                    )
                    sql = re.sub(
                        rf"(?i)({date_lit_dot})\s*(=|<>|!=|>=|<=|>|<)\s*{col_escaped}\b",
                        lambda m: f"TRY_CAST(STRPTIME({m.group(1)}, '%d.%m.%Y') AS DATE){m.group(2)}TRY_CAST({col} AS DATE)",
                        sql,
                    )
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s+BETWEEN\s+({date_lit_dot})\s+AND\s+({date_lit_dot})",
                        lambda m: f"TRY_CAST({col} AS DATE) BETWEEN TRY_CAST(STRPTIME({m.group(1)}, '%d.%m.%Y') AS DATE) AND TRY_CAST(STRPTIME({m.group(2)}, '%d.%m.%Y') AS DATE)",
                        sql,
                    )

                    # Month-name (abbrev)
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s*(=|<>|!=|>=|<=|>|<)\s*({date_lit_mon_abbrev})",
                        lambda m: f"TRY_CAST({col} AS DATE){m.group(1)}TRY_CAST(STRPTIME({m.group(2)}, '{choose_month_format(m.group(2), full=False)}') AS DATE)",
                        sql,
                    )
                    sql = re.sub(
                        rf"(?i)({date_lit_mon_abbrev})\s*(=|<>|!=|>=|<=|>|<)\s*{col_escaped}\b",
                        lambda m: f"TRY_CAST(STRPTIME({m.group(1)}, '{choose_month_format(m.group(1), full=False)}') AS DATE){m.group(2)}TRY_CAST({col} AS DATE)",
                        sql,
                    )
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s+BETWEEN\s+({date_lit_mon_abbrev})\s+AND\s+({date_lit_mon_abbrev})",
                        lambda m: f"TRY_CAST({col} AS DATE) BETWEEN TRY_CAST(STRPTIME({m.group(1)}, '{choose_month_format(m.group(1), full=False)}') AS DATE) AND TRY_CAST(STRPTIME({m.group(2)}, '{choose_month_format(m.group(2), full=False)}') AS DATE)",
                        sql,
                    )

                    # Month-name (full)
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s*(=|<>|!=|>=|<=|>|<)\s*({date_lit_mon_full})",
                        lambda m: f"TRY_CAST({col} AS DATE){m.group(1)}TRY_CAST(STRPTIME({m.group(2)}, '{choose_month_format(m.group(2), full=True)}') AS DATE)",
                        sql,
                    )
                    sql = re.sub(
                        rf"(?i)({date_lit_mon_full})\s*(=|<>|!=|>=|<=|>|<)\s*{col_escaped}\b",
                        lambda m: f"TRY_CAST(STRPTIME({m.group(1)}, '{choose_month_format(m.group(1), full=True)}') AS DATE){m.group(2)}TRY_CAST({col} AS DATE)",
                        sql,
                    )
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s+BETWEEN\s+({date_lit_mon_full})\s+AND\s+({date_lit_mon_full})",
                        lambda m: f"TRY_CAST({col} AS DATE) BETWEEN TRY_CAST(STRPTIME({m.group(1)}, '{choose_month_format(m.group(1), full=True)}') AS DATE) AND TRY_CAST(STRPTIME({m.group(2)}, '{choose_month_format(m.group(2), full=True)}') AS DATE)",
                        sql,
                    )

                    # Compact YYYYMMDD
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s*(=|<>|!=|>=|<=|>|<)\s*({date_lit_compact})",
                        lambda m: f"TRY_CAST({col} AS DATE){m.group(1)}TRY_CAST(STRPTIME({m.group(2)}, '%Y%m%d') AS DATE)",
                        sql,
                    )
                    sql = re.sub(
                        rf"(?i)({date_lit_compact})\s*(=|<>|!=|>=|<=|>|<)\s*{col_escaped}\b",
                        lambda m: f"TRY_CAST(STRPTIME({m.group(1)}, '%Y%m%d') AS DATE){m.group(2)}TRY_CAST({col} AS DATE)",
                        sql,
                    )
                    sql = re.sub(
                        rf"(?i)\b{col_escaped}\s+BETWEEN\s+({date_lit_compact})\s+AND\s+({date_lit_compact})",
                        lambda m: f"TRY_CAST({col} AS DATE) BETWEEN TRY_CAST(STRPTIME({m.group(1)}, '%Y%m%d') AS DATE) AND TRY_CAST(STRPTIME({m.group(2)}, '%Y%m%d') AS DATE)",
                        sql,
                    )

            # GROUP BY / ORDER BY coercion: cast object columns to DOUBLE where safe
            def rewrite_clause(keyword: str, text: str) -> str:
                # Find keyword and process argument list respecting parentheses/quotes
                # Capture any trailing whitespace before the next keyword so we can preserve spacing
                pattern = re.compile(
                    rf"(?is)\b{keyword}\s+BY\s+(.+?)(\s*)(?=(\bLIMIT\b|\bOFFSET\b|\bFETCH\b|\bUNION\b|\bORDER\s+BY\b|\bGROUP\s+BY\b|$))"
                )

                def repl(m):
                    args_str = m.group(1)
                    trailing_ws = m.group(2) or " "
                    # split by commas at top level
                    args = []
                    depth = 0
                    i = 0
                    start = 0
                    while i < len(args_str):
                        ch = args_str[i]
                        if ch == "'":
                            i += 1
                            while i < len(args_str):
                                if args_str[i] == "'":
                                    i += 1
                                    if i < len(args_str) and args_str[i] == "'":
                                        i += 1
                                        continue
                                    break
                                i += 1
                        elif ch == "(":
                            depth += 1
                        elif ch == ")":
                            depth = max(0, depth - 1)
                        elif ch == "," and depth == 0:
                            args.append(args_str[start:i].strip())
                            start = i + 1
                        i += 1
                    args.append(args_str[start:].strip())

                    # rewrite each arg if it's a bare object column name (with optional ASC/DESC/NULLS)
                    def rewrite_arg(a: str) -> str:
                        m = re.match(r"(?is)^([a-zA-Z_][\w]*)\s*(ASC|DESC)?\s*(NULLS\s+(FIRST|LAST))?\s*$", a)
                        if not m:
                            return a
                        col = m.group(1)
                        if col in df.columns and pd.api.types.is_object_dtype(df[col]):
                            suffix = ((" " + m.group(2)) if m.group(2) else "") + (
                                (" " + m.group(3)) if m.group(3) else ""
                            )
                            return f"{cast_double_expr(col)}{suffix}"
                        return a

                    new_args = [rewrite_arg(a) for a in args if a]
                    # Ensure there is at least one space before the next clause/token
                    return f"{keyword} BY " + ", ".join(new_args) + (trailing_ws if trailing_ws else " ")

                return pattern.sub(repl, text)

            # Only rewrite ORDER BY to avoid GROUP BY/SELECT mismatch errors
            sql = rewrite_clause("ORDER", sql)

            # Column-to-column numeric mismatch (object vs numeric) in comparisons and joins
            object_cols = [c for c in df.columns if pd.api.types.is_object_dtype(df[c])]
            numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            for oc in object_cols:
                for nc in numeric_cols:
                    oc_e = re.escape(oc)
                    nc_e = re.escape(nc)
                    # oc op nc
                    sql = re.sub(
                        rf"(?i)\b{oc_e}\s*(=|<>|!=|>=|<=|>|<)\s*{nc_e}\b",
                        lambda m: f"{cast_double_expr(oc)}{m.group(1)}{nc}",
                        sql,
                    )
                    # nc op oc
                    sql = re.sub(
                        rf"(?i)\b{nc_e}\s*(=|<>|!=|>=|<=|>|<)\s*{oc_e}\b",
                        lambda m: f"{nc}{m.group(1)}{cast_double_expr(oc)}",
                        sql,
                    )

            # Aggregates over CASE returning VARCHAR (wrap whole CASE to numeric for aggregates)
            sql = re.sub(r"(?is)\b(SUM|AVG|MIN|MAX)\s*\(\s*(CASE\b.*?END)\s*\)", r"\1(TRY_CAST(\2 AS DOUBLE))", sql)

            # Note: avoid global date literal rewriting to prevent recursive corruption.

        return sql

    def _handle_like_on_binary(self, sql: str, df: pd.DataFrame) -> str:
        """Wrap LIKE comparisons on columns that are likely binary/BLOB or numeric with CAST to VARCHAR.

        Fixes errors like: no function matches ~~(BLOB, STRING_LITERAL) or ~~(DOUBLE, STRING_LITERAL).
        Only rewrites simple patterns "col LIKE 'literal'" or "col ILIKE 'literal'".
        """
        try:
            if not getattr(self, "autocast_like", True):
                return sql
            cast_cols = set()
            for col in df.columns:
                s = df[col]
                try:
                    if s.dropna().map(lambda x: isinstance(x, (bytes, bytearray))).any():
                        cast_cols.add(col)
                    # Also consider numeric dtypes for LIKE
                    if pd.api.types.is_numeric_dtype(s):
                        cast_cols.add(col)
                except Exception:
                    pass
            if not cast_cols:
                return sql
            for col in cast_cols:
                # Build a pattern that matches optional qualifiers and quoted names
                # Allow escaped quotes inside identifiers
                base_token = r"(?:\"(?:[^\"]|\"\")+\"|[A-Za-z_][\w]*)"
                col_qualified = rf"(?:{base_token}\.){{0,2}}(?:\"{re.escape(col)}\"|{re.escape(col)})"
                literal = r"'(?:[^']|'')*'|\$\$.*?\$\$"

                # LHS: <expr> [NOT] LIKE 'literal'
                pat1 = re.compile(rf"(?is)({col_qualified})\s+((?:NOT\s+)?)\s*(ILIKE|LIKE)\s+({literal})")

                def repl_lhs(m):
                    lhs = m.group(1)
                    notkw = m.group(2) or ""
                    op = m.group(3)
                    lit = m.group(4)
                    # If already cast, leave unchanged
                    if re.match(r"(?is)\s*\(*\s*(?:TRY_)?CAST\s*\(", lhs):
                        return m.group(0)
                    # Wrap operand in parentheses to preserve complex expressions
                    return f"CAST(({lhs}) AS VARCHAR) {notkw}{op} {lit}"

                sql = pat1.sub(repl_lhs, sql)

                # RHS: 'literal' [NOT] LIKE <expr>
                pat2 = re.compile(rf"(?is)({literal})\s+((?:NOT\s+)?)\s*(ILIKE|LIKE)\s+({col_qualified})")

                def repl_rhs(m):
                    lit = m.group(1)
                    notkw = m.group(2) or ""
                    op = m.group(3)
                    rhs = m.group(4)
                    if re.match(r"(?is)\s*\(*\s*(?:TRY_)?CAST\s*\(", rhs):
                        return m.group(0)
                    return f"{lit} {notkw}{op} CAST(({rhs}) AS VARCHAR)"

                sql = pat2.sub(repl_rhs, sql)
        except Exception:
            pass
        return sql

    def _rewrite_like_any(self, sql: str) -> str:
        """Greedier LIKE rewriter: casts LHS or RHS to VARCHAR for LIKE/ILIKE.

        This is a last‑resort rewrite used only after a LIKE type error occurs.
        It does not attempt deep SQL parsing; it wraps simple LHS/RHS expressions
        that look like identifiers or function calls.
        """
        try:

            def _is_casted(expr: str) -> bool:
                # Detect leading optional parentheses before (TRY_)CAST
                return re.match(r"(?is)^\s*\(*\s*(?:TRY_)?CAST\s*\(", expr or "") is not None

            def _preceded_by_cast(m: re.Match, group_index: int = 1) -> bool:
                """True if the captured operand begins immediately after a CAST( or TRY_CAST(."""
                try:
                    left = m.string[: m.start(group_index)]
                    return re.search(r"(?is)(?:TRY_)?CAST\s*\(\s*$", left[-100:]) is not None
                except Exception:
                    return False

            def wrap_lhs(m):
                lhs, not_part, op, rhs = m.group(1), (m.group(2) or ""), m.group(3), m.group(4)
                # If operand is already inside an existing CAST( … ), leave unchanged
                if _preceded_by_cast(m, 1):
                    return m.group(0)
                # If operand already in form (X AS VARCHAR), treat as casted by normalizing X
                m_paren = re.match(r"(?is)^\s*\(\s*(.+?)\s+AS\s+VARCHAR\s*\)\s*$", lhs or "")
                if m_paren:
                    lhs = m_paren.group(1)
                # If operand is a CASE expression, enforce explicit parentheses in CAST
                if re.match(r"(?is)^\s*\(*\s*CASE\b.*END\s*\)*\s*$", lhs or "") and not _is_casted(lhs):
                    inner = re.sub(r"(?is)^\s*\(\s*(.*)\s*\)\s*$", r"\1", lhs)
                    return f"CAST(({inner}) AS VARCHAR) {not_part}{op} {rhs}"
                if _is_casted(lhs):
                    return f"{lhs} {not_part}{op} {rhs}"
                return f"CAST(({lhs}) AS VARCHAR) {not_part}{op} {rhs}"

            def wrap_rhs(m):
                lhs, not_part, op, rhs = m.group(1), (m.group(2) or ""), m.group(3), m.group(4)
                if _preceded_by_cast(m, 4):
                    return m.group(0)
                m_paren = re.match(r"(?is)^\s*\(\s*(.+?)\s+AS\s+VARCHAR\s*\)\s*$", rhs or "")
                if m_paren:
                    rhs = m_paren.group(1)
                if re.match(r"(?is)^\s*\(*\s*CASE\b.*END\s*\)*\s*$", rhs or "") and not _is_casted(rhs):
                    inner = re.sub(r"(?is)^\s*\(\s*(.*)\s*\)\s*$", r"\1", rhs)
                    return f"{lhs} {not_part}{op} CAST(({inner}) AS VARCHAR)"
                if _is_casted(rhs):
                    return f"{lhs} {not_part}{op} {rhs}"
                return f"{lhs} {not_part}{op} CAST(({rhs}) AS VARCHAR)"

            # Qualified/quoted identifier or simple function call as LHS
            # Allow quoted identifiers with spaces and escaped quotes: "a""b"
            ident_core = r"(?:\"(?:[^\"]|\"\")+\"|[A-Za-z_][\w]*)"
            ident = rf"(?:{ident_core}\.){{0,2}}{ident_core}(?:\s*\([^\)]*\))?"
            # Guard: do not match SQL keywords like NOT/AND/OR/WHERE/CAST/TRY_CAST as identifiers
            kw_guard = r"(?!\b(?:NOT|AND|OR|WHERE|HAVING|GROUP|ORDER|LIMIT|OFFSET|CASE|END|CAST|TRY_CAST)\b)"
            ident_safe = rf"{kw_guard}{ident}"
            literal = r"'(?:[^']|'')*'|\$\$.*?\$\$"

            # Do not pre-rewrite here; handle normalization inside wrappers to avoid over-matching.
            # LHS/RHS patterns (support optional NOT) with keyword guard on identifier
            pat_lhs = re.compile(rf"(?is)({ident_safe})\s+(NOT\s+)?(ILIKE|LIKE)\s+({literal})")
            pat_rhs = re.compile(rf"(?is)({literal})\s+(NOT\s+)?(ILIKE|LIKE)\s+({ident_safe})")
            # Identifier vs identifier (both guarded)
            pat_ii = re.compile(rf"(?is)({ident_safe})\s+(NOT\s+)?(ILIKE|LIKE)\s+({ident_safe})")

            # CASE expressions as LIKE operand (wrap CASE)
            case_expr = r"(?:\(\s*)?CASE\b.*?END(?:\s*\))?"
            pat_case_lhs = re.compile(rf"(?is)({case_expr})\s+(NOT\s+)?(ILIKE|LIKE)\s+({literal})")
            pat_case_rhs = re.compile(rf"(?is)({literal})\s+(NOT\s+)?(ILIKE|LIKE)\s+({case_expr})")

            # Parenthesized simple sub-expression as LIKE operand
            paren_expr = r"\((?:[^()\'\"]|\'[^\']*\'|\"(?:[^\"]|\"\")*\")+\)"
            pat_paren_lhs = re.compile(rf"(?is)({paren_expr})\s+(NOT\s+)?(ILIKE|LIKE)\s+({literal})")
            pat_paren_rhs = re.compile(rf"(?is)({literal})\s+(NOT\s+)?(ILIKE|LIKE)\s+({paren_expr})")

            # Single-pass, ordered substitutions to avoid overlapping casts
            out = sql
            # Handle CASE and parenthesized expressions first to prevent generic ident from mis-capturing tokens like WHERE
            out = pat_case_lhs.sub(wrap_lhs, out)
            out = pat_case_rhs.sub(wrap_rhs, out)
            out = pat_paren_lhs.sub(wrap_lhs, out)
            out = pat_paren_rhs.sub(wrap_rhs, out)
            # Then identifier vs identifier
            out = pat_ii.sub(
                lambda m: (
                    f"{(m.group(1) if _is_casted(m.group(1)) else f'CAST(({m.group(1)}) AS VARCHAR)')} "
                    f"{(m.group(2) or '')}{m.group(3)} "
                    f"{(m.group(4) if _is_casted(m.group(4)) else f'CAST(({m.group(4)}) AS VARCHAR)')}"
                ),
                out,
            )
            # Finally function-wrapped identifiers (LOWER/UPPER/TRIM/LTRIM/RTRIM), then generic identifier LHS/RHS
            func_name = r"(?:LOWER|UPPER|TRIM|LTRIM|RTRIM)"
            pat_func_lhs = re.compile(
                rf"(?is)({func_name}\s*\(\s*{ident_safe}\s*\))\s+(NOT\s+)?(ILIKE|LIKE)\s+({literal})"
            )
            pat_func_rhs = re.compile(
                rf"(?is)({literal})\s+(NOT\s+)?(ILIKE|LIKE)\s+({func_name}\s*\(\s*{ident_safe}\s*\))"
            )
            out = pat_func_lhs.sub(
                lambda m: (
                    f"CAST(({m.group(1)}) AS VARCHAR) {(m.group(2) or '')}{m.group(3)} {m.group(4)}"
                    if not _is_casted(m.group(1))
                    else f"{m.group(1)} {(m.group(2) or '')}{m.group(3)} {m.group(4)}"
                ),
                out,
            )
            out = pat_func_rhs.sub(
                lambda m: (
                    f"{m.group(1)} {(m.group(2) or '')}{m.group(3)} CAST(({m.group(4)}) AS VARCHAR)"
                    if not _is_casted(m.group(4))
                    else f"{m.group(1)} {(m.group(2) or '')}{m.group(3)} {m.group(4)}"
                ),
                out,
            )
            # Generic identifier LHS/RHS
            out = pat_lhs.sub(wrap_lhs, out)
            out = pat_rhs.sub(wrap_rhs, out)
            # Final normalization inside the rewrite
            out = RedshiftSQLProcessor._normalize_casts_text(out)
            return out
        except Exception:
            return sql

    def execute_sql_direct(
        self, sql: str, file_path: str, table_name: str = "excel_file", sheet_name: str = None
    ) -> pd.DataFrame:
        """
        Execute SQL query directly against Excel file without loading into memory

        Args:
            sql: The SQL query (can contain Redshift-specific syntax)
            file_path: Path to Excel file
            table_name: Name to use for the table in SQL (default: 'excel_file')
            sheet_name: Specific sheet to query (default: first sheet)

        Returns:
            pd.DataFrame: Query results
        """
        try:
            # Preprocess SQL for compatibility
            processed_sql = self._preprocess_sql(sql, table_name)
            # Apply original→cleaned column name mapping in user SQL (quoted identifiers)
            try:
                processed_sql = self._apply_column_mapping_to_sql(processed_sql, getattr(self, "column_mapping", {}))
            except Exception as map_err:
                logger.debug(f"Column mapping rewrite skipped: {map_err}")

            # Try direct Excel query first
            try:
                # Create or replace the table from Excel file
                # Note: table_name is validated by _preprocess_sql, sheet_name needs escaping
                if sheet_name:
                    # Query specific sheet (escape single quotes in sheet name)
                    safe_sheet = _escape_sheet_name(sheet_name)
                    self.conn.execute(
                        f"""
                        CREATE OR REPLACE TABLE {table_name} AS
                        SELECT * FROM st_read(?, layer='{safe_sheet}')
                    """,
                        [file_path],
                    )
                else:
                    # Query default (first) sheet
                    self.conn.execute(
                        f"""
                        CREATE OR REPLACE TABLE {table_name} AS
                        SELECT * FROM st_read(?)
                    """,
                        [file_path],
                    )

                logger.info(f"Direct Excel query: Loading {file_path}")

                # Execute the query
                result = self.conn.execute(processed_sql).fetchdf()

                # Clean up
                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")

                logger.info(f"✓ Direct query completed: {len(result):,} rows × {len(result.columns)} columns")
                return result

            except Exception as direct_error:
                logger.debug(f"Direct Excel query failed: {direct_error}")
                # Fall back to pandas method
                logger.info("Falling back to pandas Excel reader...")
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                return self.execute_sql(processed_sql, df, table_name)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ SQL Execution Failed: {error_msg}")
            raise Exception(f"SQL Error: {error_msg}") from e

    def get_excel_sheets(self, file_path: str) -> List[str]:
        """Get list of sheet names from Excel file"""
        try:
            # Try with DuckDB first
            result = self.conn.execute("SELECT * FROM st_list_layers(?)", [file_path]).fetchall()
            return [row[0] for row in result]
        except Exception:
            # Fallback to pandas
            import pandas as pd

            xl_file = pd.ExcelFile(file_path)
            return xl_file.sheet_names

    def execute_sql(self, sql: str, df: pd.DataFrame, table_name: str = "catalog_data") -> pd.DataFrame:
        """
        Execute SQL query against DataFrame with full Redshift compatibility

        Args:
            sql: The SQL query (can contain Redshift-specific syntax)
            df: Input DataFrame to query
            table_name: Name to use for the table in SQL (default: 'catalog_data')

        Returns:
            pd.DataFrame: Query results
        """

        try:
            # Convert and prepare DataFrame for SQL processing
            df_converted = df.copy()

            # Smart type conversion for SQL compatibility
            # Preserve strings for identifiers, but convert numeric-looking strings to numbers
            identifier_patterns = [
                "BARCODE",
                "UPC",
                "EAN",
                "GTIN",
                "SKU",
                "MERCHANT_SKU",
                "PRODUCT_CODE",
                "ITEM_CODE",
                "ASIN",
                "ISBN",
            ]
            numeric_patterns = [
                "PRICE",
                "COST",
                "SALES",
                "REVENUE",
                "AMOUNT",
                "VALUE",
                "QUANTITY",
                "QTY",
                "COUNT",
                "WEIGHT",
                "SIZE",
                "VOLUME",
                "PERCENT",
                "RATE",
                "MARGIN",
                "DISCOUNT",
                "TAX",
                "TOTAL",
            ]

            # Clean column names - replace spaces and special characters consistently
            column_mapping = {}
            for col in df_converted.columns:
                clean_col = self._clean_identifier(col)
                if clean_col != col:
                    column_mapping[col] = clean_col
                    df_converted = df_converted.rename(columns={col: clean_col})

            # Store column mapping for better error messages
            self.column_mapping = column_mapping

            # Log column name changes with more detail
            if column_mapping:
                logger.info("=" * 60)
                logger.info("COLUMN NAME MAPPING:")
                logger.info("Original Name → Cleaned Name")
                logger.info("-" * 60)
                for orig, clean in column_mapping.items():
                    logger.info(f"{orig} → {clean}")
                logger.info("=" * 60)
                logger.info("💡 Use the cleaned column names (right side) in your SQL queries!")
                logger.info("=" * 60)

            for col in df_converted.columns:
                col_upper = col.upper()
                # Identify identifier-like and numeric-like columns from names
                is_identifier = any(pattern in col_upper for pattern in identifier_patterns)
                is_numeric_col = any(pattern in col_upper for pattern in numeric_patterns)

                # Object or string-like columns
                if pd.api.types.is_object_dtype(df_converted[col]) or pd.api.types.is_string_dtype(df_converted[col]):
                    if not getattr(self, "strict_strings", False) and is_numeric_col and not is_identifier:
                        try:
                            cleaned_series = df_converted[col].astype(str).str.replace(r"[^\d.-]", "", regex=True)
                            numeric_series = pd.to_numeric(cleaned_series, errors="coerce")
                            if (numeric_series.notna().sum() / max(len(numeric_series), 1)) > 0.7:
                                df_converted[col] = numeric_series
                                logger.info(f"Converted '{col}' from string to numeric for SQL operations")
                            else:
                                # Keep original; optionally preserve NULLs
                                if not getattr(self, "preserve_nulls", True):
                                    df_converted[col] = df_converted[col].fillna("").astype(str)
                        except Exception as e:
                            logger.debug(f"Could not convert {col} to numeric: {e}")
                            if not getattr(self, "preserve_nulls", True):
                                df_converted[col] = df_converted[col].fillna("").astype(str)
                    else:
                        # Keep as string/objects; only coerce to str if not preserving NULLs
                        if not getattr(self, "preserve_nulls", True):
                            df_converted[col] = df_converted[col].fillna("").astype(str)

                # Numeric columns: preserve NaN as SQL NULL if requested
                elif pd.api.types.is_numeric_dtype(df_converted[col]):
                    if not getattr(self, "preserve_nulls", True):
                        df_converted[col] = df_converted[col].fillna(0)

                # Boolean columns: keep as-is (DuckDB handles booleans). If needed, cast to int.
                elif pd.api.types.is_bool_dtype(df_converted[col]):
                    # Leave booleans as bool to preserve NULLs; only cast when not preserving
                    if not getattr(self, "preserve_nulls", True):
                        df_converted[col] = df_converted[col].astype(int)

                # Datetime columns: keep native dtype to preserve NULLs and types
                elif pd.api.types.is_datetime64_any_dtype(df_converted[col]):
                    if not getattr(self, "preserve_nulls", True):
                        df_converted[col] = df_converted[col].astype(str)

            # Optional strict type enforcement by content ratio (off by default)
            if getattr(self, "strict_types", False):
                try:
                    numeric_ratio = float(config.get("strict_type_numeric_ratio", 0.7))
                except Exception:
                    numeric_ratio = 0.7
                numeric_converted = 0
                text_enforced = 0
                for col in list(df_converted.columns):
                    s = df_converted[col]
                    # Respect explicit excludes and pattern-based excludes
                    if col in getattr(self, "strict_types_exclude", set()):
                        text_enforced += 1
                        continue
                    col_lower = str(col).lower()
                    if any(pat in col_lower for pat in getattr(self, "strict_types_exclude_patterns", [])):
                        text_enforced += 1
                        continue
                    if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
                        non_null = s.dropna()
                        if non_null.empty:
                            # Keep as-is; optionally fill when not preserving nulls
                            if not getattr(self, "preserve_nulls", True):
                                df_converted[col] = s.fillna("").astype(str)
                                text_enforced += 1
                            continue
                        # Detect presence of currency/symbols; if too prevalent, avoid coercion unless ratio is very high
                        str_vals = non_null.astype(str)
                        sym_ratio = str_vals.str.contains(r"[\$€£,]", regex=True).sum() / max(len(str_vals), 1)
                        cleaned = str_vals.str.replace(r"[^\d.\-]", "", regex=True)
                        to_num = pd.to_numeric(cleaned, errors="coerce")
                        ratio = (to_num.notna().sum() / max(len(non_null), 1)) if len(non_null) else 0.0
                        effective_threshold = max(numeric_ratio, 0.85) if sym_ratio >= 0.20 else numeric_ratio
                        if ratio >= effective_threshold:
                            # Coerce entire column to numeric (preserve nulls)
                            df_converted[col] = pd.to_numeric(
                                s.astype(str).str.replace(r"[^\d.\-]", "", regex=True), errors="coerce"
                            )
                            numeric_converted += 1
                        else:
                            # Enforce text type; preserve or fill nulls based on setting
                            if not getattr(self, "preserve_nulls", True):
                                df_converted[col] = s.fillna("").astype(str)
                            else:
                                df_converted[col] = s.astype("object")
                            text_enforced += 1
                try:
                    if numeric_converted or text_enforced:
                        logger.info(
                            f"Strict types enforced • numeric={numeric_converted} text={text_enforced} (threshold={numeric_ratio:.2f})"
                        )
                except Exception:
                    pass

            # Register the DataFrame as a table
            self.conn.register(table_name, df_converted)

            # Log available columns for debugging
            logger.debug(f"Available columns in table: {list(df_converted.columns)}")

            # Preprocess SQL for compatibility
            processed_sql = self._preprocess_sql(sql, table_name)

            # Handle LTRIM/TRIM on numeric columns by using string versions
            processed_sql = self._handle_string_functions_on_numeric(processed_sql, df_converted)
            # Handle LIKE on binary/BLOB and numeric columns
            if self.autocast_like:
                before_like = processed_sql
                processed_sql = self._handle_like_on_binary(processed_sql, df_converted)
                # Normalize any nested CAST left by earlier rewrites, including accidental 'CASTCAST('
                processed_sql = RedshiftSQLProcessor._normalize_casts_text(processed_sql)
                if processed_sql != before_like:
                    self._like_rewrite_pre += 1
                    logger.info("Auto-cast applied to LIKE expressions")

            logger.info(f"Processing {len(df):,} rows from Excel data")
            logger.debug(f"Processed SQL: {processed_sql[:500]}...")

            # Execute the query
            try:
                result = self.conn.execute(processed_sql).fetchdf()
            except Exception as exec_err:
                # If type-mismatch likely, try a permissive re-cast of CASE blocks and retry once
                err_text = str(exec_err)
                if getattr(self, "permissive", True) and any(
                    k in err_text.lower() for k in ["type mismatch", "could not convert", "cannot cast"]
                ):
                    case_pattern = re.compile(r"CASE\b.*?END", re.IGNORECASE | re.DOTALL)

                    def _wrap_case_retry(match):
                        block = match.group(0)
                        if not re.match(r"\s*CAST\s*\(", block, re.IGNORECASE):
                            return f"CAST({block} AS VARCHAR)"
                        return block

                    processed_sql_retry = processed_sql
                    prev_retry = None
                    max_iterations = 10
                    iterations = 0
                    while prev_retry != processed_sql_retry and iterations < max_iterations:
                        prev_retry = processed_sql_retry
                        processed_sql_retry = case_pattern.sub(_wrap_case_retry, processed_sql_retry)
                        iterations += 1
                    result = self.conn.execute(processed_sql_retry).fetchdf()
                elif (
                    self.autocast_like
                    and re.search(r"(?is)\b(?:I)?LIKE\b", processed_sql or "") is not None
                    and any(
                        k in err_text.lower() for k in ["like", "~~(", "syntax error", "parser error", "at or near"]
                    )
                ):
                    # Deterministic retry: map identifiers, then tokenize WHERE and rewrite LIKEs structurally
                    try:
                        mapped_for_retry = self._apply_column_mapping_to_sql(
                            processed_sql, getattr(self, "column_mapping", {})
                        )
                    except Exception:
                        mapped_for_retry = processed_sql

                    structured = self._rewrite_like_tokenized(mapped_for_retry)
                    structured = RedshiftSQLProcessor._normalize_casts_text(structured)
                    if structured != processed_sql:
                        self._like_rewrite_retry += 1
                        logger.info("Auto-cast retry applied to LIKE error (structured)")
                        # Optional parse probe
                        try:
                            self.conn.execute(f"EXPLAIN {structured}")
                        except Exception as pe:
                            # Fall back to helpful guidance if tokenizer produced invalid SQL (extremely unlikely)
                            msg = (
                                "Automatic LIKE auto-cast encountered a complex pattern. "
                                "Please CAST the non-literal side(s) to VARCHAR manually (e.g., CAST(col AS VARCHAR) LIKE '…')."
                            )
                            logger.info(f"Parse probe failed: {pe}")
                            raise Exception(msg)
                        # Attempt execution; on failure, provide clear manual CAST guidance
                        try:
                            result = self.conn.execute(structured).fetchdf()
                        except Exception:
                            msg = (
                                "Automatic LIKE auto-cast could not safely rewrite this query. "
                                "Please CAST the non-literal side(s) to VARCHAR manually (e.g., CAST(col AS VARCHAR) LIKE '…')."
                            )
                            raise Exception(msg)
                    else:
                        # No safe changes detected; guide user
                        msg = (
                            "Automatic LIKE auto-cast could not safely rewrite this query. "
                            "Please CAST the non-literal side(s) to VARCHAR manually (e.g., CAST(col AS VARCHAR) LIKE '…')."
                        )
                        logger.info(msg)
                        raise Exception(msg)
                elif getattr(self, "broader_casting", False) and re.search(r"(?i)\bUNION\b", processed_sql):
                    # Attempt UNION alignment for one or more unions
                    rewritten_all = self._rewrite_all_unions_to_varchar(processed_sql)
                    if rewritten_all and rewritten_all != processed_sql:
                        result = self.conn.execute(rewritten_all).fetchdf()
                    else:
                        raise
                else:
                    raise

            # Clean up result column names if needed
            if column_mapping:
                reverse_mapping = {v: k for k, v in column_mapping.items()}
                result_columns = []
                for col in result.columns:
                    if col in reverse_mapping:
                        result_columns.append(reverse_mapping[col])
                    else:
                        result_columns.append(col)
                result.columns = result_columns

            # Quiet telemetry report
            try:
                total_like_rewrites = self._like_rewrite_pre + self._like_rewrite_retry
                if total_like_rewrites > 0:
                    logger.info(
                        f"LIKE rewrites • pre={self._like_rewrite_pre} retry={self._like_rewrite_retry} total={total_like_rewrites}"
                    )
            except Exception:
                pass

            logger.info(f"✓ Query completed: {len(result):,} rows × {len(result.columns)} columns")

            # Unregister the table to free memory
            self.conn.unregister(table_name)

            return result

        except Exception as e:
            # Clean up on error
            try:
                self.conn.unregister(table_name)
            except Exception:
                pass
            error_msg = str(e)
            logger.error(f"❌ SQL Execution Failed: {error_msg}")

            # Extract column info from error for better messages
            df_converted = df.copy() if df is not None else None

            # Try to extract more helpful error information
            if "could not convert" in error_msg.lower() or "cannot cast" in error_msg.lower():
                logger.error(
                    "💡 Data type conversion error - check if numeric operations are being performed on text columns"
                )
                logger.info("💡 Common fix: Use CAST(column AS type) or check if columns contain non-numeric values")
            elif "no such column" in error_msg.lower() or "not found" in error_msg.lower():
                # Extract column name from error
                col_match = re.search(r"[Cc]olumn[:\s]+(['\"]?)(\w+)\1", error_msg)
                if not col_match:
                    col_match = re.search(r"[Rr]eference[:\s]+(['\"]?)(\w+)\1", error_msg)
                if not col_match:
                    # Try to extract from DuckDB specific error patterns
                    col_match = re.search(r"Binder Error: Referenced column \"(\w+)\"\s+not found", error_msg)
                    if not col_match:
                        col_match = re.search(r"column \"(\w+)\" must appear", error_msg)

                if col_match:
                    if col_match.lastindex == 2:
                        col_name = col_match.group(2)
                    else:
                        col_name = col_match.group(1)
                    logger.error(f"❌ Column '{col_name}' not found in the data")

                    # Check if this might be an original column name that was cleaned
                    if hasattr(self, "column_mapping"):
                        for orig, clean in self.column_mapping.items():
                            if col_name in orig or col_name.replace("_", " ") in orig:
                                logger.error("🔄 COLUMN NAME WAS CLEANED!")
                                logger.error(f"   Original: '{orig}'")
                                logger.error(f"   Use this: '{clean}'")
                                logger.error(f"   💡 Replace '{col_name}' with '{clean}' in your SQL query")
                                return

                    if df is not None:
                        available_cols = list(df_converted.columns) if "df_converted" in locals() else list(df.columns)

                        # Find close matches
                        close_matches = get_close_matches(
                            col_name.upper(), [col.upper() for col in available_cols], n=3, cutoff=0.6
                        )
                        if close_matches:
                            # Find the original case versions
                            suggestions = []
                            for match in close_matches:
                                for orig_col in available_cols:
                                    if orig_col.upper() == match:
                                        suggestions.append(orig_col)
                                        break

                            logger.error("💡 Did you mean one of these columns?")
                            for suggestion in suggestions:
                                logger.info(f"   → {suggestion}")

                        logger.info("\n📋 All available columns:")
                        # Group columns by first letter for easier reading
                        from itertools import groupby

                        sorted_cols = sorted(available_cols, key=str.upper)
                        for letter, group in groupby(sorted_cols, key=lambda x: x[0].upper()):
                            cols_in_group = list(group)
                            logger.info(f"   {letter}: {', '.join(cols_in_group)}")
                else:
                    # Could not extract column name
                    if df is not None:
                        available_cols = list(df.columns)
                        available_cols = [
                            col for col in available_cols if not (col.islower() and col.upper() in available_cols)
                        ]
                        available_cols = [col for col in available_cols if not col.endswith("_str")]
                        logger.info("📋 Available columns: " + ", ".join(available_cols[:15]))
                        if len(available_cols) > 15:
                            logger.info(f"   ... and {len(available_cols) - 15} more columns")
            elif "syntax error" in error_msg.lower():
                logger.error("💡 SQL syntax error - check for:")
                logger.info("   • Missing commas between columns")
                logger.info("   • Unclosed parentheses or quotes")
                logger.info("   • Invalid SQL keywords or functions")

                # Try to find the location of the syntax error
                line_match = re.search(r"LINE (\d+):", error_msg)
                if line_match:
                    line_num = int(line_match.group(1))
                    logger.info(f"   • Error appears to be around line {line_num} of your SQL")
            elif "regexp" in error_msg.lower():
                logger.error("💡 Regular expression error - check your pattern syntax")
                logger.info("💡 Note: DuckDB regex syntax may differ from PostgreSQL/Redshift")
            elif "duplicate" in error_msg.lower():
                logger.error("💡 Duplicate column name in output - use aliases (AS) for duplicate columns")
                # Try to extract the duplicate column name
                dup_match = re.search(r"duplicate column name[:\s]+(['\"]?)(\w+)\1", error_msg, re.IGNORECASE)
                if dup_match:
                    dup_col = dup_match.group(2)
                    logger.info(f"   • Column '{dup_col}' appears multiple times")
                    logger.info(f"   • Try: {dup_col} AS {dup_col}_1, {dup_col} AS {dup_col}_2, etc.")
            elif "type" in error_msg.lower() and "mismatch" in error_msg.lower():
                logger.error("💡 Data type mismatch - ensure all branches of CASE statements return the same type")
                logger.info("   • Use CAST() to convert values to the same type")
                logger.info("   • Example: CAST(column AS VARCHAR) or CAST(column AS DECIMAL)")

            # Show input data info
            if df is not None:
                logger.info(f"📊 Input data: {df.shape[0]} rows × {df.shape[1]} columns")

            # Show a sample of the processed SQL for debugging
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Processed SQL (first 500 chars):\n{sql[:500]}")

            raise Exception(f"SQL Error: {error_msg}") from e

    # Duplicate context manager/close methods removed; using the implementation
    # defined at the top of the class which safely closes and nulls the connection.


def process_sql_with_redshift_compatibility(df: pd.DataFrame, sql: str) -> pd.DataFrame:
    """
    Convenience function to process SQL with Redshift compatibility

    Args:
        df: Input DataFrame
        sql: SQL query with Redshift syntax

    Returns:
        pd.DataFrame: Query results
    """
    with RedshiftSQLProcessor() as processor:
        return processor.execute_sql(sql, df)


# -------------------------------------------------------------------------
# Module-level convenience alias for tools expecting execute_query()
def execute_query(
    sql: str, df: pd.DataFrame, table_name: str = "catalog_data"
) -> pd.DataFrame:  # pragma: no cover - thin alias
    return RedshiftSQLProcessor().execute_sql(sql, df, table_name)
