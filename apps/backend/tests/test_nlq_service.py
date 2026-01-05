"""
Comprehensive tests for api/services/nlq_service.py

Tests cover:
- NLQ history schema and persistence
- SQL extraction from LLM responses
- SQL validation with security checks
- LIMIT clause injection
- Summary generation
- Prompt building
- Singleton pattern
- Error handling
"""

import pytest
import sqlite3
import tempfile
import re
import json
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


# ========== Fixtures ==========

@pytest.fixture
def temp_db_path():
    """Create a temporary database path"""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp) / "test_nlq.db"


@pytest.fixture
def mock_paths(temp_db_path):
    """Patch PATHS to use temporary database"""
    mock = MagicMock()
    mock.app_db = temp_db_path
    return mock


@pytest.fixture
def nlq_service(mock_paths):
    """Create NLQService with mocked dependencies"""
    with patch('api.services.nlq_service.PATHS', mock_paths):
        from api.services.nlq_service import NLQService
        service = NLQService()
        yield service


@pytest.fixture
def sample_schema():
    """Sample schema for testing"""
    return {
        "tables": ["products"],
        "table_name": "products",
        "schema": [
            {"name": "id", "type": "INTEGER"},
            {"name": "name", "type": "TEXT"},
            {"name": "price", "type": "REAL"},
            {"name": "category", "type": "TEXT"},
            {"name": "stock", "type": "INTEGER"}
        ],
        "sample_rows": [
            {"id": 1, "name": "Widget", "price": 9.99, "category": "Tools", "stock": 100},
            {"id": 2, "name": "Gadget", "price": 19.99, "category": "Electronics", "stock": 50},
            {"id": 3, "name": "Gizmo", "price": 14.99, "category": "Tools", "stock": 75}
        ]
    }


# ========== History Schema Tests ==========

class TestNLQHistorySchema:
    """Tests for NLQ history schema and persistence"""

    def test_ensure_history_schema_creates_table(self, mock_paths):
        """Test _ensure_nlq_history_schema creates table"""
        with patch('api.services.nlq_service.PATHS', mock_paths):
            from api.services.nlq_service import _ensure_nlq_history_schema

            _ensure_nlq_history_schema()

            # Verify table exists
            conn = sqlite3.connect(str(mock_paths.app_db))
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='nlq_history'"
            )
            assert cursor.fetchone() is not None
            conn.close()

    def test_ensure_history_schema_is_idempotent(self, mock_paths):
        """Test schema creation is idempotent"""
        with patch('api.services.nlq_service.PATHS', mock_paths):
            from api.services.nlq_service import _ensure_nlq_history_schema

            # Call multiple times - should not raise
            _ensure_nlq_history_schema()
            _ensure_nlq_history_schema()
            _ensure_nlq_history_schema()

    def test_save_nlq_history_basic(self, mock_paths):
        """Test saving NLQ history"""
        with patch('api.services.nlq_service.PATHS', mock_paths):
            from api.services.nlq_service import _save_nlq_history

            _save_nlq_history(
                user_id="user123",
                question="What is the total sales?",
                sql="SELECT SUM(price) FROM products",
                summary="Total sales is $1000"
            )

            # Verify saved
            conn = sqlite3.connect(str(mock_paths.app_db))
            cursor = conn.execute(
                "SELECT user_id, question, sql, summary FROM nlq_history"
            )
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "user123"
            assert row[1] == "What is the total sales?"
            assert row[2] == "SELECT SUM(price) FROM products"
            conn.close()

    def test_save_nlq_history_null_summary(self, mock_paths):
        """Test saving history with null summary"""
        with patch('api.services.nlq_service.PATHS', mock_paths):
            from api.services.nlq_service import _save_nlq_history

            _save_nlq_history(
                user_id="user123",
                question="Query",
                sql="SELECT * FROM products",
                summary=None
            )

            conn = sqlite3.connect(str(mock_paths.app_db))
            cursor = conn.execute(
                "SELECT summary FROM nlq_history"
            )
            row = cursor.fetchone()
            assert row[0] is None
            conn.close()

    def test_save_nlq_history_handles_errors(self, mock_paths):
        """Test history save handles errors gracefully"""
        with patch('api.services.nlq_service.PATHS', mock_paths):
            from api.services.nlq_service import _save_nlq_history

            # Make database read-only by using invalid path
            mock_paths.app_db = Path("/nonexistent/path/db.sqlite")

            # Should not raise - best effort
            _save_nlq_history(
                user_id="user123",
                question="Query",
                sql="SELECT 1",
                summary=None
            )


