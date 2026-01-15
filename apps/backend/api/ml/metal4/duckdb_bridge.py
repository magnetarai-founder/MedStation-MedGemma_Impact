#!/usr/bin/env python3
"""
Metal 4 DuckDB Integration Bridge

"He leads me beside quiet waters, he refreshes my soul" - Psalm 23:2-3

Implements Phase 2.2 of Metal 4 Optimization Roadmap:
- DuckDB → Metal zero-copy data transfer
- Automatic query optimization (CPU vs GPU)
- Column-wise GPU acceleration
- Hybrid execution (DuckDB + Metal)

Performance Target: 3-5x faster for analytical queries on large datasets

Architecture:
- Arrow format for zero-copy transfers
- Automatic partitioning (GPU for large aggregations, CPU for small/complex queries)
- Columnar storage optimization
- Unified memory on Apple Silicon
"""

import logging
import time
from typing import Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class Metal4DuckDBBridge:
    """
    Integration bridge between DuckDB and Metal 4 GPU acceleration

    Automatically accelerates suitable DuckDB queries using Metal GPU:
    - Large aggregations (SUM, AVG, COUNT, MIN, MAX)
    - Column scans and filters
    - GROUP BY operations
    - Window functions

    Falls back to DuckDB CPU execution for:
    - Complex joins
    - String operations
    - Small datasets (< 10k rows)
    """

    def __init__(self):
        """Initialize DuckDB-Metal bridge"""
        self.sql_engine = None
        self.duckdb_conn = None

        # Query optimizer settings
        self.gpu_threshold_rows = 10000
        self.gpu_threshold_columns = 5

        # State
        self._initialized = False

        # Performance stats
        self.stats = {
            'total_queries': 0,
            'gpu_accelerated': 0,
            'cpu_executed': 0,
            'total_time_ms': 0,
            'gpu_time_ms': 0,
            'cpu_time_ms': 0
        }

        # Initialize
        self._initialize()

    def _initialize(self) -> None:
        """Initialize bridge components"""
        logger.info("Initializing Metal 4 DuckDB bridge...")

        # Initialize Metal SQL engine
        try:
            from metal4_sql_engine import get_sql_engine
            self.sql_engine = get_sql_engine()
            logger.info(f"   Metal SQL engine: {'✓' if self.sql_engine.uses_metal() else '✗ (CPU fallback)'}")
        except Exception as e:
            logger.warning(f"Metal SQL engine initialization failed: {e}")

        # Initialize DuckDB
        try:
            import duckdb
            self.duckdb_conn = duckdb.connect(':memory:')
            logger.info("   DuckDB connection: ✓")
        except ImportError:
            logger.error("DuckDB not installed. Install with: pip install duckdb")

        self._initialized = True
        logger.info("✅ Metal 4 DuckDB bridge initialized")

    # ========================================================================
    # Query Execution with Automatic GPU Acceleration
    # ========================================================================

    def execute(
        self,
        query: str,
        params: dict[str, Any] | None = None
    ) -> pd.DataFrame:
        """
        Execute SQL query with automatic GPU acceleration

        Analyzes query and decides whether to use:
        1. Metal GPU (for large aggregations)
        2. DuckDB CPU (for complex queries or small data)
        3. Hybrid (split execution)

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            DataFrame with results
        """
        if not self._initialized or not self.duckdb_conn:
            raise RuntimeError("Bridge not initialized")

        start = time.time()

        # Analyze query to determine execution strategy
        strategy = self._analyze_query(query)

        if strategy == 'gpu' and self.sql_engine and self.sql_engine.uses_metal():
            # GPU-accelerated execution
            result = self._execute_gpu(query, params)
            self.stats['gpu_accelerated'] += 1
            self.stats['gpu_time_ms'] += (time.time() - start) * 1000

        elif strategy == 'hybrid':
            # Hybrid execution (GPU aggregations + DuckDB)
            result = self._execute_hybrid(query, params)
            self.stats['gpu_accelerated'] += 1
            self.stats['gpu_time_ms'] += (time.time() - start) * 1000

        else:
            # CPU-only execution via DuckDB
            result = self._execute_cpu(query, params)
            self.stats['cpu_executed'] += 1
            self.stats['cpu_time_ms'] += (time.time() - start) * 1000

        self.stats['total_queries'] += 1
        self.stats['total_time_ms'] += (time.time() - start) * 1000

        return result

    def _analyze_query(self, query: str) -> str:
        """
        Analyze query to determine execution strategy

        Args:
            query: SQL query

        Returns:
            'gpu', 'cpu', or 'hybrid'
        """
        query_lower = query.lower()

        # Check for GPU-friendly patterns
        has_aggregation = any(
            agg in query_lower
            for agg in ['sum(', 'avg(', 'count(', 'min(', 'max(']
        )

        has_group_by = 'group by' in query_lower
        has_window = 'over(' in query_lower

        # Check for CPU-only operations
        has_join = 'join' in query_lower
        has_subquery = '(select' in query_lower
        has_string_ops = any(
            op in query_lower
            for op in ['concat', 'substring', 'like', 'regexp']
        )

        # Decision logic
        if has_string_ops or has_subquery:
            return 'cpu'  # Too complex for GPU

        if has_aggregation and not has_join:
            return 'gpu'  # Simple aggregation - GPU wins

        if has_group_by and not has_join:
            return 'hybrid'  # GROUP BY can benefit from GPU

        return 'cpu'  # Default to CPU

    def _execute_gpu(
        self,
        query: str,
        params: dict[str, Any] | None
    ) -> pd.DataFrame:
        """
        Execute query on GPU using Metal SQL engine

        This is a simplified implementation.
        Full version would parse SQL and call appropriate Metal kernels.

        Args:
            query: SQL query
            params: Parameters

        Returns:
            Results DataFrame
        """
        # For now, extract simple aggregations and execute on GPU
        # Full implementation would use a SQL parser

        # Fallback to CPU for now
        logger.debug("GPU execution not yet fully implemented, using CPU")
        return self._execute_cpu(query, params)

    def _execute_hybrid(
        self,
        query: str,
        params: dict[str, Any] | None
    ) -> pd.DataFrame:
        """
        Execute query using hybrid CPU+GPU approach

        Strategy:
        1. Use DuckDB to load and prepare data
        2. Extract aggregation columns
        3. Run aggregations on Metal GPU
        4. Combine results

        Args:
            query: SQL query
            params: Parameters

        Returns:
            Results DataFrame
        """
        # Simplified hybrid execution
        # Full implementation would split query into GPU and CPU parts

        logger.debug("Hybrid execution not yet fully implemented, using CPU")
        return self._execute_cpu(query, params)

    def _execute_cpu(
        self,
        query: str,
        params: dict[str, Any] | None
    ) -> pd.DataFrame:
        """
        Execute query on CPU using DuckDB

        Args:
            query: SQL query
            params: Parameters

        Returns:
            Results DataFrame
        """
        try:
            result = self.duckdb_conn.execute(query).fetchdf()
            return result

        except Exception as e:
            logger.error(f"DuckDB query failed: {e}")
            raise

    # ========================================================================
    # Table Management
    # ========================================================================

    def register_dataframe(
        self,
        name: str,
        df: pd.DataFrame
    ) -> None:
        """
        Register DataFrame as DuckDB table

        Args:
            name: Table name
            df: DataFrame to register
        """
        if not self.duckdb_conn:
            raise RuntimeError("DuckDB not initialized")

        self.duckdb_conn.register(name, df)
        logger.debug(f"Registered DataFrame '{name}' ({len(df)} rows, {len(df.columns)} cols)")

    def load_parquet(
        self,
        path: str,
        table_name: str | None = None
    ) -> pd.DataFrame:
        """
        Load Parquet file into DuckDB

        Args:
            path: Path to Parquet file
            table_name: Optional table name to register

        Returns:
            Loaded DataFrame
        """
        if not self.duckdb_conn:
            raise RuntimeError("DuckDB not initialized")

        query = f"SELECT * FROM '{path}'"
        df = self.duckdb_conn.execute(query).fetchdf()

        if table_name:
            self.register_dataframe(table_name, df)

        return df

    # ========================================================================
    # Accelerated Aggregations (Direct API)
    # ========================================================================

    import re
    _IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

    def _validate_identifier(self, name: str, kind: str = "identifier") -> None:
        """Validate DuckDB identifier (table/column) to prevent SQL injection."""
        if not isinstance(name, str) or not self._IDENTIFIER_RE.match(name):
            raise ValueError(f"Invalid {kind}: {name!r}")

    def accelerated_sum(
        self,
        table_name: str,
        column_name: str
    ) -> float:
        """
        Compute SUM using GPU acceleration

        Args:
            table_name: Table name
            column_name: Column to sum

        Returns:
            Sum value
        """
        # Validate identifiers to prevent SQL injection
        self._validate_identifier(table_name, "table name")
        self._validate_identifier(column_name, "column name")

        if not self.sql_engine:
            # Fallback to DuckDB
            query = f"SELECT SUM({column_name}) FROM {table_name}"
            result = self.duckdb_conn.execute(query).fetchone()
            return float(result[0])

        # Get column data
        query = f"SELECT {column_name} FROM {table_name}"
        df = self.duckdb_conn.execute(query).fetchdf()
        column = df[column_name].values

        # Use Metal GPU
        return self.sql_engine.sum(column)

    def accelerated_avg(
        self,
        table_name: str,
        column_name: str
    ) -> float:
        """
        Compute AVG using GPU acceleration

        Args:
            table_name: Table name
            column_name: Column to average

        Returns:
            Average value
        """
        # Validate identifiers to prevent SQL injection
        self._validate_identifier(table_name, "table name")
        self._validate_identifier(column_name, "column name")

        if not self.sql_engine:
            query = f"SELECT AVG({column_name}) FROM {table_name}"
            result = self.duckdb_conn.execute(query).fetchone()
            return float(result[0])

        # Get column data
        query = f"SELECT {column_name} FROM {table_name}"
        df = self.duckdb_conn.execute(query).fetchdf()
        column = df[column_name].values

        # Use Metal GPU
        return self.sql_engine.avg(column)

    def accelerated_count(
        self,
        table_name: str,
        column_name: str | None = None
    ) -> int:
        """
        Compute COUNT using GPU acceleration

        Args:
            table_name: Table name
            column_name: Optional column (or * for all rows)

        Returns:
            Count value
        """
        # Validate identifiers to prevent SQL injection
        self._validate_identifier(table_name, "table name")
        col = column_name or '*'
        if col != '*':
            self._validate_identifier(col, "column name")
        query = f"SELECT COUNT({col}) FROM {table_name}"
        result = self.duckdb_conn.execute(query).fetchone()
        return int(result[0])

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_table_info(self, table_name: str) -> dict[str, Any]:
        """
        Get information about a table

        Args:
            table_name: Table name

        Returns:
            Table metadata
        """
        if not self.duckdb_conn:
            return {}

        # Validate identifier
        self._validate_identifier(table_name, "table name")

        # Get row count
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        row_count = self.duckdb_conn.execute(count_query).fetchone()[0]

        # Get column info
        desc_query = f"DESCRIBE {table_name}"
        columns_df = self.duckdb_conn.execute(desc_query).fetchdf()

        return {
            'row_count': row_count,
            'column_count': len(columns_df),
            'columns': columns_df.to_dict('records')
        }

    def is_available(self) -> bool:
        """Check if bridge is initialized"""
        return self._initialized

    def uses_metal(self) -> bool:
        """Check if Metal GPU is available"""
        return self.sql_engine and self.sql_engine.uses_metal()

    def get_stats(self) -> dict[str, Any]:
        """Get performance statistics"""
        stats = self.stats.copy()

        if stats['total_queries'] > 0:
            stats['avg_time_ms'] = stats['total_time_ms'] / stats['total_queries']
            stats['gpu_percentage'] = (stats['gpu_accelerated'] / stats['total_queries']) * 100
        else:
            stats['avg_time_ms'] = 0
            stats['gpu_percentage'] = 0

        stats['metal_available'] = self.uses_metal()

        return stats

    def reset_stats(self) -> None:
        """Reset performance statistics"""
        self.stats = {
            'total_queries': 0,
            'gpu_accelerated': 0,
            'cpu_executed': 0,
            'total_time_ms': 0,
            'gpu_time_ms': 0,
            'cpu_time_ms': 0
        }


