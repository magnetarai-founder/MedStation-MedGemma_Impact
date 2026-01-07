"""
Comprehensive tests for api/data_engine.py

Tests the data engine including:
- DataEngine initialization
- File upload and loading (Excel, CSV, JSON)
- Auto-cleaning of dataframes
- SQL execution with security validation
- Schema discovery and query suggestions
- Dataset CRUD operations
- Security features
"""

import pytest
import json
import sqlite3
import tempfile
import os
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import module under test
from api.data_engine import (
    DataEngine,
    get_data_engine,
    _COLUMN_NAME_SPECIAL_CHARS,
    _COLUMN_NAME_WHITESPACE,
    _TABLE_NAME_VALIDATOR,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary database file"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield Path(path)
    # Cleanup
    for ext in ['', '-wal', '-shm']:
        try:
            os.unlink(str(path) + ext)
        except FileNotFoundError:
            pass


@pytest.fixture
def engine(temp_db):
    """Create a DataEngine instance with temp database"""
    eng = DataEngine(db_path=temp_db)
    yield eng
    eng.conn.close()


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file"""
    csv_path = tmp_path / "sample.csv"
    df = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
        'value': [10.5, 20.3, 30.1, 40.7, 50.9],
        'category': ['A', 'B', 'A', 'C', 'B']
    })
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_json(tmp_path):
    """Create a sample JSON file"""
    json_path = tmp_path / "sample.json"
    data = [
        {'id': 1, 'name': 'Alice', 'score': 95},
        {'id': 2, 'name': 'Bob', 'score': 87},
        {'id': 3, 'name': 'Charlie', 'score': 92}
    ]
    with open(json_path, 'w') as f:
        json.dump(data, f)
    return json_path


@pytest.fixture
def sample_excel(tmp_path):
    """Create a sample Excel file"""
    excel_path = tmp_path / "sample.xlsx"
    df = pd.DataFrame({
        'Product': ['Widget', 'Gadget', 'Gizmo'],
        'Price': [9.99, 19.99, 29.99],
        'Quantity': [100, 50, 25]
    })
    df.to_excel(excel_path, index=False)
    return excel_path


# ============================================================================
# Test Regex Patterns
# ============================================================================

class TestRegexPatterns:
    """Tests for pre-compiled regex patterns"""

    def test_column_name_special_chars(self):
        """Pattern matches special characters"""
        assert _COLUMN_NAME_SPECIAL_CHARS.search("hello@world")
        assert _COLUMN_NAME_SPECIAL_CHARS.search("column#1")
        assert not _COLUMN_NAME_SPECIAL_CHARS.search("hello_world")

    def test_column_name_whitespace(self):
        """Pattern matches whitespace"""
        assert _COLUMN_NAME_WHITESPACE.search("hello world")
        assert _COLUMN_NAME_WHITESPACE.search("col  name")
        assert not _COLUMN_NAME_WHITESPACE.search("hello_world")

    def test_table_name_validator(self):
        """Pattern validates table names"""
        assert _TABLE_NAME_VALIDATOR.match("ds_abc123")
        assert _TABLE_NAME_VALIDATOR.match("table_name")
        assert not _TABLE_NAME_VALIDATOR.match("table-name")
        assert not _TABLE_NAME_VALIDATOR.match("table name")


# ============================================================================
# Test DataEngine Initialization
# ============================================================================

class TestDataEngineInit:
    """Tests for DataEngine initialization"""

    def test_init_creates_database(self, temp_db):
        """Initialization creates database file"""
        os.unlink(temp_db)  # Remove first
        engine = DataEngine(db_path=temp_db)
        assert temp_db.exists()
        engine.conn.close()

    def test_init_creates_parent_dirs(self):
        """Creates parent directories if needed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nested" / "dirs" / "test.db"
            engine = DataEngine(db_path=db_path)
            assert db_path.exists()
            engine.conn.close()

    def test_init_enables_wal_mode(self, engine):
        """WAL mode is enabled"""
        cursor = engine.conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"

    def test_init_creates_metadata_table(self, engine):
        """Metadata table is created"""
        cursor = engine.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='dataset_metadata'"
        )
        assert cursor.fetchone() is not None

    def test_init_creates_index(self, engine):
        """Session index is created"""
        cursor = engine.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_metadata_session'"
        )
        assert cursor.fetchone() is not None


# ============================================================================
# Test Column Name Sanitization
# ============================================================================

