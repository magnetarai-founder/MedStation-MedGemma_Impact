"""
Shared Pydantic models for API request/response schemas.

Centralized location for all API models to avoid circular imports
between main.py and routers.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from neutron_utils.sql_utils import SQLDialect


# ============================================================================
# Session Models
# ============================================================================

class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime


# ============================================================================
# SQL/JSON Data Processing Models
# ============================================================================

class ColumnInfo(BaseModel):
    original_name: str
    clean_name: str
    dtype: str
    non_null_count: int
    null_count: int


class FileUploadResponse(BaseModel):
    filename: str
    size_mb: float
    row_count: int
    column_count: int
    columns: list[ColumnInfo]
    preview: list[dict]


class QueryRequest(BaseModel):
    sql: str
    limit: int | None = 1000
    dialect: SQLDialect = SQLDialect.DUCKDB
    timeout_seconds: int | None = 300


class QueryResponse(BaseModel):
    query_id: str
    row_count: int
    column_count: int
    columns: list[str]
    execution_time_ms: float
    preview: list[dict]
    has_more: bool


class ExportRequest(BaseModel):
    query_id: str
    format: str = Field(default="excel", pattern="^(excel|csv|tsv|parquet|json)$")
    filename: str | None = None


class ValidationRequest(BaseModel):
    sql: str
    dialect: SQLDialect = SQLDialect.DUCKDB


class ValidationResponse(BaseModel):
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class QueryHistoryItem(BaseModel):
    id: str
    query: str
    timestamp: str
    executionTime: float | None = None
    rowCount: int | None = None
    status: str


class QueryHistoryResponse(BaseModel):
    history: list[QueryHistoryItem]


class DatasetListResponse(BaseModel):
    datasets: list[dict[str, Any]]


# ============================================================================
# JSON Processing Models
# ============================================================================

class JsonUploadResponse(BaseModel):
    filename: str
    size_mb: float
    object_count: int
    depth: int
    columns: list[str]
    preview: list[dict[str, Any]]


class JsonConvertRequest(BaseModel):
    json_data: str
    options: dict[str, Any] = Field(default_factory=lambda: {
        "expand_arrays": True,
        "max_depth": 5,
        "auto_safe": True,
        "include_summary": True
    })


class JsonConvertResponse(BaseModel):
    success: bool
    output_file: str
    total_rows: int
    sheets: list[str]
    columns: list[str]
    preview: list[dict[str, Any]]
    is_preview_only: bool = False


# ============================================================================
# Additional Session Data Models
# ============================================================================

class SheetNamesResponse(BaseModel):
    filename: str
    sheets: list[str]


class TableInfo(BaseModel):
    name: str
    file: str
    row_count: int
    column_count: int


class TablesListResponse(BaseModel):
    tables: list[TableInfo]


# Generic Response Models
# ============================================================================

class SuccessResponse(BaseModel):
    success: bool
    message: str | None = None