# ========== SQL Extraction Tests ==========

class TestSQLExtraction:
    """Tests for _extract_sql method"""

    def test_extract_sql_plain(self, nlq_service):
        """Test extracting plain SQL"""
        raw = "SELECT * FROM products WHERE price > 10"
        result = nlq_service._extract_sql(raw)
        assert result == "SELECT * FROM products WHERE price > 10"

    def test_extract_sql_from_markdown(self, nlq_service):
        """Test extracting SQL from markdown code block"""
        raw = """Here is the query:

```sql
SELECT name, price FROM products
WHERE category = 'Tools'
```

This will get all tools."""

        result = nlq_service._extract_sql(raw)
        assert "SELECT" in result
        assert "FROM products" in result
        assert "```" not in result

    def test_extract_sql_removes_comments(self, nlq_service):
        """Test SQL comments are removed"""
        raw = """SELECT * FROM products -- get all products
WHERE price > 10 /* filter expensive */"""

        result = nlq_service._extract_sql(raw)
        assert "--" not in result
        assert "/*" not in result
        assert "SELECT" in result

    def test_extract_sql_normalizes_whitespace(self, nlq_service):
        """Test whitespace is normalized"""
        raw = """SELECT    *
        FROM    products
        WHERE   price   >   10"""

        result = nlq_service._extract_sql(raw)
        # Should be single-line with normalized spaces
        assert "\n" not in result
        assert "  " not in result  # No double spaces

    def test_extract_sql_empty_returns_empty(self, nlq_service):
        """Test empty input returns empty"""
        result = nlq_service._extract_sql("")
        assert result == ""

    def test_extract_sql_only_comments(self, nlq_service):
        """Test input with only comments returns empty"""
        raw = "-- This is just a comment\n/* Another comment */"
        result = nlq_service._extract_sql(raw)
        assert result.strip() == ""


# ========== SQL Validation Tests ==========

