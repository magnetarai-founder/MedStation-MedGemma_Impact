"""
Redshift SQL Processor - Backward Compatibility Shim

This module provides backward compatibility for code that imports from
the original monolithic redshift_sql_processor.py file.

The implementation has been refactored into the redshift_sql_processor package:
- redshift_sql_processor/core.py: Main RedshiftSQLProcessor class
- redshift_sql_processor/constants.py: Constants and regex patterns
- redshift_sql_processor/utils.py: Utility functions

All public APIs are re-exported from this module to maintain compatibility.
"""

# Re-export everything from the package
from redshift_sql_processor import (
    RedshiftSQLProcessor,
    process_sql_with_redshift_compatibility,
    execute_query,
)

__all__ = [
    "RedshiftSQLProcessor",
    "process_sql_with_redshift_compatibility",
    "execute_query",
]
