"""
Base Repository Pattern

Provides common CRUD operations and query patterns for SQLite repositories:
- Schema creation with migrations
- Standard CRUD operations
- Pagination helpers
- Query building utilities

Note: S608 warnings are intentionally suppressed - table_name comes from class
properties (not user input) and all user values use parameterized queries.
SQL identifiers are validated via _validate_identifier() and _validate_order_by().
"""
# ruff: noqa: S608
import logging
import re
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, TypeVar

from .connection import DatabaseConnection

logger = logging.getLogger(__name__)


# SECURITY: SQL identifier validation to prevent injection
_VALID_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_VALID_ORDER_DIRECTIONS = {"ASC", "DESC", "asc", "desc"}


def _validate_identifier(name: str, context: str = "identifier") -> str:
    """
    Validate a SQL identifier (table name, column name) to prevent injection.

    Args:
        name: The identifier to validate
        context: Description for error messages (e.g., "column name", "table name")

    Returns:
        The validated identifier

    Raises:
        ValueError: If identifier contains invalid characters
    """
    if not name:
        raise ValueError(f"Empty {context} not allowed")

    if not _VALID_IDENTIFIER_PATTERN.match(name):
        raise ValueError(
            f"Invalid {context}: '{name}'. "
            f"Must start with letter/underscore and contain only alphanumeric/underscore."
        )

    # Additional check: reasonable length
    if len(name) > 128:
        raise ValueError(f"{context} too long: max 128 characters")

    return name


