"""
SQL Query Execution and Dialect Translation

Handles SQL query execution and translation between different SQL dialects.
"""
import re
import logging
import duckdb
import pandas as pd
from typing import Optional
from enum import Enum
from dataclasses import dataclass
from neutron_utils.config import config

logger = logging.getLogger(__name__)


class SQLDialect(Enum):
    """Supported SQL dialects"""
    DUCKDB = "duckdb"
    REDSHIFT = "redshift"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"


@dataclass
class QueryResult:
    """Result of a SQL query execution"""
    data: Optional[pd.DataFrame]
    row_count: int
    column_names: list[str]
    execution_time_ms: float
    error: Optional[str] = None
    warnings: list[str] = None


def execute_sql(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    dialect: SQLDialect = SQLDialect.DUCKDB,
    limit: Optional[int] = None
) -> QueryResult:
    """
    Execute SQL in any dialect.

    Args:
        conn: DuckDB connection
        query: SQL query string
        dialect: SQL dialect to translate from
        limit: Optional row limit for sampling

    Returns:
        QueryResult with execution results
    """
    start_time = pd.Timestamp.now()
    warnings = []

    try:
        # Translate query based on dialect
        translated_query = translate_query(query, dialect)

        if limit:
            # Use TABLESAMPLE for random sampling when limit is applied
            translated_query = f"SELECT * FROM ({translated_query}) sq USING SAMPLE {limit} ROWS"

        # Execute query
        result = conn.execute(translated_query)
        df = result.fetchdf()

        execution_time = (pd.Timestamp.now() - start_time).total_seconds() * 1000

        return QueryResult(
            data=df,
            row_count=len(df),
            column_names=df.columns.tolist() if not df.empty else [],
            execution_time_ms=execution_time,
            warnings=warnings,
        )

    except Exception as e:
        execution_time = (pd.Timestamp.now() - start_time).total_seconds() * 1000
        # Enhanced error message with context
        error_msg = str(e)

        # Add helpful context based on error type
        if "Binder Error" in error_msg:
            if "Referenced column" in error_msg or "not found" in error_msg:
                error_msg = f"Column Error: {error_msg}\n\nTip: Check column names in the Columns panel. Use double quotes for names with spaces."
            elif "table" in error_msg.lower() and "not found" in error_msg.lower():
                error_msg = f"Table Error: {error_msg}\n\nTip: Make sure you've uploaded a file first. The table name is 'excel_file'."
        elif "Conversion Error" in error_msg or "Could not convert" in error_msg:
            error_msg = f"Type Mismatch: {error_msg}\n\nTip: Use CAST() to convert between types, e.g., CAST(column AS VARCHAR)"
        elif "unit" in error_msg.lower() and "count" in error_msg.lower():
            error_msg = f"Column Count Mismatch: {error_msg}\n\nTip: Check that all SELECT statements in UNION have the same number of columns."
        elif "division by zero" in error_msg.lower():
            error_msg = f"Division by Zero: {error_msg}\n\nTip: Use NULLIF to prevent division by zero: column / NULLIF(divisor, 0)"
        elif "Parser Error" in error_msg:
            error_msg = f"Syntax Error: {error_msg}\n\nTip: Check for missing commas, parentheses, or typos in SQL keywords."

        logger.error(f"Query execution failed: {error_msg}")
        return QueryResult(data=None, row_count=0, column_names=[], execution_time_ms=execution_time, error=error_msg)