class TestSQLValidation:
    """Tests for _validate_sql method"""

    @pytest.fixture
    def mock_validator(self, nlq_service):
        """Mock SQL validator"""
        mock = MagicMock()
        mock.validate_sql.return_value = (True, [], [])
        nlq_service.sql_validator = mock
        return mock

    def test_validate_sql_valid_select(self, nlq_service, mock_validator, sample_schema):
        """Test valid SELECT query passes"""
        sql = "SELECT * FROM products WHERE price > 10"
        result = nlq_service._validate_sql(
            sql=sql,
            allowed_tables=sample_schema["tables"],
            schema=sample_schema["schema"]
        )

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_sql_blocks_drop(self, nlq_service, mock_validator, sample_schema):
        """Test DROP statements are blocked"""
        sql = "DROP TABLE products"
        result = nlq_service._validate_sql(
            sql=sql,
            allowed_tables=sample_schema["tables"],
            schema=sample_schema["schema"]
        )

        assert result["valid"] is False
        assert any("DROP" in e for e in result["errors"])

    def test_validate_sql_blocks_delete(self, nlq_service, mock_validator, sample_schema):
        """Test DELETE statements are blocked"""
        sql = "DELETE FROM products WHERE id = 1"
        result = nlq_service._validate_sql(
            sql=sql,
            allowed_tables=sample_schema["tables"],
            schema=sample_schema["schema"]
        )

        assert result["valid"] is False
        assert any("DELETE" in e for e in result["errors"])

    def test_validate_sql_blocks_update(self, nlq_service, mock_validator, sample_schema):
        """Test UPDATE statements are blocked"""
        sql = "UPDATE products SET price = 0"
        result = nlq_service._validate_sql(
            sql=sql,
            allowed_tables=sample_schema["tables"],
            schema=sample_schema["schema"]
        )

        assert result["valid"] is False
        assert any("UPDATE" in e for e in result["errors"])

    def test_validate_sql_blocks_insert(self, nlq_service, mock_validator, sample_schema):
        """Test INSERT statements are blocked"""
        sql = "INSERT INTO products VALUES (1, 'Test', 10)"
        result = nlq_service._validate_sql(
            sql=sql,
            allowed_tables=sample_schema["tables"],
            schema=sample_schema["schema"]
        )

        assert result["valid"] is False
        assert any("INSERT" in e for e in result["errors"])

    def test_validate_sql_blocks_sqlite_specific(self, nlq_service, mock_validator, sample_schema):
        """Test SQLite-specific dangerous keywords are blocked"""
        dangerous_sqls = [
            "ATTACH DATABASE 'evil.db' AS evil",
            "DETACH DATABASE main",
            "PRAGMA table_info(products)",
            "VACUUM",
            "REINDEX products"
        ]

        for sql in dangerous_sqls:
            result = nlq_service._validate_sql(
                sql=sql,
                allowed_tables=sample_schema["tables"],
                schema=sample_schema["schema"]
            )
            assert result["valid"] is False, f"Should block: {sql}"

    def test_validate_sql_blocks_unknown_table(self, nlq_service, mock_validator, sample_schema):
        """Test unknown tables are blocked"""
        sql = "SELECT * FROM users"  # 'users' not in allowed_tables
        result = nlq_service._validate_sql(
            sql=sql,
            allowed_tables=sample_schema["tables"],
            schema=sample_schema["schema"]
        )

        assert result["valid"] is False
        assert any("Unknown table" in e for e in result["errors"])

    def test_validate_sql_warns_union(self, nlq_service, mock_validator, sample_schema):
        """Test UNION generates warning"""
        sql = "SELECT * FROM products UNION SELECT * FROM products"
        result = nlq_service._validate_sql(
            sql=sql,
            allowed_tables=sample_schema["tables"],
            schema=sample_schema["schema"]
        )

        # UNION should generate warning, not error
        assert any("UNION" in w for w in result["warnings"])

    def test_validate_sql_warns_unknown_column(self, nlq_service, mock_validator, sample_schema):
        """Test unknown columns generate warnings"""
        sql = "SELECT nonexistent_column FROM products"
        result = nlq_service._validate_sql(
            sql=sql,
            allowed_tables=sample_schema["tables"],
            schema=sample_schema["schema"]
        )

        # Should warn about potential unknown column
        assert any("may not exist" in w for w in result["warnings"])


# ========== LIMIT Injection Tests ==========