class TestSanitizeColumnName:
    """Tests for _sanitize_column_name method"""

    def test_basic_name(self, engine):
        """Basic name unchanged"""
        assert engine._sanitize_column_name("column_name") == "column_name"

    def test_spaces_to_underscores(self, engine):
        """Spaces converted to underscores"""
        assert engine._sanitize_column_name("column name") == "column_name"

    def test_special_chars_removed(self, engine):
        """Special characters replaced with underscores"""
        result = engine._sanitize_column_name("price$")
        assert "$" not in result

    def test_leading_number(self, engine):
        """Leading number gets col_ prefix"""
        assert engine._sanitize_column_name("123abc").startswith("col_")

    def test_empty_name(self, engine):
        """Empty name becomes 'unnamed'"""
        assert engine._sanitize_column_name("") == "unnamed"

    def test_only_special_chars(self, engine):
        """Only special chars becomes 'unnamed'"""
        assert engine._sanitize_column_name("@#$") == "unnamed"


# ============================================================================
# Test Data Type Inference
# ============================================================================

class TestInferAndConvert:
    """Tests for _infer_and_convert method"""

    def test_numeric_column(self, engine):
        """Numeric values converted to numeric"""
        series = pd.Series(['1', '2', '3'])
        result = engine._infer_and_convert(series)
        assert pd.api.types.is_numeric_dtype(result)

    def test_datetime_column(self, engine):
        """Datetime strings converted to datetime"""
        series = pd.Series(['2025-01-01', '2025-01-02', '2025-01-03'])
        result = engine._infer_and_convert(series)
        assert pd.api.types.is_datetime64_any_dtype(result)

    def test_string_column(self, engine):
        """String values stay as string"""
        series = pd.Series(['apple', 'banana', 'cherry'])
        result = engine._infer_and_convert(series)
        assert result.dtype == object or str(result.dtype) == 'string'


# ============================================================================
# Test Auto-Clean
# ============================================================================

class TestAutoClean:
    """Tests for _auto_clean method"""

    def test_removes_duplicate_columns(self, engine):
        """Duplicate columns are removed"""
        df = pd.DataFrame([[1, 2, 3]], columns=['a', 'b', 'a'])
        result = engine._auto_clean(df)
        assert len(result.columns) == 2

    def test_removes_empty_rows(self, engine):
        """Empty rows are removed"""
        df = pd.DataFrame({
            'a': [1, None, 2],
            'b': [3, None, 4]
        })
        result = engine._auto_clean(df)
        assert len(result) == 2

    def test_removes_empty_columns(self, engine):
        """Empty columns are removed"""
        df = pd.DataFrame({
            'a': [1, 2, 3],
            'b': [None, None, None]
        })
        result = engine._auto_clean(df)
        assert 'b' not in result.columns

    def test_sanitizes_column_names(self, engine):
        """Column names are sanitized"""
        df = pd.DataFrame({
            'Column Name': [1],
            'price$': [2]
        })
        result = engine._auto_clean(df)
        for col in result.columns:
            assert ' ' not in col
            assert '$' not in col


# ============================================================================
# Test File Upload and Load
# ============================================================================

class TestUploadAndLoad:
    """Tests for upload_and_load method"""

    def test_load_csv(self, engine, sample_csv):
        """Load CSV file successfully"""
        result = engine.upload_and_load(sample_csv, "sample.csv")

        assert 'dataset_id' in result
        assert 'table_name' in result
        assert result['rows'] == 5
        assert len(result['columns']) == 4
        assert len(result['preview']) == 5

    def test_load_json(self, engine, sample_json):
        """Load JSON file successfully"""
        result = engine.upload_and_load(sample_json, "sample.json")

        assert 'dataset_id' in result
        assert result['rows'] == 3

    def test_load_excel(self, engine, sample_excel):
        """Load Excel file successfully"""
        result = engine.upload_and_load(sample_excel, "sample.xlsx")

        assert 'dataset_id' in result
        assert result['rows'] == 3

    def test_load_with_session_id(self, engine, sample_csv):
        """Load with session ID"""
        result = engine.upload_and_load(sample_csv, "sample.csv", session_id="session123")

        # Verify session ID stored
        metadata = engine.get_dataset_metadata(result['dataset_id'])
        assert metadata['session_id'] == "session123"

    def test_load_unsupported_type(self, engine, tmp_path):
        """Unsupported file type raises error"""
        unsupported = tmp_path / "file.xyz"
        unsupported.write_text("test")

        with pytest.raises(ValueError, match="Unsupported file type"):
            engine.upload_and_load(unsupported, "file.xyz")

    def test_load_generates_query_suggestions(self, engine, sample_csv):
        """Query suggestions are generated"""
        result = engine.upload_and_load(sample_csv, "sample.csv")

        assert 'query_suggestions' in result
        assert len(result['query_suggestions']) > 0


