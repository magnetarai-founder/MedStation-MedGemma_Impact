"""
SQL query processing utilities.

Handles SQL cleaning, validation, and security checks.
"""

from typing import Set


def clean_sql(sql_text: str) -> str:
    """
    Clean SQL query by removing comments and trailing semicolons.

    Args:
        sql_text: Raw SQL query text

    Returns:
        Cleaned SQL query
    """
    from api.routes.sql_json.utils import get_SQLProcessor
    SQLProcessor = get_SQLProcessor()
    return SQLProcessor.clean_sql(sql_text)


def extract_table_names(sql_text: str) -> list:
    """
    Extract table names referenced in SQL query.

    Args:
        sql_text: SQL query text

    Returns:
        List of table names
    """
    from neutron_utils.sql_utils import SQLProcessor
    return SQLProcessor.extract_table_names(sql_text)


def validate_table_access(referenced_tables: list, allowed_tables: Set[str]) -> None:
    """
    Validate that query only accesses allowed tables.

    Args:
        referenced_tables: List of tables referenced in query
        allowed_tables: Set of allowed table names

    Raises:
        AppException: If query references unauthorized tables
    """
    from api.errors import http_403

    unauthorized_tables = set(referenced_tables) - allowed_tables
    if unauthorized_tables:
        raise http_403(f"Query references unauthorized tables: {', '.join(unauthorized_tables)}. Only 'excel_file' is allowed.")


def validate_sql_syntax(sql_text: str, expected_table: str = "excel_file") -> tuple:
    """
    Validate SQL syntax before execution.

    Args:
        sql_text: SQL query to validate
        expected_table: Expected table name in query

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    from neutron_utils.sql_utils import SQLValidator
    validator = SQLValidator()
    return validator.validate_sql(sql_text, expected_table=expected_table)