class TestEnsureLimit:
    """Tests for _ensure_limit method"""

    def test_ensure_limit_adds_when_missing(self, nlq_service):
        """Test LIMIT is added when missing"""
        sql = "SELECT * FROM products"
        result = nlq_service._ensure_limit(sql, 100)

        assert "LIMIT 100" in result

    def test_ensure_limit_preserves_existing(self, nlq_service):
        """Test existing LIMIT is preserved if within max"""
        sql = "SELECT * FROM products LIMIT 50"
        result = nlq_service._ensure_limit(sql, 100)

        assert "LIMIT 50" in result

    def test_ensure_limit_caps_excessive(self, nlq_service, mock_paths):
        """Test excessive LIMIT is capped"""
        with patch('api.services.nlq_service.MAX_RESULT_ROWS', 1000):
            from api.services.nlq_service import NLQService
            service = NLQService()

            sql = "SELECT * FROM products LIMIT 10000"
            result = service._ensure_limit(sql, 100)

            # Should be capped to MAX_RESULT_ROWS
            assert "LIMIT 1000" in result

    def test_ensure_limit_removes_semicolon(self, nlq_service):
        """Test semicolon is handled"""
        sql = "SELECT * FROM products;"
        result = nlq_service._ensure_limit(sql, 100)

        assert "LIMIT 100" in result
        assert not result.endswith(";LIMIT")

    def test_ensure_limit_case_insensitive(self, nlq_service):
        """Test LIMIT detection is case insensitive"""
        sql = "SELECT * FROM products limit 50"
        result = nlq_service._ensure_limit(sql, 100)

        # Should preserve existing limit
        assert "50" in result or "LIMIT 50" in result.upper()


# ========== Prompt Building Tests ==========

class TestBuildPrompt:
    """Tests for _build_prompt method"""

    def test_build_prompt_includes_question(self, nlq_service, sample_schema):
        """Test prompt includes the question"""
        prompt = nlq_service._build_prompt("What are the cheapest products?", sample_schema)

        assert "What are the cheapest products?" in prompt

    def test_build_prompt_includes_table_name(self, nlq_service, sample_schema):
        """Test prompt includes table name"""
        prompt = nlq_service._build_prompt("Query", sample_schema)

        assert "products" in prompt

    def test_build_prompt_includes_columns(self, nlq_service, sample_schema):
        """Test prompt includes column definitions"""
        prompt = nlq_service._build_prompt("Query", sample_schema)

        assert "id" in prompt
        assert "name" in prompt
        assert "price" in prompt
        assert "INTEGER" in prompt or "TEXT" in prompt or "REAL" in prompt

    def test_build_prompt_includes_sample_rows(self, nlq_service, sample_schema):
        """Test prompt includes sample rows"""
        prompt = nlq_service._build_prompt("Query", sample_schema)

        assert "Sample data" in prompt
        assert "Widget" in prompt  # From sample data

    def test_build_prompt_includes_constraints(self, nlq_service, sample_schema):
        """Test prompt includes constraints"""
        prompt = nlq_service._build_prompt("Query", sample_schema)

        assert "SELECT only" in prompt
        assert "LIMIT" in prompt

    def test_build_prompt_without_sample_rows(self, nlq_service):
        """Test prompt handles missing sample rows"""
        schema = {
            "tables": ["products"],
            "table_name": "products",
            "schema": [{"name": "id", "type": "INTEGER"}],
            "sample_rows": []
        }

        prompt = nlq_service._build_prompt("Query", schema)

        assert "products" in prompt
        # Should not have sample data section
        assert "Sample data" not in prompt or "[]" in prompt


# ========== Summary Generation Tests ==========

class TestSummaryGeneration:
    """Tests for _generate_summary method"""

    @pytest.mark.asyncio
    async def test_summary_no_results(self, nlq_service):
        """Test summary for empty results"""
        results = {"row_count": 0, "columns": [], "rows": []}

        summary = await nlq_service._generate_summary("Query", results)

        assert "No results found" in summary

    @pytest.mark.asyncio
    async def test_summary_single_result(self, nlq_service):
        """Test summary for single result"""
        results = {
            "row_count": 1,
            "columns": ["name", "price"],
            "rows": [{"name": "Widget", "price": 9.99}]
        }

        summary = await nlq_service._generate_summary("Query", results)

        assert "1 result" in summary
        assert "2 column" in summary

    @pytest.mark.asyncio
    async def test_summary_multiple_results(self, nlq_service):
        """Test summary for multiple results"""
        results = {
            "row_count": 5,
            "columns": ["name", "price"],
            "rows": [
                {"name": "A", "price": 10},
                {"name": "B", "price": 20},
                {"name": "C", "price": 30},
                {"name": "D", "price": 40},
                {"name": "E", "price": 50}
            ]
        }

        summary = await nlq_service._generate_summary("Query", results)

        assert "5 results" in summary

    @pytest.mark.asyncio
    async def test_summary_includes_numeric_range(self, nlq_service):
        """Test summary includes numeric column range"""
        results = {
            "row_count": 3,
            "columns": ["name", "price"],
            "rows": [
                {"name": "A", "price": 10},
                {"name": "B", "price": 50},
                {"name": "C", "price": 30}
            ]
        }

        summary = await nlq_service._generate_summary("Query", results)

        # Should mention range
        assert "10" in summary and "50" in summary


