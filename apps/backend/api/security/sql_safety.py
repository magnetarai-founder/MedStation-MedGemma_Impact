"""
SQL Safety Utilities for MedStation

Provides secure SQL operations to prevent SQL injection attacks.
All table/column names MUST be validated before use in SQL statements.

Usage:
    from api.security.sql_safety import validate_identifier, quote_identifier, SafeSQLBuilder

    # Validate a table name
    table = validate_identifier(user_input, allowed=["users", "sessions"])

    # Quote an identifier for safe SQL inclusion
    safe_col = quote_identifier("column_name")

    # Build safe dynamic SQL
    builder = SafeSQLBuilder("users")
    sql = builder.select(["id", "name"]).where("id = ?").build()
"""

import re
from typing import Optional, Sequence


# Valid SQL identifier pattern (alphanumeric + underscore, must start with letter/underscore)
IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Maximum identifier length (SQLite limit is 128, we use a reasonable default)
MAX_IDENTIFIER_LENGTH = 64


class SQLInjectionError(ValueError):
    """Raised when a potential SQL injection is detected"""
    pass


def validate_identifier(
    name: str,
    allowed: Optional[Sequence[str]] = None,
    context: str = "identifier"
) -> str:
    """
    Validate a SQL identifier (table name, column name, etc.)

    Args:
        name: The identifier to validate
        allowed: Optional whitelist of allowed values (strongest protection)
        context: Description of what's being validated (for error messages)

    Returns:
        The validated identifier (unchanged if valid)

    Raises:
        SQLInjectionError: If the identifier is invalid or not in whitelist
    """
    if not name:
        raise SQLInjectionError(f"Empty {context} is not allowed")

    if len(name) > MAX_IDENTIFIER_LENGTH:
        raise SQLInjectionError(
            f"{context} '{name[:20]}...' exceeds maximum length of {MAX_IDENTIFIER_LENGTH}"
        )

    # If whitelist provided, use strict matching
    if allowed is not None:
        if name not in allowed:
            raise SQLInjectionError(
                f"Invalid {context}: '{name}'. Must be one of: {', '.join(allowed[:10])}"
                + ("..." if len(allowed) > 10 else "")
            )
        return name

    # Pattern validation for dynamic identifiers
    if not IDENTIFIER_PATTERN.match(name):
        raise SQLInjectionError(
            f"Invalid {context}: '{name}'. Must contain only alphanumeric characters and underscores, "
            "and must start with a letter or underscore."
        )

    # Check for SQL keywords that shouldn't be identifiers
    sql_keywords = {
        "select", "insert", "update", "delete", "drop", "create", "alter",
        "table", "index", "from", "where", "and", "or", "not", "null",
        "union", "join", "exec", "execute", "grant", "revoke"
    }
    if name.lower() in sql_keywords:
        raise SQLInjectionError(
            f"Invalid {context}: '{name}' is a reserved SQL keyword"
        )

    return name


def quote_identifier(name: str) -> str:
    """
    Quote a SQL identifier for safe inclusion in SQL statements.

    Uses double-quotes which is standard SQL and works in SQLite.
    Any embedded double-quotes are escaped by doubling them.

    Args:
        name: The identifier to quote (must be pre-validated)

    Returns:
        The quoted identifier
    """
    # Escape any embedded double-quotes
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def validate_and_quote(
    name: str,
    allowed: Optional[Sequence[str]] = None,
    context: str = "identifier"
) -> str:
    """
    Validate and quote a SQL identifier in one step.

    Args:
        name: The identifier to validate and quote
        allowed: Optional whitelist of allowed values
        context: Description of what's being validated

    Returns:
        The quoted, validated identifier
    """
    validated = validate_identifier(name, allowed=allowed, context=context)
    return quote_identifier(validated)


class SafeSQLBuilder:
    """
    Safe SQL query builder that prevents injection attacks.

    All table and column names are validated and quoted.
    Values must use parameterized placeholders (?).

    Example:
        builder = SafeSQLBuilder("users", allowed_columns=["id", "name", "email"])
        sql = builder.select(["id", "name"]).where("id = ?").order_by("name").build()
        # Returns: SELECT "id", "name" FROM "users" WHERE id = ? ORDER BY "name"
    """

    def __init__(
        self,
        table: str,
        allowed_tables: Optional[Sequence[str]] = None,
        allowed_columns: Optional[Sequence[str]] = None
    ):
        self.table = validate_identifier(table, allowed=allowed_tables, context="table name")
        self.allowed_columns = allowed_columns
        self._select_cols: list[str] = []
        self._where: Optional[str] = None
        self._order_by: Optional[str] = None
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None

    def select(self, columns: Sequence[str]) -> "SafeSQLBuilder":
        """Add SELECT columns (validated and quoted)"""
        for col in columns:
            validated = validate_identifier(col, allowed=self.allowed_columns, context="column name")
            self._select_cols.append(quote_identifier(validated))
        return self

    def where(self, condition: str) -> "SafeSQLBuilder":
        """Add WHERE clause (use ? for parameters)"""
        # Note: The condition should use ? for values, not string interpolation
        self._where = condition
        return self

    def order_by(self, column: str, desc: bool = False) -> "SafeSQLBuilder":
        """Add ORDER BY clause"""
        validated = validate_identifier(column, allowed=self.allowed_columns, context="column name")
        direction = "DESC" if desc else "ASC"
        self._order_by = f"{quote_identifier(validated)} {direction}"
        return self

    def limit(self, count: int) -> "SafeSQLBuilder":
        """Add LIMIT clause"""
        if count < 0:
            raise ValueError("LIMIT must be non-negative")
        self._limit = count
        return self

    def offset(self, count: int) -> "SafeSQLBuilder":
        """Add OFFSET clause"""
        if count < 0:
            raise ValueError("OFFSET must be non-negative")
        self._offset = count
        return self

    def build(self) -> str:
        """Build the final SQL query"""
        cols = ", ".join(self._select_cols) if self._select_cols else "*"
        sql = f"SELECT {cols} FROM {quote_identifier(self.table)}"

        if self._where:
            sql += f" WHERE {self._where}"

        if self._order_by:
            sql += f" ORDER BY {self._order_by}"

        if self._limit is not None:
            sql += f" LIMIT {self._limit}"

        if self._offset is not None:
            sql += f" OFFSET {self._offset}"

        return sql


def build_update_sql(
    table: str,
    columns: Sequence[str],
    allowed_tables: Optional[Sequence[str]] = None,
    allowed_columns: Optional[Sequence[str]] = None,
    where_clause: str = "id = ?"
) -> str:
    """
    Build a safe UPDATE statement.

    Args:
        table: Table name to update
        columns: Column names to update
        allowed_tables: Whitelist of valid table names
        allowed_columns: Whitelist of valid column names
        where_clause: WHERE clause (should use ? for parameters)

    Returns:
        Safe UPDATE SQL string with placeholders

    Example:
        sql = build_update_sql("users", ["name", "email"], where_clause="id = ?")
        # Returns: UPDATE "users" SET "name" = ?, "email" = ? WHERE id = ?
    """
    validated_table = validate_identifier(table, allowed=allowed_tables, context="table name")
    validated_columns = [
        validate_identifier(col, allowed=allowed_columns, context="column name")
        for col in columns
    ]

    set_clause = ", ".join(f"{quote_identifier(col)} = ?" for col in validated_columns)
    return f"UPDATE {quote_identifier(validated_table)} SET {set_clause} WHERE {where_clause}"
