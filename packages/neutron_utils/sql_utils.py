"""
SQL processing utilities with optimized regex compilation
"""

import re
from typing import List, Tuple, Optional
import logging
import pandas as pd

logger = logging.getLogger(__name__)

# Pre-compiled regex patterns for performance
REGEX_PATTERNS = {
    "comments": re.compile(r"--.*?$|/\*.*?\*/", re.MULTILINE | re.DOTALL),
    "whitespace": re.compile(r"\s+"),
    "semicolon": re.compile(r";\s*$"),
    "quotes": re.compile(r"'[^']*'"),
    "double_quotes": re.compile(r'"[^"]*"'),
    "parameters": re.compile(r":[a-zA-Z_]\w*|\?"),
    "temp_tables": re.compile(r"\b(CREATE|DROP)\s+TEMP(ORARY)?\s+TABLE\b", re.IGNORECASE),
    "column_names": re.compile(r"[^a-zA-Z0-9_]"),
    "invalid_chars": re.compile(r"[^\w\s,._\-()]"),
    "multiple_spaces": re.compile(r"\s{2,}"),
    "redshift_copy": re.compile(r"\bCOPY\s+\w+\s+FROM\b", re.IGNORECASE),
    "redshift_unload": re.compile(r"\bUNLOAD\s*\(", re.IGNORECASE),
}


class SQLProcessor:
    """SQL processing utilities"""

    @staticmethod
    def clean_sql(sql: str) -> str:
        """
        Clean SQL query by removing comments and extra whitespace

        Args:
            sql: Raw SQL query

        Returns:
            Cleaned SQL query
        """
        # Remove comments
        sql = REGEX_PATTERNS["comments"].sub("", sql)

        # Replace multiple whitespaces with single space
        sql = REGEX_PATTERNS["whitespace"].sub(" ", sql)

        # Remove trailing semicolon
        sql = REGEX_PATTERNS["semicolon"].sub("", sql)

        return sql.strip()

    @staticmethod
    def split_sql_statements(sql: str) -> List[str]:
        """
        Split SQL into individual statements

        Args:
            sql: SQL query string

        Returns:
            List of SQL statements
        """
        # Preserve quoted strings
        quoted_strings = []

        def replace_quoted(match):
            quoted_strings.append(match.group(0))
            return f"__QUOTED_{len(quoted_strings)-1}__"

        # Replace quoted strings temporarily
        sql_temp = REGEX_PATTERNS["quotes"].sub(replace_quoted, sql)
        sql_temp = REGEX_PATTERNS["double_quotes"].sub(replace_quoted, sql_temp)

        # Split by semicolon
        statements = [s.strip() for s in sql_temp.split(";") if s.strip()]

        # Restore quoted strings
        for i, statement in enumerate(statements):
            for j, quoted in enumerate(quoted_strings):
                statements[i] = statements[i].replace(f"__QUOTED_{j}__", quoted)

        return statements

    @staticmethod
    def validate_sql(sql: str) -> Tuple[bool, Optional[str]]:
        """
        Basic SQL validation

        Args:
            sql: SQL query to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        sql = sql.strip()

        if not sql:
            return False, "Empty SQL query"

        # Check for basic SQL keywords
        sql_upper = sql.upper()
        valid_starts = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "WITH", "COPY", "UNLOAD"]

        if not any(sql_upper.startswith(keyword) for keyword in valid_starts):
            return False, "SQL must start with a valid keyword"

        # Check for balanced parentheses
        open_parens = sql.count("(")
        close_parens = sql.count(")")
        if open_parens != close_parens:
            return False, f"Unbalanced parentheses: {open_parens} open, {close_parens} close"

        # Check for balanced quotes
        single_quotes = sql.count("'")
        if single_quotes % 2 != 0:
            return False, "Unbalanced single quotes"

        double_quotes = sql.count('"')
        if double_quotes % 2 != 0:
            return False, "Unbalanced double quotes"

        return True, None

    @staticmethod
    def extract_table_names(sql: str) -> List[str]:
        """
        Extract table names from SQL query

        Args:
            sql: SQL query

        Returns:
            List of table names
        """
        # Simple regex to find table names after FROM, JOIN, etc.
        table_pattern = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([a-zA-Z_][\w.]*)", re.IGNORECASE)

        tables = []
        for match in table_pattern.finditer(sql):
            table = match.group(1)
            # Remove schema prefix if present
            if "." in table:
                table = table.split(".")[-1]
            tables.append(table)

        return list(set(tables))


class ColumnNameCleaner:
    """Utilities for cleaning column names.

    This class historically exposed different method names in tests/scripts.
    To maintain backward compatibility, it now provides both a static
    `clean_column_name` and an instance method `clean` that delegates to it.
    """

    @staticmethod
    def clean_column_name(name: str) -> str:
        """
        Clean column name for SQL compatibility

        Args:
            name: Original column name

        Returns:
            Cleaned column name
        """
        # Replace invalid characters with underscore
        name = REGEX_PATTERNS["column_names"].sub("_", str(name))

        # Remove leading/trailing underscores
        name = name.strip("_")

        # Replace multiple underscores with single
        name = re.sub(r"_{2,}", "_", name)

        # Ensure name doesn't start with number
        if name and name[0].isdigit():
            name = f"col_{name}"

        # Ensure name is not empty
        if not name:
            name = "unnamed_column"

        return name  # Preserve original case

    @staticmethod
    def clean_sql_identifier(name: str, preserve_case: bool = True) -> str:
        """Clean to a SQL-safe identifier.

        - Replaces invalid characters with underscore
        - Collapses multiple underscores
        - Strips leading/trailing underscores
        - Prefixes with 'col_' if starting with a digit
        - Optionally preserves original case (default True)
        """
        cleaned = REGEX_PATTERNS["column_names"].sub("_", str(name))
        cleaned = cleaned.strip("_")
        cleaned = re.sub(r"_{2,}", "_", cleaned)
        if cleaned and cleaned[0].isdigit():
            cleaned = f"col_{cleaned}"
        if not cleaned:
            cleaned = "unnamed_column"
        return cleaned if preserve_case else cleaned.lower()

    # Backward-compatible instance API used by some stress tests
    def clean(self, name: str) -> str:  # pragma: no cover - thin adapter
        return ColumnNameCleaner.clean_column_name(name)

    @staticmethod
    def clean_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean all column names in a DataFrame

        Args:
            df: DataFrame with potentially invalid column names

        Returns:
            DataFrame with cleaned column names
        """
        df = df.copy()
        df.columns = [ColumnNameCleaner.clean_column_name(col) for col in df.columns]
        return df