# ========== Singleton Tests ==========

class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_nlq_service_returns_instance(self, mock_paths):
        """Test get_nlq_service returns instance"""
        with patch('api.services.nlq_service.PATHS', mock_paths):
            import api.services.nlq_service as nlq_module
            nlq_module._nlq_service = None  # Reset singleton

            from api.services.nlq_service import get_nlq_service, NLQService

            service = get_nlq_service()
            assert isinstance(service, NLQService)

    def test_get_nlq_service_returns_same_instance(self, mock_paths):
        """Test get_nlq_service returns same instance"""
        with patch('api.services.nlq_service.PATHS', mock_paths):
            import api.services.nlq_service as nlq_module
            nlq_module._nlq_service = None  # Reset singleton

            from api.services.nlq_service import get_nlq_service

            service1 = get_nlq_service()
            service2 = get_nlq_service()

            assert service1 is service2


# ========== Lazy Initialization Tests ==========

class TestLazyInit:
    """Tests for lazy initialization of dependencies"""

    def test_ollama_client_lazy_init(self, nlq_service):
        """Test Ollama client is lazily initialized"""
        assert nlq_service.ollama_client is None

        # Patch at the source module where the import happens
        with patch('api.services.chat.streaming.OllamaClient') as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # First call should create client
            client = nlq_service._get_ollama_client()
            assert client is mock_instance
            mock_class.assert_called_once()

    def test_data_engine_lazy_init(self, nlq_service):
        """Test DataEngine is lazily initialized"""
        assert nlq_service.data_engine is None

        mock_engine = MagicMock()
        with patch.dict('sys.modules', {'api.data_engine': MagicMock(DataEngine=lambda: mock_engine)}):
            engine = nlq_service._get_data_engine()
            # After call, should be set
            assert nlq_service.data_engine is not None

    def test_sql_validator_lazy_init(self, nlq_service):
        """Test SQLValidator is lazily initialized"""
        assert nlq_service.sql_validator is None

        mock_validator = MagicMock()
        with patch.dict('sys.modules', {'sql_validator': MagicMock(SQLValidator=lambda: mock_validator)}):
            validator = nlq_service._get_sql_validator()
            assert nlq_service.sql_validator is not None


# ========== Process NLQ Integration Tests ==========