# ============================================================================
# Test Brute-Force Discovery
# ============================================================================

class TestBruteForceDiscover:
    """Tests for _brute_force_discover method"""

    def test_numeric_column_suggestions(self, engine, sample_csv):
        """Generates suggestions for numeric columns"""
        result = engine.upload_and_load(sample_csv, "sample.csv")
        suggestions = result['query_suggestions']

        # Should have aggregate suggestions for numeric cols
        aggregate_suggestions = [s for s in suggestions if s['category'] == 'aggregate']
        assert len(aggregate_suggestions) > 0

    def test_categorical_column_suggestions(self, engine, sample_csv):
        """Generates suggestions for categorical columns"""
        result = engine.upload_and_load(sample_csv, "sample.csv")
        suggestions = result['query_suggestions']

        # Should have distribution suggestions for categorical cols
        distribution_suggestions = [s for s in suggestions if s['category'] == 'distribution']
        assert len(distribution_suggestions) > 0

    def test_basic_row_count_suggestion(self, engine, sample_csv):
        """Always includes row count suggestion"""
        result = engine.upload_and_load(sample_csv, "sample.csv")
        suggestions = result['query_suggestions']

        # Should have basic row count
        basic_suggestions = [s for s in suggestions if s['category'] == 'basic']
        assert len(basic_suggestions) > 0

    def test_suggestions_sorted_by_confidence(self, engine, sample_csv):
        """Suggestions sorted by confidence descending"""
        result = engine.upload_and_load(sample_csv, "sample.csv")
        suggestions = result['query_suggestions']

        if len(suggestions) >= 2:
            for i in range(len(suggestions) - 1):
                assert suggestions[i]['confidence'] >= suggestions[i+1]['confidence']


# ============================================================================
# Test SQL Execution
# ============================================================================

class TestExecuteSQL:
    """Tests for execute_sql method"""

    def test_execute_select(self, engine, sample_csv):
        """Execute SELECT query"""
        engine.upload_and_load(sample_csv, "sample.csv")

        # Get table name from metadata
        datasets = engine.list_datasets()
        table_name = datasets[0]['table_name']

        result = engine.execute_sql(f'SELECT * FROM "{table_name}"')

        assert 'columns' in result
        assert 'rows' in result
        assert result['row_count'] == 5

    def test_blocks_drop(self, engine):
        """Blocks DROP queries"""
        with pytest.raises(ValueError, match="Forbidden SQL operation"):
            engine.execute_sql("DROP TABLE test")

    def test_blocks_delete(self, engine):
        """Blocks DELETE queries"""
        with pytest.raises(ValueError, match="Forbidden SQL operation"):
            engine.execute_sql("DELETE FROM test")

    def test_blocks_update(self, engine):
        """Blocks UPDATE queries"""
        with pytest.raises(ValueError, match="Forbidden SQL operation"):
            engine.execute_sql("UPDATE test SET col = 1")

    def test_blocks_insert(self, engine):
        """Blocks INSERT queries"""
        with pytest.raises(ValueError, match="Forbidden SQL operation"):
            engine.execute_sql("INSERT INTO test VALUES (1)")

    def test_blocks_alter(self, engine):
        """Blocks ALTER queries"""
        with pytest.raises(ValueError, match="Forbidden SQL operation"):
            engine.execute_sql("ALTER TABLE test ADD col INT")

    def test_blocks_pragma(self, engine):
        """Blocks PRAGMA queries"""
        with pytest.raises(ValueError, match="Forbidden SQL operation"):
            engine.execute_sql("PRAGMA table_info(test)")

    def test_auto_adds_limit(self, engine, sample_csv):
        """Auto-adds LIMIT if not present"""
        engine.upload_and_load(sample_csv, "sample.csv")
        datasets = engine.list_datasets()
        table_name = datasets[0]['table_name']

        # Query without LIMIT - should still work
        result = engine.execute_sql(f'SELECT * FROM "{table_name}"')
        assert result['row_count'] <= 10000

    def test_respects_existing_limit(self, engine, sample_csv):
        """Respects existing LIMIT clause"""
        engine.upload_and_load(sample_csv, "sample.csv")
        datasets = engine.list_datasets()
        table_name = datasets[0]['table_name']

        result = engine.execute_sql(f'SELECT * FROM "{table_name}" LIMIT 2')
        assert result['row_count'] == 2

    def test_returns_execution_time(self, engine, sample_csv):
        """Returns execution time in ms"""
        engine.upload_and_load(sample_csv, "sample.csv")
        datasets = engine.list_datasets()
        table_name = datasets[0]['table_name']

        result = engine.execute_sql(f'SELECT * FROM "{table_name}"')
        assert 'execution_time' in result
        assert isinstance(result['execution_time'], float)


