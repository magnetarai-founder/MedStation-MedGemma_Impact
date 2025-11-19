"""
File Loading for Excel and CSV

Handles loading Excel and CSV files into DuckDB with robust error handling,
streaming support for large files, and automatic type inference.

This module contains the "Excel → SQL" magic that is core to Neutron's value proposition.
"""
import os
import uuid
import logging
import duckdb
import pandas as pd
from typing import Dict, Union, Optional
from pathlib import Path
from neutron_utils.config import config
from neutron_utils.excel_ops import ExcelReader
from neutron_utils.csv_ops import normalize_csv_to_temp
from .query_executor import QueryResult
from .type_mapper import auto_type_infer_table

logger = logging.getLogger(__name__)


def load_excel(
    conn: duckdb.DuckDBPyConnection,
    tables: Dict[str, str],
    file_path: Union[str, Path],
    table_name: str = "excel_file",
    sheet_name: Optional[str] = None,
) -> QueryResult:
    """
    Load an Excel file into the engine.

    This is the core 'Excel → SQL' magic.

    Args:
        conn: DuckDB connection
        tables: Table registry dict (will be updated)
        file_path: Path to Excel file
        table_name: Name for the table
        sheet_name: Optional sheet name

    Returns:
        QueryResult with load status
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
            conn.execute(sql)

            # Get metadata
            result = conn.execute(f"SELECT COUNT(*) as cnt FROM {table_name}").fetchone()
            row_count = result[0]

            columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
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
                conn.execute(rename_sql)

            tables[table_name] = str(file_path)

            # Optional type inference to improve UX
            auto_type_infer_table(conn, table_name)

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
            conn.execute(sql)
            # Column names
            columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
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
                conn.execute(rename_sql)
                column_names = cleaned_columns

            # Cleanup temp CSV
            try:
                tmp_csv.unlink()
            except Exception:
                pass

            tables[table_name] = str(file_path)
            # Optional type inference
            auto_type_infer_table(conn, table_name)
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

        conn.register(table_name, df)
        tables[table_name] = str(file_path)

        # Optional type inference
        auto_type_infer_table(conn, table_name)

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


def load_csv(
    conn: duckdb.DuckDBPyConnection,
    tables: Dict[str, str],
    file_path: Union[str, Path],
    table_name: str = "excel_file"
) -> QueryResult:
    """
    Load a CSV file into the engine in a robust, text-first way.

    Default: pandas first with dtype=str (more forgiving), then DuckDB.

    Args:
        conn: DuckDB connection
        tables: Table registry dict (will be updated)
        file_path: Path to CSV file
        table_name: Name for the table

    Returns:
        QueryResult with load status
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

            conn.register(table_name, df)
            tables[table_name] = str(file_path)

            # Optional type inference
            auto_type_infer_table(conn, table_name)

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
                encoding = config.get("csv_encoding", "utf-8")
                norm_path, _ = normalize_csv_to_temp(file_path, encoding=encoding)
                sql = (
                    f"CREATE OR REPLACE TABLE {table_name} AS "
                    f"SELECT * FROM read_csv_auto('{norm_path}', header=True, ALL_VARCHAR=TRUE)"
                )
                conn.execute(sql)
                # Metadata
                row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
                column_names = [col[0] for col in columns]
                tables[table_name] = str(file_path)
                # Optional type inference
                auto_type_infer_table(conn, table_name)
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
        conn.execute(sql)

        # Metadata
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
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
            conn.execute(rename_sql)
            column_names = cleaned_columns

        tables[table_name] = str(file_path)
        # Optional type inference
        auto_type_infer_table(conn, table_name)
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
            conn.execute(sql)
            row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
            column_names = [col[0] for col in columns]
            tables[table_name] = str(file_path)
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
