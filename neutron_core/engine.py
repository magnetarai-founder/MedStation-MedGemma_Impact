"""
Neutron Star Core Engine
The dumb core that always works - Excel + SQL + DuckDB = Results

This is the foundation that NEVER breaks, requires ZERO dependencies beyond DuckDB,
and works completely offline. All smart features are built on top of this.
"""

import os
import uuid
import re
import duckdb
import pandas as pd
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum
from neutron_utils.config import config, bootstrap_logging
from neutron_utils.excel_ops import ExcelReader
from neutron_utils.csv_ops import normalize_csv_to_temp

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
    column_names: List[str]
    execution_time_ms: float
    error: Optional[str] = None
    warnings: List[str] = None


class NeutronEngine:
    """
    The core SQL engine that powers everything.
    This is the dumb, reliable foundation that always works.
    """

    def __init__(self, memory_limit: Optional[str] = None):
        """Initialize the engine with DuckDB"""
        try:
            bootstrap_logging()
        except Exception:
            pass
        self.conn = duckdb.connect(":memory:")
        # Memory limit
        try:
            mem = memory_limit
            if not mem:
                mb = int(config.get("memory_limit_mb", 4096))
                mem = f"{mb}MB"
            self.conn.execute(f"SET memory_limit='{mem}'")
        except Exception as e:
            logger.debug(f"Could not set memory limit: {e}")
        # Threads + temp dir
        try:
            self.conn.execute("PRAGMA threads=system_threads();")
        except Exception:
            pass
        try:
            tmp = os.getenv("DATA_TOOL_TEMP_DIR") or config.get("temp_dir")
            if tmp:
                self.conn.execute(f"SET temp_directory='{tmp}'")
        except Exception as e:
            logger.debug(f"Could not set temp_directory: {e}")
        self.tables: Dict[str, str] = {}  # table_name -> file_path mapping
        self._setup_extensions()
        try:
            logger.info(
                "DuckDB configured • memory=%s threads=auto temp_dir=%s",
                mem if "mem" in locals() else "default",
                tmp if "tmp" in locals() else "default",
            )
        except Exception:
            pass

    def _setup_extensions(self):
        """Setup DuckDB extensions for Excel support"""
        try:
            self.conn.install_extension("excel")
            self.conn.load_extension("excel")
        except Exception as e:
            logger.warning(f"Excel extension not available, using pandas fallback: {e}")

    # ------------------------------
    # Type inference helpers
    # ------------------------------
    def _quote_ident(self, name: str) -> str:
        return '"' + str(name).replace('"', '""') + '"'

    def _should_infer_numeric(self, table: str, col: str, sample_rows: int, threshold: float) -> bool:
        """Decide if a VARCHAR column should be auto-cast to DOUBLE based on sample ratio.

        Uses a dynamic threshold if the column name suggests a numeric semantic.
        """
        colq = self._quote_ident(col)
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
            ratio = self.conn.execute(sql).fetchone()[0]
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

    def _auto_type_infer_table(self, table_name: str) -> None:
        """Attempt to auto-cast numeric-like VARCHAR columns to DOUBLE.

        This creates a typed shadow table and then replaces the original, so user SQL
        can 'just work' with SUM/AVG/etc. on numbers that were originally strings.
        """
        try:
            # Respect string-safe mode and explicit disable
            if bool(config.get("string_safe_mode", False)):
                return
            if not bool(config.get("auto_type_infer_on_load", False)):
                return
            # Read current column types
            cols = self.conn.execute(f"SELECT name, type FROM pragma_table_info('{table_name}')").fetchall()
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
                    if self._should_infer_numeric(table_name, name, sample_rows, threshold):
                        candidates.append(str(name))

            if not candidates:
                return

            # Build typed SELECT expressions
            select_exprs = []
            for name, ctype in cols:
                colq = self._quote_ident(name)
                if name in candidates:
                    expr = f"TRY_CAST(regexp_replace({colq}, '[^0-9.-]', '') AS DOUBLE) AS {colq}"
                else:
                    expr = f"{colq}"
                select_exprs.append(expr)

            typed_table = f"{table_name}__typed"
            sql_create = f"CREATE OR REPLACE TABLE {typed_table} AS SELECT {', '.join(select_exprs)} FROM {table_name}"
            self.conn.execute(sql_create)
            # Swap in place (handle view or table)
            self.conn.execute(f"DROP VIEW IF EXISTS {table_name}")
            self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            self.conn.execute(f"ALTER TABLE {typed_table} RENAME TO {table_name}")

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

    def load_excel(
        self,
        file_path: Union[str, Path],
        table_name: str = "excel_file",
        sheet_name: Optional[str] = None,
    ) -> QueryResult:
        """
        Load an Excel file into the engine.
        This is the core 'Excel → SQL' magic.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return QueryResult(
                data=None, row_count=0, column_names=[], execution_time_ms=0, error=f"File not found: {file_path}"
            )

        start_time = pd.Timestamp.now()

        # Prefer safer pandas path first unless explicitly configured to try DuckDB Excel
        prefer_duckdb_excel = bool(config.get("prefer_duckdb_excel", False))
        if prefer_duckdb_excel:
            try:
                # Try direct Excel loading with DuckDB
                sheet = sheet_name or config.get("excel_sheet_name")
                if sheet:
                    safe_sheet = str(sheet).replace("'", "''")
                    sql = f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_excel('{file_path}', sheet='{safe_sheet}')"
                else:
                    sql = f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_excel('{file_path}')"
                self.conn.execute(sql)

                # Get metadata
                result = self.conn.execute(f"SELECT COUNT(*) as cnt FROM {table_name}").fetchone()
                row_count = result[0]

                columns = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
                column_names = [col[0] for col in columns]

                # Friendly empty check
                if row_count == 0 or len(column_names) == 0:
                    return QueryResult(
                        data=None,
                        row_count=0,
                        column_names=[],
                        execution_time_ms=(pd.Timestamp.now() - start_time).total_seconds() * 1000,
                        error="The Excel file appears to be empty (no rows/columns).",
                    )

                # Clean column names
                from neutron_utils.sql_utils import ColumnNameCleaner
                cleaned_columns = []
                rename_sql_parts = []
                for col in column_names:
                    cleaned = ColumnNameCleaner.clean_column_name(col)
                    cleaned_columns.append(cleaned)
                    if cleaned != col:
                        # Need to quote both original and new names
                        rename_sql_parts.append(f'"{col}" TO "{cleaned}"')
                
                # Rename columns if needed
                if rename_sql_parts:
                    rename_sql = f"ALTER TABLE {table_name} RENAME COLUMN " + ", RENAME COLUMN ".join(rename_sql_parts)
                    self.conn.execute(rename_sql)
                
                self.tables[table_name] = str(file_path)

                # Optional type inference to improve UX
                self._auto_type_infer_table(table_name)

                execution_time = (pd.Timestamp.now() - start_time).total_seconds() * 1000

                return QueryResult(
                    data=None,  # Don't load full data on file load
                    row_count=row_count,
                    column_names=column_names,
                    execution_time_ms=execution_time,
                )

            except Exception as e:
                # Log and continue to pandas/streaming path
                logger.info("Falling back to pandas for Excel reading")
                try:
                    logger.debug("DuckDB read_excel error: %s", e)
                except Exception:
                    pass
        # Safer path: pandas (optionally stream) with all columns as text
        # Decide whether to stream to CSV based on file size
        try:
            file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        except Exception:
            file_size_mb = 0

        threshold = float(config.get("excel_stream_to_csv_threshold_mb", 100))

        if file_size_mb >= threshold:
            # Stream Excel -> temp CSV -> DuckDB
            try:
                tmp_csv = Path(file_path).with_name(
                    f"{Path(file_path).stem}__ns_{uuid.uuid4().hex[:8]}.csv"
                )
                first = True
                total_rows = 0
                chunk_size = int(config.get("excel_chunk_size", 5000))
                for chunk in ExcelReader.read_excel_chunked(
                    str(file_path),
                    sheet_name=sheet_name or config.get("excel_sheet_name"),
                    chunk_size=chunk_size,
                    dtype=str,
                ):
                    total_rows += len(chunk)
                    chunk.to_csv(tmp_csv, index=False, header=first, mode="w" if first else "a")
                    first = False
                # Load from CSV
                sql = (
                    f"CREATE OR REPLACE TABLE {table_name} AS "
                    f"SELECT * FROM read_csv_auto('{tmp_csv}', header=True, ALL_VARCHAR=TRUE)"
                )
                self.conn.execute(sql)
                # Column names
                columns = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
                column_names = [c[0] for c in columns]
                
                # Clean column names
                from neutron_utils.sql_utils import ColumnNameCleaner
                cleaned_columns = []
                rename_sql_parts = []
                for col in column_names:
                    cleaned = ColumnNameCleaner.clean_column_name(col)
                    cleaned_columns.append(cleaned)
                    if cleaned != col:
                        rename_sql_parts.append(f'"{col}" TO "{cleaned}"')
                
                # Rename columns if needed
                if rename_sql_parts:
                    rename_sql = f"ALTER TABLE {table_name} RENAME COLUMN " + ", RENAME COLUMN ".join(rename_sql_parts)
                    self.conn.execute(rename_sql)
                    column_names = cleaned_columns
                
                # Cleanup temp CSV
                try:
                    tmp_csv.unlink()
                except Exception:
                    pass

                self.tables[table_name] = str(file_path)
                # Optional type inference
                self._auto_type_infer_table(table_name)
                execution_time = (pd.Timestamp.now() - start_time).total_seconds() * 1000
                return QueryResult(
                    data=None,
                    row_count=total_rows,
                    column_names=column_names,
                    execution_time_ms=execution_time,
                )
            except Exception as stream_err:
                # Fall through to non-streaming pandas path
                try:
                    logger.debug("Excel stream-to-CSV failed: %s", stream_err)
                except Exception:
                    pass

        # Non-streaming pandas path
        try:
            sheet = sheet_name or config.get("excel_sheet_name")
            # Force all columns to text to preserve leading zeros and avoid cast errors
            if sheet:
                df = pd.read_excel(file_path, sheet_name=sheet, dtype=str)
            else:
                df = pd.read_excel(file_path, dtype=str)
            # Friendly empty check (headers-only or no columns)
            if df is None or df.shape[1] == 0 or df.shape[0] == 0:
                return QueryResult(
                    data=None,
                    row_count=0,
                    column_names=[],
                    execution_time_ms=(pd.Timestamp.now() - start_time).total_seconds() * 1000,
                    error="The Excel file appears to be empty (no rows/columns).",
                )

            # Clean column names while preserving case
            from neutron_utils.sql_utils import ColumnNameCleaner
            df = ColumnNameCleaner.clean_dataframe_columns(df)
            
            self.conn.register(table_name, df)
            self.tables[table_name] = str(file_path)

            # Optional type inference
            self._auto_type_infer_table(table_name)

            execution_time = (pd.Timestamp.now() - start_time).total_seconds() * 1000

            return QueryResult(
                data=None, row_count=len(df), column_names=df.columns.tolist(), execution_time_ms=execution_time
            )
        except Exception as pandas_error:
            return QueryResult(
                data=None,
                row_count=0,
                column_names=[],
                execution_time_ms=0,
                error=(
                    "The file appears to be corrupted or not a valid Excel workbook."
                    if any(
                        x in str(pandas_error)
                        for x in [
                            "BadZipFile",
                            "bad zip file",
                            "not a zip file",
                            "Excel file format cannot be determined",
                            "format cannot be determined",
                        ]
                    )
                    else f"Failed to load Excel: {str(pandas_error)}"
                ),
            )
        # Absolute safety net: should never reach here
        return QueryResult(
            data=None,
            row_count=0,
            column_names=[],
            execution_time_ms=(pd.Timestamp.now() - start_time).total_seconds() * 1000,
            error="Unknown error while loading Excel",
        )

    def load_csv(self, file_path: Union[str, Path], table_name: str = "excel_file") -> QueryResult:
        """
        Load a CSV file into the engine in a robust, text-first way.
        Default: pandas first with dtype=str (more forgiving), then DuckDB.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return QueryResult(
                data=None,
                row_count=0,
                column_names=[],
                execution_time_ms=0,
                error=f"File not found: {file_path}",
            )

        start_time = pd.Timestamp.now()

        prefer_pandas_csv = bool(config.get("prefer_pandas_csv", True))
        if prefer_pandas_csv:
            try:
                encoding = config.get("csv_encoding", "utf-8")
                # Robust parsing: python engine for better sniffing, sep=None to auto-detect,
                # dtype=str to keep everything as text; do NOT skip lines.
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    dtype=str,
                    engine="python",
                    sep=None,
                    on_bad_lines="error",
                    low_memory=False,
                    keep_default_na=False,
                )
                if df is None or df.shape[1] == 0 or df.shape[0] == 0:
                    return QueryResult(
                        data=None,
                        row_count=0,
                        column_names=[],
                        execution_time_ms=(pd.Timestamp.now() - start_time).total_seconds() * 1000,
                        error="The CSV file appears to be empty (no rows/columns).",
                    )
                # Clean column names while preserving case
                from neutron_utils.sql_utils import ColumnNameCleaner
                df = ColumnNameCleaner.clean_dataframe_columns(df)
                
                self.conn.register(table_name, df)
                self.tables[table_name] = str(file_path)

                # Optional type inference
                self._auto_type_infer_table(table_name)

                execution_time = (pd.Timestamp.now() - start_time).total_seconds() * 1000
                return QueryResult(
                    data=None,
                    row_count=len(df),
                    column_names=df.columns.tolist(),
                    execution_time_ms=execution_time,
                )
            except Exception as pandas_first_err:
                # Fall through to DuckDB reader
                try:
                    logger.debug("Pandas CSV read failed, trying DuckDB: %s", pandas_first_err)
                except Exception:
                    pass
                # Normalize CSV to preserve row/column counts, then ingest
                try:
                    norm_path, _ = normalize_csv_to_temp(file_path, encoding=encoding)
                    sql = (
                        f"CREATE OR REPLACE TABLE {table_name} AS "
                        f"SELECT * FROM read_csv_auto('{norm_path}', header=True, ALL_VARCHAR=TRUE)"
                    )
                    self.conn.execute(sql)
                    # Metadata
                    row_count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    columns = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
                    column_names = [col[0] for col in columns]
                    self.tables[table_name] = str(file_path)
                    # Optional type inference
                    self._auto_type_infer_table(table_name)
                    try:
                        Path(norm_path).unlink()
                    except Exception:
                        pass
                    execution_time = (pd.Timestamp.now() - start_time).total_seconds() * 1000
                    return QueryResult(
                        data=None,
                        row_count=row_count,
                        column_names=column_names,
                        execution_time_ms=execution_time,
                    )
                except Exception as norm_err:
                    try:
                        logger.debug("CSV normalization + DuckDB ingest failed: %s", norm_err)
                    except Exception:
                        pass

        try:
            # DuckDB path with ALL_VARCHAR for safety
            sql = (
                f"CREATE OR REPLACE TABLE {table_name} AS "
                f"SELECT * FROM read_csv_auto('{file_path}', header=True, ALL_VARCHAR=TRUE)"
            )
            self.conn.execute(sql)

            # Metadata
            row_count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            columns = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
            column_names = [col[0] for col in columns]

            if row_count == 0 or len(column_names) == 0:
                return QueryResult(
                    data=None,
                    row_count=0,
                    column_names=[],
                    execution_time_ms=(pd.Timestamp.now() - start_time).total_seconds() * 1000,
                    error="The CSV file appears to be empty (no rows/columns).",
                )

            # Clean column names
            from neutron_utils.sql_utils import ColumnNameCleaner
            cleaned_columns = []
            rename_sql_parts = []
            for col in column_names:
                cleaned = ColumnNameCleaner.clean_column_name(col)
                cleaned_columns.append(cleaned)
                if cleaned != col:
                    rename_sql_parts.append(f'"{col}" TO "{cleaned}"')
            
            # Rename columns if needed
            if rename_sql_parts:
                rename_sql = f"ALTER TABLE {table_name} RENAME COLUMN " + ", RENAME COLUMN ".join(rename_sql_parts)
                self.conn.execute(rename_sql)
                column_names = cleaned_columns
            
            self.tables[table_name] = str(file_path)
            # Optional type inference
            self._auto_type_infer_table(table_name)
            execution_time = (pd.Timestamp.now() - start_time).total_seconds() * 1000
            return QueryResult(
                data=None,
                row_count=row_count,
                column_names=column_names,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            # Final fallback to pandas if DuckDB CSV read fails
            logger.info("Falling back to pandas for CSV reading")
            try:
                logger.debug("DuckDB read_csv_auto error: %s", e)
            except Exception:
                pass
            try:
                encoding = config.get("csv_encoding", "utf-8")
                norm_path, _ = normalize_csv_to_temp(file_path, encoding=encoding)
                sql = (
                    f"CREATE OR REPLACE TABLE {table_name} AS "
                    f"SELECT * FROM read_csv_auto('{norm_path}', header=True, ALL_VARCHAR=TRUE)"
                )
                self.conn.execute(sql)
                row_count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                columns = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
                column_names = [col[0] for col in columns]
                self.tables[table_name] = str(file_path)
                try:
                    Path(norm_path).unlink()
                except Exception:
                    pass
                execution_time = (pd.Timestamp.now() - start_time).total_seconds() * 1000
                return QueryResult(
                    data=None,
                    row_count=row_count,
                    column_names=column_names,
                    execution_time_ms=execution_time,
                )
            except Exception as pandas_error:
                return QueryResult(
                    data=None,
                    row_count=0,
                    column_names=[],
                    execution_time_ms=0,
                    error=f"Failed to load CSV: {str(pandas_error)}",
                )

    def execute_sql(
        self, query: str, dialect: SQLDialect = SQLDialect.DUCKDB, limit: Optional[int] = None
    ) -> QueryResult:
        """
        Execute SQL in any dialect. This is where the magic happens.
        DuckDB handles the heavy lifting, we just translate dialects.
        """
        start_time = pd.Timestamp.now()
        warnings = []

        try:
            # Translate query based on dialect
            translated_query = self._translate_query(query, dialect)

            if limit:
                translated_query = f"SELECT * FROM ({translated_query}) sq LIMIT {limit}"

            # Execute query
            result = self.conn.execute(translated_query)
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
            return QueryResult(data=None, row_count=0, column_names=[], execution_time_ms=execution_time, error=str(e))

    def _translate_query(self, query: str, dialect: SQLDialect) -> str:
        """
        Translate SQL from various dialects to DuckDB.
        This enables 'write once, run anywhere' SQL.
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

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a loaded table"""
        if table_name not in self.tables:
            return {"error": f"Table '{table_name}' not found"}

        try:
            # Get column info
            columns = self.conn.execute(f"DESCRIBE {table_name}").fetchall()

            # Get row count
            row_count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

            # Get sample data (JSON safe)
            sample = self.conn.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchdf()
            try:
                from neutron_utils.json_utils import df_to_jsonsafe_records
                sample_records = df_to_jsonsafe_records(sample)
            except Exception:
                sample_records = sample.where(pd.notna(sample), None).to_dict("records")

            return {
                "table_name": table_name,
                "file_path": self.tables[table_name],
                "row_count": row_count,
                "columns": [{"name": col[0], "type": col[1]} for col in columns],
                "sample_data": sample_records,
            }
        except Exception as e:
            return {"error": str(e)}

    def export_results(self, query_result: QueryResult, output_path: Union[str, Path], format: str = "excel") -> bool:
        """Export query results to file"""
        if query_result.error or query_result.data is None:
            return False

        output_path = Path(output_path)

        try:
            if format == "excel":
                query_result.data.to_excel(output_path, index=False)
            elif format == "csv":
                query_result.data.to_csv(output_path, index=False)
            elif format == "parquet":
                query_result.data.to_parquet(output_path, index=False)
            else:
                raise ValueError(f"Unsupported format: {format}")

            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def close(self):
        """Close the DuckDB connection"""
        self.conn.close()


# Singleton instance for easy access
_engine_instance: Optional[NeutronEngine] = None


def get_engine() -> NeutronEngine:
    """Get or create the singleton engine instance"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = NeutronEngine()
    return _engine_instance