class TestProcessNLQ:
    """Integration tests for process_nlq method"""

    @pytest.mark.asyncio
    async def test_process_nlq_no_schema(self, nlq_service):
        """Test process_nlq handles missing schema"""
        nlq_service._get_schema = AsyncMock(return_value=None)

        result = await nlq_service.process_nlq("What products?")

        assert "error" in result
        assert "not found" in result["error"].lower() or "no schema" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_process_nlq_sql_generation_error(self, nlq_service, sample_schema):
        """Test process_nlq handles SQL generation error"""
        nlq_service._get_schema = AsyncMock(return_value=sample_schema)
        nlq_service._generate_sql = AsyncMock(return_value={
            "error": "LLM unavailable",
            "suggestion": "Check Ollama"
        })

        result = await nlq_service.process_nlq("What products?")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_process_nlq_validation_failure(self, nlq_service, sample_schema):
        """Test process_nlq handles validation failure"""
        nlq_service._get_schema = AsyncMock(return_value=sample_schema)
        nlq_service._generate_sql = AsyncMock(return_value={"sql": "DROP TABLE products"})

        # Mock validator to return errors
        mock_validator = MagicMock()
        mock_validator.validate_sql.return_value = (False, ["DROP not allowed"], [])
        nlq_service.sql_validator = mock_validator

        result = await nlq_service.process_nlq("Delete everything")

        assert "error" in result
        assert "validation" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_process_nlq_success(self, nlq_service, sample_schema):
        """Test successful process_nlq flow"""
        nlq_service._get_schema = AsyncMock(return_value=sample_schema)
        nlq_service._generate_sql = AsyncMock(return_value={"sql": "SELECT * FROM products"})

        # Mock validator
        mock_validator = MagicMock()
        mock_validator.validate_sql.return_value = (True, [], [])
        nlq_service.sql_validator = mock_validator

        # Mock data engine
        mock_engine = MagicMock()
        mock_engine.execute_sql.return_value = {
            "rows": [{"id": 1, "name": "Widget"}],
            "row_count": 1,
            "columns": ["id", "name"],
            "execution_time": 0.1
        }
        nlq_service.data_engine = mock_engine

        result = await nlq_service.process_nlq(
            "What products?",
            user_id="user123"
        )

        assert "sql" in result
        assert "results" in result
        assert "summary" in result
        assert result["row_count"] == 1

    @pytest.mark.asyncio
    async def test_process_nlq_timeout(self, nlq_service, sample_schema):
        """Test process_nlq handles execution timeout"""
        nlq_service._get_schema = AsyncMock(return_value=sample_schema)
        nlq_service._generate_sql = AsyncMock(return_value={"sql": "SELECT * FROM products"})

        # Mock validator
        mock_validator = MagicMock()
        mock_validator.validate_sql.return_value = (True, [], [])
        nlq_service.sql_validator = mock_validator

        # Mock data engine with synchronous sleep (execute_sql is called in thread)
        def slow_execute(sql):
            import time
            time.sleep(10)  # Will be interrupted by timeout
            return {"rows": [], "row_count": 0, "columns": []}

        mock_engine = MagicMock()
        mock_engine.execute_sql.side_effect = slow_execute
        nlq_service.data_engine = mock_engine

        # Patch timeout to be very short
        with patch('api.services.nlq_service.MAX_SQL_TIMEOUT', 0.01):
            result = await nlq_service.process_nlq("Complex query")

        assert "error" in result
        assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_process_nlq_truncates_large_results(self, nlq_service, sample_schema):
        """Test large result sets are truncated"""
        nlq_service._get_schema = AsyncMock(return_value=sample_schema)
        nlq_service._generate_sql = AsyncMock(return_value={"sql": "SELECT * FROM products"})

        # Mock validator
        mock_validator = MagicMock()
        mock_validator.validate_sql.return_value = (True, [], [])
        nlq_service.sql_validator = mock_validator

        # Mock data engine to return large result set
        large_rows = [{"id": i} for i in range(2000)]
        mock_engine = MagicMock()
        mock_engine.execute_sql.return_value = {
            "rows": large_rows,
            "row_count": 2000,
            "columns": ["id"],
            "execution_time": 0.1
        }
        nlq_service.data_engine = mock_engine

        with patch('api.services.nlq_service.MAX_RESULT_ROWS', 1000):
            result = await nlq_service.process_nlq("Get all")

        assert result["row_count"] == 1000
        assert result["metadata"]["truncated"] is True


# ========== Schema Caching Tests ==========

