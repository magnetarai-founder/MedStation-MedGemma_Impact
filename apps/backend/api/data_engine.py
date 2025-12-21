#!/usr/bin/env python3
"""
ElohimOS Data Engine
Complete data pipeline: Excel/JSON → Auto-Clean → SQLite → Query Generation

Features:
- Auto-clean uploaded files
- Load into SQLite with WAL mode
- Brute-force schema discovery
- Natural language to SQL generation
- Multi-tier query assistance
"""

import pandas as pd
import sqlite3
import json
import hashlib
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, UTC
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from utils import sanitize_for_log
from metrics import get_metrics
from api.security.sql_safety import quote_identifier

logger = logging.getLogger(__name__)
metrics = get_metrics()

# MED-02: Compile frequently-used regex patterns once at module load
_COLUMN_NAME_SPECIAL_CHARS = re.compile(r'[^\w\s]')
_COLUMN_NAME_WHITESPACE = re.compile(r'\s+')
_TABLE_NAME_VALIDATOR = re.compile(r'^[a-zA-Z0-9_]+$')

# Metal 4 integration for parallel SQL operations
try:
    from api.metal4_engine import get_metal4_engine
    _metal4_engine = get_metal4_engine()
    if _metal4_engine.is_available():
        logger.info("✅ Metal 4 tick flow enabled for SQL operations")
except ImportError:
    _metal4_engine = None
    logger.info("⚠️  Metal 4 not available - using CPU for SQL")

# Storage path
from config_paths import get_config_paths
DATA_DIR = get_config_paths().datasets_dir
DATA_DIR.mkdir(parents=True, exist_ok=True)


