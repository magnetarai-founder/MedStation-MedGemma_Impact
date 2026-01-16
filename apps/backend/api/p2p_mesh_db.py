"""
Compatibility Shim for P2P Mesh Database

The implementation now lives in the `api.p2p_mesh` package:
- api.p2p_mesh.db: Connection code database operations

This shim maintains backward compatibility.
"""

from api.p2p_mesh.db import (
    PATHS,
    CODES_DB_PATH,
    init_codes_db,
    save_connection_code,
    load_connection_codes,
    delete_connection_code,
    get_connection_code,
    cleanup_expired_codes,
    count_connection_codes,
    generate_connection_code,
)

__all__ = [
    "PATHS",
    "CODES_DB_PATH",
    "init_codes_db",
    "save_connection_code",
    "load_connection_codes",
    "delete_connection_code",
    "get_connection_code",
    "cleanup_expired_codes",
    "count_connection_codes",
    "generate_connection_code",
]