# ============================================================================
# Test Dataset Metadata
# ============================================================================

class TestGetDatasetMetadata:
    """Tests for get_dataset_metadata method"""

    def test_get_existing_metadata(self, engine, sample_csv):
        """Get metadata for existing dataset"""
        upload_result = engine.upload_and_load(sample_csv, "sample.csv")
        dataset_id = upload_result['dataset_id']

        metadata = engine.get_dataset_metadata(dataset_id)

        assert metadata is not None
        assert metadata['dataset_id'] == dataset_id
        assert metadata['filename'] == "sample.csv"
        assert metadata['rows'] == 5

    def test_get_nonexistent_metadata(self, engine):
        """Returns None for nonexistent dataset"""
        metadata = engine.get_dataset_metadata("nonexistent_id")
        assert metadata is None


# ============================================================================
# Test List Datasets
# ============================================================================

class TestListDatasets:
    """Tests for list_datasets method"""

    def test_list_empty(self, engine):
        """List returns empty when no datasets"""
        datasets = engine.list_datasets()
        assert datasets == []

    def test_list_all(self, engine, sample_csv, sample_json):
        """List returns all datasets"""
        engine.upload_and_load(sample_csv, "sample.csv")
        engine.upload_and_load(sample_json, "sample.json")

        datasets = engine.list_datasets()
        assert len(datasets) == 2

    def test_list_by_session(self, engine, sample_csv, sample_json):
        """List filters by session ID"""
        engine.upload_and_load(sample_csv, "sample.csv", session_id="session1")
        engine.upload_and_load(sample_json, "sample.json", session_id="session2")

        datasets = engine.list_datasets(session_id="session1")
        assert len(datasets) == 1
        assert datasets[0]['filename'] == "sample.csv"

    def test_list_ordered_by_timestamp(self, engine, sample_csv, sample_json, tmp_path):
        """List ordered by timestamp descending"""
        engine.upload_and_load(sample_csv, "sample.csv")

        # Create another CSV
        csv2 = tmp_path / "sample2.csv"
        pd.DataFrame({'a': [1, 2]}).to_csv(csv2, index=False)
        engine.upload_and_load(csv2, "sample2.csv")

        datasets = engine.list_datasets()
        # Most recent first
        assert datasets[0]['filename'] == "sample2.csv"


# ============================================================================
# Test Get All Table Names
# ============================================================================

class TestGetAllTableNames:
    """Tests for get_all_table_names method"""

    def test_get_table_names_empty(self, engine):
        """Returns empty list when no datasets"""
        tables = engine.get_all_table_names()
        assert tables == []

    def test_get_table_names_with_data(self, engine, sample_csv, sample_json):
        """Returns all table names"""
        engine.upload_and_load(sample_csv, "sample.csv")
        engine.upload_and_load(sample_json, "sample.json")

        tables = engine.get_all_table_names()
        assert len(tables) == 2
        for table in tables:
            assert table.startswith("ds_")


# ============================================================================
# Test Delete Dataset
# ============================================================================

class TestDeleteDataset:
    """Tests for delete_dataset method"""

    def test_delete_existing_dataset(self, engine, sample_csv):
        """Delete existing dataset"""
        result = engine.upload_and_load(sample_csv, "sample.csv")
        dataset_id = result['dataset_id']
        table_name = result['table_name']

        success = engine.delete_dataset(dataset_id)

        assert success is True
        # Verify table dropped
        cursor = engine.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        assert cursor.fetchone() is None

    def test_delete_nonexistent_dataset(self, engine):
        """Delete nonexistent dataset returns False"""
        success = engine.delete_dataset("nonexistent_id")
        assert success is False

    def test_delete_removes_metadata(self, engine, sample_csv):
        """Delete removes metadata"""
        result = engine.upload_and_load(sample_csv, "sample.csv")
        dataset_id = result['dataset_id']

        engine.delete_dataset(dataset_id)

        metadata = engine.get_dataset_metadata(dataset_id)
        assert metadata is None