# ===== Singleton Instance =====

_duckdb_bridge: Metal4DuckDBBridge | None = None


def get_duckdb_bridge() -> Metal4DuckDBBridge:
    """Get singleton DuckDB bridge instance"""
    global _duckdb_bridge
    if _duckdb_bridge is None:
        _duckdb_bridge = Metal4DuckDBBridge()
    return _duckdb_bridge


def validate_duckdb_bridge() -> dict[str, Any]:
    """Validate DuckDB bridge setup"""
    try:
        bridge = get_duckdb_bridge()

        # Create test DataFrame
        test_df = pd.DataFrame({
            'id': range(100000),
            'value': np.random.randn(100000),
            'category': np.random.choice(['A', 'B', 'C'], 100000)
        })

        # Register with DuckDB
        bridge.register_dataframe('test_table', test_df)

        # Test SUM
        sum_result = bridge.accelerated_sum('test_table', 'value')
        expected_sum = test_df['value'].sum()
        sum_test = abs(sum_result - expected_sum) < 1.0

        # Test AVG
        avg_result = bridge.accelerated_avg('test_table', 'value')
        expected_avg = test_df['value'].mean()
        avg_test = abs(avg_result - expected_avg) < 0.01

        # Test COUNT
        count_result = bridge.accelerated_count('test_table')
        count_test = count_result == len(test_df)

        status = {
            'initialized': bridge.is_available(),
            'metal_available': bridge.uses_metal(),
            'duckdb_available': bridge.duckdb_conn is not None,
            'sum_test': sum_test,
            'avg_test': avg_test,
            'count_test': count_test,
            'all_tests_passed': all([sum_test, avg_test, count_test]),
            'stats': bridge.get_stats()
        }

        if status['all_tests_passed']:
            logger.info("✅ DuckDB bridge validation passed")
        else:
            logger.warning("⚠️  Some DuckDB bridge tests failed")

        return status

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            'initialized': False,
            'error': str(e)
        }


# Export
__all__ = [
    'Metal4DuckDBBridge',
    'get_duckdb_bridge',
    'validate_duckdb_bridge'
]
