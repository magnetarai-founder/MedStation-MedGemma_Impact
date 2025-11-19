"""
Type Mapping and Inference

Handles DuckDB type inference and automatic type casting for VARCHAR columns
that contain numeric data.
"""
import re
import logging
import duckdb
from neutron_utils.config import config

logger = logging.getLogger(__name__)


def quote_identifier(name: str) -> str:
    """
    Quote a SQL identifier for safe use in queries.

    Args:
        name: Identifier to quote

    Returns:
        Quoted identifier
    """
    return '"' + str(name).replace('"', '""') + '"'


def should_infer_numeric(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    col: str,
    sample_rows: int,
    threshold: float
) -> bool:
    """
    Decide if a VARCHAR column should be auto-cast to DOUBLE based on sample ratio.

    Uses a dynamic threshold if the column name suggests a numeric semantic.

    Args:
        conn: DuckDB connection
        table: Table name
        col: Column name
        sample_rows: Number of rows to sample (0 for all)
        threshold: Minimum ratio of numeric values required

    Returns:
        True if column should be cast to numeric
    """
    colq = quote_identifier(col)
    limit_clause = f" LIMIT {sample_rows}" if sample_rows and sample_rows > 0 else ""
    # Remove non-numeric chars and try cast to DOUBLE
    sql = (
        f"SELECT COALESCE("
        f"  CAST(SUM(CASE WHEN TRY_CAST(regexp_replace({colq}, '[^0-9.-]', '') AS DOUBLE) IS NOT NULL THEN 1 ELSE 0 END) AS DOUBLE) / "
        f"  NULLIF(SUM(CASE WHEN {colq} IS NOT NULL AND LENGTH(TRIM({colq}))>0 THEN 1 ELSE 0 END), 0),"
        f"  0"
        f") FROM {table}{limit_clause}"
    )
    try:
        ratio = conn.execute(sql).fetchone()[0]
        if ratio is None:
            return False
        ratio = float(ratio)
        # Lower threshold for common numeric-like names
        try:
            prefer_pats = [re.compile(p, re.IGNORECASE) for p in (config.get("prefer_numeric_patterns") or [])]
        except Exception:
            prefer_pats = []
        lower_thresh = 0.3 if any(p.search(col) for p in prefer_pats) else threshold
        return ratio >= float(lower_thresh)
    except Exception as e:
        try:
            logger.debug("Type inference ratio calc failed for %s.%s: %s", table, col, e)
        except Exception:
            pass
        return False


def auto_type_infer_table(conn: duckdb.DuckDBPyConnection, table_name: str) -> None:
    """
    Attempt to auto-cast numeric-like VARCHAR columns to DOUBLE.

    This creates a typed shadow table and then replaces the original, so user SQL
    can 'just work' with SUM/AVG/etc. on numbers that were originally strings.

    Args:
        conn: DuckDB connection
        table_name: Name of table to infer types for
    """
    try:
        # Respect string-safe mode and explicit disable
        if bool(config.get("string_safe_mode", False)):
            return
        if not bool(config.get("auto_type_infer_on_load", False)):
            return
        # Read current column types
        cols = conn.execute(f"SELECT name, type FROM pragma_table_info('{table_name}')").fetchall()
        if not cols:
            return
        # Decide candidates (VARCHAR-like only)
        threshold = float(config.get("strict_type_numeric_ratio", 0.7))
        sample_rows = int(config.get("type_infer_sample_rows", 50000))
        # Respect excludes
        excludes = set(config.get("strict_types_exclude", []) or [])
        exclude_patterns = [re.compile(pat, re.IGNORECASE) for pat in (config.get("strict_types_exclude_patterns", []) or [])]

        def is_excluded(cn: str) -> bool:
            if cn in excludes:
                return True
            for pat in exclude_patterns:
                if pat.search(cn):
                    return True
            return False

        candidates = []
        for name, ctype in cols:
            if is_excluded(str(name)):
                continue
            t = str(ctype or "").upper()
            if t in ("VARCHAR", "STRING", "TEXT", "UNKNOWN"):
                if should_infer_numeric(conn, table_name, name, sample_rows, threshold):
                    candidates.append(str(name))

        if not candidates:
            return

        # Build typed SELECT expressions
        select_exprs = []
        for name, ctype in cols:
            colq = quote_identifier(name)
            if name in candidates:
                expr = f"TRY_CAST(regexp_replace({colq}, '[^0-9.-]', '') AS DOUBLE) AS {colq}"
            else:
                expr = f"{colq}"
            select_exprs.append(expr)

        typed_table = f"{table_name}__typed"
        sql_create = f"CREATE OR REPLACE TABLE {typed_table} AS SELECT {', '.join(select_exprs)} FROM {table_name}"
        conn.execute(sql_create)
        # Swap in place (handle view or table)
        conn.execute(f"DROP VIEW IF EXISTS {table_name}")
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.execute(f"ALTER TABLE {typed_table} RENAME TO {table_name}")

        try:
            logger.info("Auto-typed %d column(s) to DOUBLE in %s", len(candidates), table_name)
        except Exception:
            pass
    except Exception as e:
        # Non-fatal; better to succeed with original strings than to fail load
        try:
            logger.debug("Auto type inference failed for %s: %s", table_name, e)
        except Exception:
            pass
