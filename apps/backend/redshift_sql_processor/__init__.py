"""
Redshift SQL Processor Package

Provides robust SQL processing that mimics Redshift/DataCentral behavior using DuckDB.

Public API:
- RedshiftSQLProcessor: Main SQL processor class
- process_sql_with_redshift_compatibility: Convenience function
- execute_query: Module-level convenience alias

Example usage:
    from redshift_sql_processor import RedshiftSQLProcessor

    with RedshiftSQLProcessor() as processor:
        result = processor.execute_sql(sql, df)

Package structure:
- core.py: Main RedshiftSQLProcessor class
- constants.py: Reserved words, regex patterns, column patterns
- utils.py: Pure utility functions
"""

from redshift_sql_processor.core import (
    RedshiftSQLProcessor,
    process_sql_with_redshift_compatibility,
    execute_query,
)

__all__ = [
    "RedshiftSQLProcessor",
    "process_sql_with_redshift_compatibility",
    "execute_query",
]