class TestSchemaCache:
    """Tests for schema caching"""

    @pytest.mark.asyncio
    async def test_schema_cache_miss(self, nlq_service):
        """Test schema cache miss fetches from engine"""
        from api.services.nlq_service import _SCHEMA_CACHE
        _SCHEMA_CACHE.clear()

        mock_engine = MagicMock()
        mock_engine.get_dataset_metadata.return_value = {
            "table_name": "products",
            "schema": [{"name": "id", "type": "INTEGER"}]
        }
        mock_engine.execute_sql.return_value = {"rows": []}
        nlq_service.data_engine = mock_engine

        with patch('api.security.sql_safety.quote_identifier', return_value='"products"'):
            schema = await nlq_service._get_schema("dataset123", None)

        assert schema is not None
        assert schema["table_name"] == "products"

    @pytest.mark.asyncio
    async def test_schema_cache_hit(self, nlq_service):
        """Test schema cache hit returns cached data"""
        from api.services.nlq_service import _SCHEMA_CACHE
        import time

        # Pre-populate cache
        cached_schema = {"tables": ["cached_table"], "table_name": "cached_table", "schema": []}
        _SCHEMA_CACHE["dataset_cached"] = (cached_schema, time.time())

        schema = await nlq_service._get_schema("dataset_cached", None)

        assert schema["table_name"] == "cached_table"

    @pytest.mark.asyncio
    async def test_schema_cache_expired(self, nlq_service):
        """Test expired cache triggers refetch"""
        from api.services.nlq_service import _SCHEMA_CACHE, SCHEMA_CACHE_TTL
        import time

        # Pre-populate with expired cache
        old_schema = {"tables": ["old_table"], "table_name": "old_table", "schema": []}
        _SCHEMA_CACHE["dataset_expired"] = (old_schema, time.time() - SCHEMA_CACHE_TTL - 100)

        mock_engine = MagicMock()
        mock_engine.get_dataset_metadata.return_value = {
            "table_name": "fresh_table",
            "schema": [{"name": "id", "type": "INTEGER"}]
        }
        mock_engine.execute_sql.return_value = {"rows": []}
        nlq_service.data_engine = mock_engine

        with patch('api.security.sql_safety.quote_identifier', return_value='"fresh_table"'):
            schema = await nlq_service._get_schema("dataset_expired", None)

        assert schema["table_name"] == "fresh_table"


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_extract_sql_mixed_case_markdown(self, nlq_service):
        """Test SQL extraction handles mixed case markdown"""
        raw = """```SQL
SELECT * FROM products
```"""
        result = nlq_service._extract_sql(raw)
        assert "SELECT" in result
        assert "```" not in result

    def test_validate_sql_case_insensitive_keywords(self, nlq_service, sample_schema):
        """Test dangerous keyword detection is case insensitive"""
        mock_validator = MagicMock()
        mock_validator.validate_sql.return_value = (True, [], [])
        nlq_service.sql_validator = mock_validator

        # Lowercase dangerous keyword
        result = nlq_service._validate_sql(
            "drop table products",
            sample_schema["tables"],
            sample_schema["schema"]
        )
        assert result["valid"] is False

    def test_build_prompt_unicode_question(self, nlq_service, sample_schema):
        """Test prompt handles unicode question"""
        prompt = nlq_service._build_prompt("查询所有产品", sample_schema)

        assert "查询所有产品" in prompt

    @pytest.mark.asyncio
    async def test_summary_handles_none_values(self, nlq_service):
        """Test summary handles None values in rows"""
        results = {
            "row_count": 2,
            "columns": ["name", "price"],
            "rows": [
                {"name": "Widget", "price": None},
                {"name": "Gadget", "price": 10}
            ]
        }

        summary = await nlq_service._generate_summary("Query", results)
        # Should not raise
        assert "2 results" in summary

    def test_ensure_limit_with_offset(self, nlq_service):
        """Test LIMIT with OFFSET is handled"""
        sql = "SELECT * FROM products LIMIT 10 OFFSET 5"
        result = nlq_service._ensure_limit(sql, 100)

        # Should preserve existing limit
        assert "LIMIT 10" in result