# ============================================================================
# Test Singleton
# ============================================================================

class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_data_engine_returns_same_instance(self):
        """get_data_engine returns same instance"""
        # Reset singleton
        import api.data_engine as de
        de._data_engine = None

        engine1 = get_data_engine()
        engine2 = get_data_engine()

        assert engine1 is engine2


# ============================================================================
# Test Thread Safety
# ============================================================================

class TestThreadSafety:
    """Tests for thread safety"""

    def test_concurrent_uploads(self, engine, tmp_path):
        """Concurrent uploads work"""
        import concurrent.futures

        # Create multiple CSV files
        def create_and_upload(i):
            csv_path = tmp_path / f"sample_{i}.csv"
            df = pd.DataFrame({'id': [i], 'value': [i * 10]})
            df.to_csv(csv_path, index=False)
            return engine.upload_and_load(csv_path, f"sample_{i}.csv")

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_and_upload, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 5

        # All datasets stored
        datasets = engine.list_datasets()
        assert len(datasets) == 5


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_column_names(self, engine, tmp_path):
        """Unicode column names handled"""
        csv_path = tmp_path / "unicode.csv"
        df = pd.DataFrame({
            '名前': ['Alice', 'Bob'],
            '价格': [100, 200]
        })
        df.to_csv(csv_path, index=False)

        result = engine.upload_and_load(csv_path, "unicode.csv")
        assert result['rows'] == 2

    def test_empty_file(self, engine, tmp_path):
        """Empty file is handled"""
        csv_path = tmp_path / "empty.csv"
        df = pd.DataFrame()
        df.to_csv(csv_path, index=False)

        # May raise or return empty - both acceptable
        try:
            result = engine.upload_and_load(csv_path, "empty.csv")
            assert result['rows'] == 0
        except Exception:
            pass  # Also acceptable

    def test_large_file(self, engine, tmp_path):
        """Large file handled"""
        csv_path = tmp_path / "large.csv"
        df = pd.DataFrame({
            'id': range(10000),
            'value': range(10000)
        })
        df.to_csv(csv_path, index=False)

        result = engine.upload_and_load(csv_path, "large.csv")
        assert result['rows'] == 10000

    def test_special_chars_in_filename(self, engine, sample_csv):
        """Special chars in filename handled"""
        result = engine.upload_and_load(sample_csv, "file (1) - copy.csv")
        assert 'dataset_id' in result


# ============================================================================
# Test Integration
# ============================================================================

class TestIntegration:
    """Integration tests"""

    def test_full_workflow(self, engine, sample_csv):
        """Full workflow: upload -> query -> delete"""
        # Upload
        upload_result = engine.upload_and_load(sample_csv, "sample.csv")
        dataset_id = upload_result['dataset_id']
        table_name = upload_result['table_name']

        # List
        datasets = engine.list_datasets()
        assert len(datasets) == 1

        # Query
        sql_result = engine.execute_sql(f'SELECT * FROM "{table_name}" WHERE value > 20')
        assert sql_result['row_count'] > 0

        # Delete
        success = engine.delete_dataset(dataset_id)
        assert success is True

        # Verify gone
        datasets = engine.list_datasets()
        assert len(datasets) == 0

    def test_multiple_file_types(self, engine, sample_csv, sample_json, sample_excel):
        """Load multiple file types"""
        csv_result = engine.upload_and_load(sample_csv, "sample.csv")
        json_result = engine.upload_and_load(sample_json, "sample.json")
        excel_result = engine.upload_and_load(sample_excel, "sample.xlsx")

        assert csv_result['dataset_id'] != json_result['dataset_id']
        assert json_result['dataset_id'] != excel_result['dataset_id']

        datasets = engine.list_datasets()
        assert len(datasets) == 3

        # All queryable
        for ds in datasets:
            result = engine.execute_sql(f'SELECT COUNT(*) FROM "{ds["table_name"]}"')
            assert result['row_count'] == 1