class DataEngine:
    """
    Complete data pipeline engine
    - Auto-cleans Excel/JSON/CSV
    - Loads into SQLite (not DuckDB)
    - Provides schema discovery
    - Brute-force query generation
    """

    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = DATA_DIR / "datasets.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # SQLite connection with WAL mode
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0,
            isolation_level='DEFERRED'
        )
        self.conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrent access
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA mmap_size=30000000000")

        # Thread lock for write operations
        self._write_lock = threading.Lock()

        self._setup_metadata()

        logger.info(f"✅ Data Engine initialized: {self.db_path}")

    def _setup_metadata(self):
        """Store metadata about uploaded datasets"""
        with self._write_lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS dataset_metadata (
                    dataset_id TEXT PRIMARY KEY,
                    original_filename TEXT,
                    table_name TEXT UNIQUE,
                    upload_timestamp TEXT,
                    row_count INTEGER,
                    column_count INTEGER,
                    schema_json TEXT,
                    file_hash TEXT,
                    file_type TEXT,
                    session_id TEXT
                )
            """)

            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_session
                ON dataset_metadata(session_id)
            """)

            self.conn.commit()

    def upload_and_load(
        self,
        file_path: Path,
        filename: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload Excel/JSON/CSV and load into SQLite

        Args:
            file_path: Path to file
            filename: Original filename
            session_id: Optional session ID to associate dataset with

        Returns:
            {
                'dataset_id': '...',
                'table_name': '...',
                'rows': 1000,
                'columns': ['col1', 'col2', ...],
                'schema': {col: dtype, ...},
                'preview': [...first 5 rows...],
                'query_suggestions': [...]
            }
        """
        # METRICS: Track file upload operation
        with metrics.track("data_upload"):
            # 1. Read file based on type
            file_ext = file_path.suffix.lower()

            try:
                if file_ext in ['.xlsx', '.xls']:
                    df = pd.read_excel(file_path)
                elif file_ext == '.json':
                    df = pd.read_json(file_path)
                elif file_ext == '.csv':
                    df = pd.read_csv(file_path)
                else:
                    raise ValueError(f"Unsupported file type: {file_ext}")
            except Exception as e:
                safe_filename = sanitize_for_log(filename)
                logger.error(f"Failed to read file {safe_filename}: {e}")
                metrics.increment_error("data_upload")
                raise

        # 2. Auto-clean
        df = self._auto_clean(df)

        # 3. Generate unique table name
        file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()[:8]
        table_name = f"ds_{file_hash}"
        dataset_id = f"dataset_{file_hash}"

        # 4. Load into SQLite
        with self._write_lock:
            df.to_sql(table_name, self.conn, if_exists='replace', index=False)

        # 5. Store metadata
        schema = {col: str(dtype) for col, dtype in df.dtypes.items()}

        with self._write_lock:
            self.conn.execute("""
                INSERT OR REPLACE INTO dataset_metadata
                (dataset_id, original_filename, table_name, upload_timestamp,
                 row_count, column_count, schema_json, file_hash, file_type, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dataset_id,
                filename,
                table_name,
                datetime.now(UTC).isoformat(),
                len(df),
                len(df.columns),
                json.dumps(schema),
                file_hash,
                file_ext,
                session_id
            ))
            self.conn.commit()

        safe_filename = sanitize_for_log(filename)
        logger.info(f"✅ Loaded {safe_filename} → {table_name} ({len(df)} rows, {len(df.columns)} cols)")

        # 6. Generate query suggestions using brute-force discovery
        query_suggestions = self._brute_force_discover(table_name, df)

        return {
            'dataset_id': dataset_id,
            'table_name': table_name,
            'rows': len(df),
            'columns': list(df.columns),
            'schema': schema,
            'preview': df.head(5).to_dict('records'),
            'query_suggestions': query_suggestions
        }

    def _auto_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Auto-clean dataframe"""
        # Remove duplicate columns
        df = df.loc[:, ~df.columns.duplicated()]

        # Remove completely empty rows/columns
        df = df.dropna(how='all', axis=0)
        df = df.dropna(how='all', axis=1)

        # Clean column names (SQL-safe)
        df.columns = [self._sanitize_column_name(col) for col in df.columns]

        # Infer and convert dtypes
        for col in df.columns:
            df[col] = self._infer_and_convert(df[col])

        return df

    def _sanitize_column_name(self, name: str) -> str:
        """Make column name SQL-safe"""
        # Replace spaces and special chars with underscores
        # MED-02: Use pre-compiled regex patterns
        name = _COLUMN_NAME_SPECIAL_CHARS.sub('_', str(name))
        name = _COLUMN_NAME_WHITESPACE.sub('_', name)
        # Remove leading/trailing underscores
        name = name.strip('_')
        # Ensure it doesn't start with a number
        if name and name[0].isdigit():
            name = f'col_{name}'
        return name or 'unnamed'

    def _infer_and_convert(self, series: pd.Series) -> pd.Series:
        """Infer and convert column dtype"""
        # Try numeric first
        try:
            return pd.to_numeric(series, errors='raise')
        except (ValueError, TypeError):
            pass

        # Try datetime
        try:
            return pd.to_datetime(series, errors='raise')
        except (ValueError, TypeError):
            pass

        # Default to string
        return series.astype(str)

    def _brute_force_discover(self, table_name: str, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Brute-force schema discovery
        Concurrently run broad queries to discover what data looks like

        Returns list of query suggestions with metadata
        """
        suggestions = []

        # 1. Basic aggregations for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        for col in numeric_cols[:5]:  # Limit to first 5
            suggestions.append({
                'query': f'SELECT AVG("{col}") as avg_{col}, MIN("{col}") as min_{col}, MAX("{col}") as max_{col} FROM {table_name}',
                'description': f'Statistics for {col}',
                'category': 'aggregate',
                'confidence': 0.9
            })

        # 2. Top values for categorical columns
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        for col in categorical_cols[:5]:
            suggestions.append({
                'query': f'SELECT "{col}", COUNT(*) as count FROM {table_name} GROUP BY "{col}" ORDER BY count DESC LIMIT 10',
                'description': f'Top 10 {col} values',
                'category': 'distribution',
                'confidence': 0.85
            })

        # 3. Time-based analysis if datetime columns exist
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        for col in datetime_cols[:3]:
            suggestions.append({
                'query': f'SELECT DATE("{col}") as date, COUNT(*) as count FROM {table_name} GROUP BY DATE("{col}") ORDER BY date',
                'description': f'Daily distribution by {col}',
                'category': 'temporal',
                'confidence': 0.8
            })

        # 4. Correlation discovery (numeric pairs)
        if len(numeric_cols) >= 2:
            for i, col1 in enumerate(numeric_cols[:3]):
                for col2 in numeric_cols[i+1:4]:
                    suggestions.append({
                        'query': f'SELECT "{col1}", "{col2}" FROM {table_name} WHERE "{col1}" IS NOT NULL AND "{col2}" IS NOT NULL LIMIT 100',
                        'description': f'Correlation between {col1} and {col2}',
                        'category': 'correlation',
                        'confidence': 0.7
                    })

        # 5. Null analysis
        for col in df.columns[:10]:
            null_count = df[col].isna().sum()
            if null_count > 0:
                suggestions.append({
                    'query': f'SELECT COUNT(*) as total, SUM(CASE WHEN "{col}" IS NULL THEN 1 ELSE 0 END) as null_count FROM {table_name}',
                    'description': f'Null analysis for {col}',
                    'category': 'data_quality',
                    'confidence': 0.75
                })

        # 6. Row count (always useful)
        suggestions.append({
            'query': f'SELECT COUNT(*) as total_rows FROM {table_name}',
            'description': 'Total row count',
            'category': 'basic',
            'confidence': 1.0
        })

        return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)

    def execute_sql(self, query: str) -> Dict[str, Any]:
        """
        Execute SQL query and return results

        Returns:
            {
                'columns': [...],
                'rows': [...],
                'row_count': N,
                'execution_time': 0.123
            }
        """
        import time

        # METRICS: Track SQL query execution
        with metrics.track("sql_query_execution"):
            # ===== METAL 4 TICK FLOW =====
            # Kick frame if Metal4 is available
            if _metal4_engine and _metal4_engine.is_available():
                _metal4_engine.kick_frame()
                logger.debug(f"⚡ SQL query on Metal4 frame {_metal4_engine.frame_counter}")
            # ===== END METAL 4 TICK FLOW =====

            start = time.time()

            try:
                cursor = self.conn.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()

                # Convert Row objects to dicts
                results = [dict(row) for row in rows]

                execution_time = time.time() - start

                # ===== METAL 4 DIAGNOSTICS =====
                # Record SQL operation in Metal4 diagnostics
                if _metal4_engine and _metal4_engine.is_available():
                    try:
                        from api.metal4_diagnostics import get_diagnostics
                        diag = get_diagnostics()
                        if diag:
                            diag.record_operation('sql_queries', execution_time * 1000, 'ml')
                            logger.info(f"⚡ SQL query executed: {execution_time * 1000:.2f}ms (Metal4 tracked)")
                    except (ImportError, AttributeError):
                        pass  # Diagnostics not available
                # ===== END METAL 4 DIAGNOSTICS =====

                # METRICS: Record row count for query size tracking
                metrics.record("sql_rows_returned", len(results))

                return {
                    'columns': columns,
                    'rows': results,
                    'row_count': len(results),
                    'execution_time': round(execution_time * 1000, 2)  # ms
                }
            except Exception as e:
                logger.error(f"SQL execution failed: {e}")
                metrics.increment_error("sql_query_execution")
                raise

    def get_dataset_metadata(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a dataset"""
        cursor = self.conn.execute("""
            SELECT * FROM dataset_metadata WHERE dataset_id = ?
        """, (dataset_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'dataset_id': row['dataset_id'],
            'filename': row['original_filename'],
            'table_name': row['table_name'],
            'uploaded_at': row['upload_timestamp'],
            'rows': row['row_count'],
            'columns': row['column_count'],
            'schema': json.loads(row['schema_json']),
            'file_type': row['file_type'],
            'session_id': row['session_id']
        }

    def list_datasets(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all datasets, optionally filtered by session"""
        if session_id:
            cursor = self.conn.execute("""
                SELECT * FROM dataset_metadata
                WHERE session_id = ?
                ORDER BY upload_timestamp DESC
            """, (session_id,))
        else:
            cursor = self.conn.execute("""
                SELECT * FROM dataset_metadata
                ORDER BY upload_timestamp DESC
            """)

        datasets = []
        for row in cursor.fetchall():
            datasets.append({
                'dataset_id': row['dataset_id'],
                'filename': row['original_filename'],
                'table_name': row['table_name'],
                'uploaded_at': row['upload_timestamp'],
                'rows': row['row_count'],
                'columns': row['column_count'],
                'file_type': row['file_type']
            })

        return datasets

    def get_all_table_names(self) -> List[str]:
        """Get all valid table names from dataset metadata (for whitelist validation)"""
        cursor = self.conn.execute("""
            SELECT table_name FROM dataset_metadata
        """)
        return [row[0] for row in cursor.fetchall()]

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset and its table"""
        # Get table name
        metadata = self.get_dataset_metadata(dataset_id)
        if not metadata:
            return False

        table_name = metadata['table_name']

        # Validate table name to prevent SQL injection
        # MED-02: Use pre-compiled regex
        if not _TABLE_NAME_VALIDATOR.match(table_name):
            logger.error(f"Invalid table name: {table_name}")
            return False

        with self._write_lock:
            # Drop table (quote_identifier provides defense in depth)
            self.conn.execute(f"DROP TABLE IF EXISTS {quote_identifier(table_name)}")

            # Delete metadata
            self.conn.execute("""
                DELETE FROM dataset_metadata WHERE dataset_id = ?
            """, (dataset_id,))

            self.conn.commit()

        logger.info(f"Deleted dataset {dataset_id} ({table_name})")
        return True


# Singleton instance
_data_engine: Optional[DataEngine] = None


def get_data_engine() -> DataEngine:
    """Get singleton data engine instance"""
    global _data_engine
    if _data_engine is None:
        _data_engine = DataEngine()
    return _data_engine
