"""
DuckDB Connection Management

Handles DuckDB connection creation, configuration, and extension setup.
"""
import os
import logging
import duckdb
from typing import Optional
from neutron_utils.config import config

logger = logging.getLogger(__name__)


def create_connection(memory_limit: Optional[str] = None) -> duckdb.DuckDBPyConnection:
    """
    Create and configure a DuckDB connection.

    Args:
        memory_limit: Memory limit string (e.g., "4096MB"), or None to use config default

    Returns:
        Configured DuckDB connection
    """
    conn = duckdb.connect(":memory:")

    # Configure memory limit
    configure_memory_limit(conn, memory_limit)

    # Configure threads
    configure_threads(conn)

    # Configure temp directory
    configure_temp_directory(conn)

    # Setup extensions
    setup_extensions(conn)

    # Log configuration
    try:
        mem_str = memory_limit if memory_limit else "default"
        tmp_str = os.getenv("DATA_TOOL_TEMP_DIR") or config.get("temp_dir") or "default"
        logger.info(
            "DuckDB configured • memory=%s threads=auto temp_dir=%s",
            mem_str,
            tmp_str,
        )
    except Exception:
        pass

    return conn


def configure_memory_limit(conn: duckdb.DuckDBPyConnection, memory_limit: Optional[str] = None) -> None:
    """
    Configure DuckDB memory limit.

    Args:
        conn: DuckDB connection
        memory_limit: Memory limit string or None for default
    """
    try:
        mem = memory_limit
        if not mem:
            mb = int(config.get("memory_limit_mb", 4096))
            mem = f"{mb}MB"
        conn.execute(f"SET memory_limit='{mem}'")
    except Exception as e:
        logger.debug(f"Could not set memory limit: {e}")


def configure_threads(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Configure DuckDB to use system threads.

    Args:
        conn: DuckDB connection
    """
    try:
        conn.execute("PRAGMA threads=system_threads();")
    except Exception:
        pass


def configure_temp_directory(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Configure DuckDB temporary directory.

    Args:
        conn: DuckDB connection
    """
    try:
        tmp = os.getenv("DATA_TOOL_TEMP_DIR") or config.get("temp_dir")
        if tmp:
            conn.execute(f"SET temp_directory='{tmp}'")
    except Exception as e:
        logger.debug(f"Could not set temp_directory: {e}")


def setup_extensions(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Setup DuckDB extensions (e.g., Excel support).

    Args:
        conn: DuckDB connection
    """
    try:
        conn.install_extension("excel")
        conn.load_extension("excel")
    except Exception as e:
        logger.warning(f"Excel extension not available, using pandas fallback: {e}")