def _validate_order_by(order_by: str) -> str:
    """
    Validate an ORDER BY clause to prevent SQL injection.

    Accepts formats like:
    - "column_name"
    - "column_name ASC"
    - "column_name DESC"
    - "column1 ASC, column2 DESC"

    Args:
        order_by: The ORDER BY clause to validate

    Returns:
        The validated ORDER BY clause

    Raises:
        ValueError: If the clause contains invalid components
    """
    if not order_by:
        return order_by

    validated_parts = []

    # Split by comma for multiple columns
    for part in order_by.split(","):
        part = part.strip()
        if not part:
            continue

        # Split by space to separate column and direction
        tokens = part.split()

        if len(tokens) == 1:
            # Just column name
            _validate_identifier(tokens[0], "column name in ORDER BY")
            validated_parts.append(tokens[0])

        elif len(tokens) == 2:
            # Column name + direction
            _validate_identifier(tokens[0], "column name in ORDER BY")

            if tokens[1].upper() not in _VALID_ORDER_DIRECTIONS:
                raise ValueError(
                    f"Invalid ORDER BY direction: '{tokens[1]}'. Must be ASC or DESC."
                )

            validated_parts.append(f"{tokens[0]} {tokens[1].upper()}")

        else:
            raise ValueError(
                f"Invalid ORDER BY component: '{part}'. "
                f"Expected 'column' or 'column ASC/DESC'."
            )

    return ", ".join(validated_parts)

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base class for SQLite repositories.

    Provides:
    - Schema creation with migration support
    - Standard CRUD operations
    - Query helpers
    - Consistent patterns for all repositories

    Subclasses must implement:
    - table_name: Name of the database table
    - _create_table_sql(): SQL for table creation
    - _row_to_entity(): Convert sqlite3.Row to entity
    """

    def __init__(self, db: DatabaseConnection):
        """
        Initialize repository with database connection.

        Args:
            db: DatabaseConnection instance
        """
        self.db = db
        self._ensure_table()

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Return the name of the database table."""
        pass

    @abstractmethod
    def _create_table_sql(self) -> str:
        """Return SQL statement to create the table."""
        pass

    @abstractmethod
    def _row_to_entity(self, row: sqlite3.Row) -> T:
        """Convert a database row to an entity object."""
        pass

    def _ensure_table(self):
        """Create table if it doesn't exist and run migrations."""
        self.db.execute(self._create_table_sql())
        self.db.get().commit()
        self._run_migrations()

    def _run_migrations(self):
        """
        Override to add column migrations.

        Example:
            self._add_column_if_missing("new_column", "TEXT DEFAULT ''")
        """
        pass

    def _add_column_if_missing(
        self,
        column_name: str,
        column_def: str,
    ):
        """
        Add a column if it doesn't exist (for migrations).

        Args:
            column_name: Name of column to add
            column_def: Column definition (e.g., "TEXT DEFAULT ''")
        """
        try:
            self.db.execute(
                f"ALTER TABLE {self.table_name} ADD COLUMN {column_name} {column_def}"
            )
            self.db.get().commit()
            logger.info(f"Added column {column_name} to {self.table_name}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    def _create_index(
        self,
        columns: list[str],
        unique: bool = False,
        name: str | None = None,
    ):
        """
        Create an index on the table.

        Args:
            columns: List of column names
            unique: Whether index should be unique
            name: Optional index name (auto-generated if not provided)
        """
        if name is None:
            name = f"idx_{self.table_name}_{'_'.join(columns)}"

        self.db.create_index(name, self.table_name, columns, unique)

    # =========================================================================
    # Standard CRUD Operations
    # =========================================================================

    def find_by_id(self, id_value: Any, id_column: str = "id") -> T | None:
        """
        Find entity by ID.

        Args:
            id_value: ID value to search for
            id_column: Name of ID column (default: "id")

        Returns:
            Entity or None
        """
        # SECURITY: Validate column name to prevent SQL injection
        _validate_identifier(id_column, "ID column name")

        row = self.db.fetchone(
            f"SELECT * FROM {self.table_name} WHERE {id_column} = ?",
            (id_value,),
        )
        return self._row_to_entity(row) if row else None

    def find_all(
        self,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[T]:
        """
        Find all entities with optional ordering and pagination.

        Args:
            order_by: Column(s) to order by (e.g., "created_at DESC")
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of entities
        """
        sql = f"SELECT * FROM {self.table_name}"

        if order_by:
            # SECURITY: Validate ORDER BY clause to prevent SQL injection
            validated_order = _validate_order_by(order_by)
            sql += f" ORDER BY {validated_order}"

        if limit:
            sql += f" LIMIT {limit}"
            if offset:
                sql += f" OFFSET {offset}"

        rows = self.db.fetchall(sql)
        return [self._row_to_entity(row) for row in rows]

    def find_where(
        self,
        where: str,
        params: tuple | list | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[T]:
        """
        Find entities matching WHERE clause.

        Args:
            where: WHERE clause (e.g., "status = ? AND user_id = ?")
            params: Parameters for WHERE clause
            order_by: Column(s) to order by
            limit: Maximum number of results

        Returns:
            List of matching entities
        """
        sql = f"SELECT * FROM {self.table_name} WHERE {where}"

        if order_by:
            # SECURITY: Validate ORDER BY clause to prevent SQL injection
            validated_order = _validate_order_by(order_by)
            sql += f" ORDER BY {validated_order}"

        if limit:
            sql += f" LIMIT {limit}"

        rows = self.db.fetchall(sql, params)
        return [self._row_to_entity(row) for row in rows]

    def find_one_where(
        self,
        where: str,
        params: tuple | list | None = None,
    ) -> T | None:
        """
        Find single entity matching WHERE clause.

        Args:
            where: WHERE clause
            params: Parameters for WHERE clause

        Returns:
            Entity or None
        """
        sql = f"SELECT * FROM {self.table_name} WHERE {where} LIMIT 1"
        row = self.db.fetchone(sql, params)
        return self._row_to_entity(row) if row else None

    def count(self, where: str | None = None, params: tuple | list | None = None) -> int:
        """
        Count entities.

        Args:
            where: Optional WHERE clause
            params: Parameters for WHERE clause

        Returns:
            Count of entities
        """
        sql = f"SELECT COUNT(*) as count FROM {self.table_name}"

        if where:
            sql += f" WHERE {where}"

        row = self.db.fetchone(sql, params)
        return row["count"] if row else 0

    def exists(self, where: str, params: tuple | list | None = None) -> bool:
        """
        Check if any entities match WHERE clause.

        Args:
            where: WHERE clause
            params: Parameters for WHERE clause

        Returns:
            True if matching entities exist
        """
        sql = f"SELECT 1 FROM {self.table_name} WHERE {where} LIMIT 1"
        row = self.db.fetchone(sql, params)
        return row is not None

    def insert(self, data: dict[str, Any]) -> int:
        """
        Insert a new row.

        Args:
            data: Column-value dictionary

        Returns:
            Last inserted row ID
        """
        return self.db.insert(self.table_name, data)

    def update_where(
        self,
        data: dict[str, Any],
        where: str,
        where_params: tuple | list | None = None,
    ) -> int:
        """
        Update rows matching WHERE clause.

        Args:
            data: Column-value dictionary for SET clause
            where: WHERE clause
            where_params: Parameters for WHERE clause

        Returns:
            Number of affected rows
        """
        return self.db.update(self.table_name, data, where, where_params)

    def delete_where(self, where: str, params: tuple | list | None = None) -> int:
        """
        Delete rows matching WHERE clause.

        Args:
            where: WHERE clause
            params: Parameters for WHERE clause

        Returns:
            Number of deleted rows
        """
        return self.db.delete(self.table_name, where, params)

    def delete_by_id(self, id_value: Any, id_column: str = "id") -> bool:
        """
        Delete entity by ID.

        Args:
            id_value: ID value
            id_column: Name of ID column

        Returns:
            True if deleted
        """
        # SECURITY: Validate column name to prevent SQL injection
        _validate_identifier(id_column, "ID column name")

        count = self.delete_where(f"{id_column} = ?", (id_value,))
        return count > 0

    # =========================================================================
    # Utility Methods
    # =========================================================================

    @staticmethod
    def now_iso() -> str:
        """Get current UTC time as ISO string."""
        return datetime.utcnow().isoformat()

    def raw_query(
        self,
        sql: str,
        params: tuple | list | None = None,
    ) -> list[sqlite3.Row]:
        """
        Execute raw SQL query.

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            List of rows
        """
        return self.db.fetchall(sql, params)