def translate_query(query: str, dialect: SQLDialect) -> str:
    """
    Translate SQL from various dialects to DuckDB.

    This enables 'write once, run anywhere' SQL.

    Args:
        query: SQL query string
        dialect: Source SQL dialect

    Returns:
        Translated SQL compatible with DuckDB
    """
    # String hygiene: make TRIM/LTRIM/RTRIM tolerant of numeric args by casting to VARCHAR
    def _cast_trim(sql: str) -> str:
        try:
            if not bool(config.get("cast_trim_args", False)):
                return sql
            def _wrap_if_needed(expr: str) -> str:
                expr_stripped = expr.strip()
                low = expr_stripped.lower()
                # If already casted or contains explicit :: casts, don't wrap
                if 'cast(' in low or '::' in expr_stripped:
                    return expr_stripped
                return f"CAST({expr_stripped} AS VARCHAR)"

            # TRIM(LEADING|TRAILING|BOTH 'x' FROM expr)
            sql = re.sub(
                r"\btrim\s*\(\s*(leading|trailing|both)\s+('[^']*')\s+from\s+([^)]+?)\)",
                lambda m: f"TRIM({m.group(1)} {m.group(2)} FROM {_wrap_if_needed(m.group(3))})",
                sql,
                flags=re.IGNORECASE,
            )
            # TRIM(expr) where expr is not another TRIM style with FROM
            sql = re.sub(
                r"\btrim\s*\(\s*(?!leading\b|trailing\b|both\b)([^)]+?)\)",
                lambda m: f"TRIM({_wrap_if_needed(m.group(1))})",
                sql,
                flags=re.IGNORECASE,
            )
            # LTRIM/RTRIM: wrap first arg
            def _wrap_lr(m):
                func = m.group(1)
                arg1 = m.group(2)
                rest = m.group(3) or ""
                return f"{func}({_wrap_if_needed(arg1)}{rest})"
            sql = re.sub(
                r"\b(ltrim|rtrim)\s*\(\s*([^,()]+?)\s*(,\s*[^)]*)?\)",
                _wrap_lr,
                sql,
                flags=re.IGNORECASE,
            )
            return sql
        except Exception:
            return sql

    # Begin with optional trim-cast for all dialects
    translated = _cast_trim(query)

    # Numeric aggregates: wrap SUM/AVG arguments to tolerant numeric cast if enabled
    def _wrap_numeric_aggregates(sql: str) -> str:
        try:
            if not bool(config.get("auto_cast_numeric_aggregates", True)):
                return sql
            # Build wrapper for expression
            def _num_wrap(expr: str) -> str:
                s = expr.strip()
                low = s.lower()
                if 'try_cast' in low or 'cast(' in low or '::' in s:
                    return s
                # Remove non-numeric characters and cast to DOUBLE
                return f"TRY_CAST(regexp_replace({s}, '[^0-9.-]', '') AS DOUBLE)"

            # Replace sum(...) [over (...)] and avg(...)
            def _repl(m):
                func = m.group(1)
                inner = m.group(2)
                over = m.group(3) or ''
                return f"{func}({_num_wrap(inner)}){over}"

            # Note: this is a heuristic; avoids nested parentheses complexity
            pattern = r"\b(sum|avg)\s*\(\s*([^()]+?)\s*\)(\s*over\s*\([^)]*\))?"
            return re.sub(pattern, _repl, sql, flags=re.IGNORECASE)
        except Exception:
            return sql

    if dialect == SQLDialect.REDSHIFT:
        # Redshift -> DuckDB translations
        translated = translated.replace("GETDATE()", "CURRENT_TIMESTAMP")
        translated = translated.replace("DATEADD(", "DATEADD('")
        translated = translated.replace("DATEDIFF(", "DATEDIFF('")
        # NVL -> COALESCE (two-argument null coalescing)
        try:
            translated = re.sub(r"\bNVL\s*\(", "COALESCE(", translated, flags=re.IGNORECASE)
        except Exception:
            pass
        # Add more Redshift-specific translations
        try:
            translated = re.sub(
                r"\bNVL2\s*\(([^,]+),\s*([^,]+),\s*([^\)]+)\)",
                r"CASE WHEN \1 IS NOT NULL THEN \2 ELSE \3 END",
                translated,
                flags=re.IGNORECASE,
            )
        except Exception:
            pass

    elif dialect == SQLDialect.MYSQL:
        # MySQL -> DuckDB translations
        translated = translated.replace("NOW()", "CURRENT_TIMESTAMP")
        translated = translated.replace("CURDATE()", "CURRENT_DATE")
        # Add more MySQL-specific translations
        translated = re.sub(r"\bIFNULL\s*\(", "COALESCE(", translated, flags=re.IGNORECASE)
        try:
            translated = re.sub(
                r"\bIF\s*\(([^,]+),\s*([^,]+),\s*([^\)]+)\)",
                r"CASE WHEN \1 THEN \2 ELSE \3 END",
                translated,
                flags=re.IGNORECASE,
            )
        except Exception:
            pass

    elif dialect == SQLDialect.POSTGRESQL:
        # PostgreSQL -> DuckDB translations
        translated = translated.replace("::text", "::VARCHAR")
        translated = translated.replace("::jsonb", "::JSON")
        # Add more PostgreSQL-specific translations
        translated = re.sub(r"\bGENERATE_SERIES\b", "generate_series", translated, flags=re.IGNORECASE)

    elif dialect == SQLDialect.BIGQUERY:
        # BigQuery -> DuckDB translations
        translated = translated.replace("CURRENT_DATETIME()", "CURRENT_TIMESTAMP")
        # Add more BigQuery-specific translations
        translated = re.sub(r"\bSAFE_CAST\s*\(", "TRY_CAST(", translated, flags=re.IGNORECASE)

    # Apply numeric aggregate wrapping last
    translated = _wrap_numeric_aggregates(translated)

    return translated