class RedshiftOptimizer:
    """Redshift-specific SQL optimizations"""

    @staticmethod
    def optimize_for_redshift(sql: str) -> str:
        """
        Optimize SQL for Redshift execution

        Args:
            sql: Original SQL query

        Returns:
            Optimized SQL query
        """
        # Add COMPUPDATE OFF to COPY commands
        if REGEX_PATTERNS["redshift_copy"].search(sql):
            if "COMPUPDATE" not in sql.upper():
                sql = sql.rstrip(";") + " COMPUPDATE OFF;"

        # Add compression to UNLOAD commands
        if REGEX_PATTERNS["redshift_unload"].search(sql):
            if "GZIP" not in sql.upper() and "BZIP2" not in sql.upper():
                sql = sql.rstrip(";") + " GZIP;"

        return sql

    @staticmethod
    def add_distribution_key(create_table_sql: str, dist_key: str) -> str:
        """
        Add distribution key to CREATE TABLE statement

        Args:
            create_table_sql: CREATE TABLE SQL
            dist_key: Column name for distribution key

        Returns:
            Modified SQL with distribution key
        """
        if "DISTKEY" in create_table_sql.upper():
            return create_table_sql

        # Add before the final semicolon
        sql = create_table_sql.rstrip(";")
        sql += f" DISTKEY({dist_key});"

        return sql
