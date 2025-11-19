"""
Neutron Star Core Engine
The dumb core that always works - Excel + SQL + DuckDB = Results

This is the foundation that NEVER breaks, requires ZERO dependencies beyond DuckDB,
and works completely offline. All smart features are built on top of this.

This module serves as the public API facade. Heavy lifting is delegated to:
- connection.py: DuckDB connection and configuration
- type_mapper.py: Type inference and automatic numeric casting
- query_executor.py: SQL execution and dialect translation
- file_loader.py: Excel/CSV loading with streaming support
"""

import logging
import pandas as pd
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from neutron_utils.config import bootstrap_logging

# Import public API components
from .connection import create_connection
from .query_executor import SQLDialect, QueryResult, execute_sql
from .file_loader import load_excel, load_csv

logger = logging.getLogger(__name__)


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

        # Create and configure connection
        self.conn = create_connection(memory_limit)

        # Table registry (table_name -> file_path mapping)
        self.tables: Dict[str, str] = {}

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
        return load_excel(self.conn, self.tables, file_path, table_name, sheet_name)

    def load_csv(self, file_path: Union[str, Path], table_name: str = "excel_file") -> QueryResult:
        """
        Load a CSV file into the engine in a robust, text-first way.
        Default: pandas first with dtype=str (more forgiving), then DuckDB.
        """
        return load_csv(self.conn, self.tables, file_path, table_name)

    def execute_sql(
        self, query: str, dialect: SQLDialect = SQLDialect.DUCKDB, limit: Optional[int] = None
    ) -> QueryResult:
        """
        Execute SQL in any dialect. This is where the magic happens.
        DuckDB handles the heavy lifting, we just translate dialects.
        """
        return execute_sql(self.conn, query, dialect, limit)

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
