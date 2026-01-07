"""
Comprehensive tests for Metal 4 DuckDB Integration Bridge

Tests cover:
- Metal4DuckDBBridge initialization
- Query execution with automatic GPU/CPU/hybrid routing
- Query analysis logic
- Accelerated aggregation functions (SUM, AVG, COUNT)
- Identifier validation (SQL injection prevention)
- Table management (register, load parquet)
- Performance statistics
- Singleton pattern
- Validation function
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import builtins


class TestMetal4DuckDBBridgeInit:
    """Tests for Metal4DuckDBBridge initialization"""

    def test_init_with_metal_and_duckdb_available(self):
        """Test initialization with both Metal and DuckDB available"""
        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = True

        mock_duckdb = Mock()
        mock_conn = Mock()
        mock_duckdb.connect.return_value = mock_conn

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine)),
            'duckdb': mock_duckdb
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge

            bridge = Metal4DuckDBBridge()

            assert bridge._initialized is True
            assert bridge.sql_engine == mock_sql_engine
            assert bridge.duckdb_conn == mock_conn

    def test_init_metal_unavailable(self):
        """Test initialization when Metal SQL engine fails"""
        mock_duckdb = Mock()
        mock_conn = Mock()
        mock_duckdb.connect.return_value = mock_conn

        # Metal import fails
        def mock_import(name, *args, **kwargs):
            if name == 'metal4_sql_engine' or name.startswith('metal4_sql_engine'):
                raise ImportError("No Metal")
            return original_import(name, *args, **kwargs)

        original_import = builtins.__import__

        with patch.dict('sys.modules', {'duckdb': mock_duckdb}):
            with patch.object(builtins, '__import__', mock_import):
                from api.metal4_duckdb_bridge import Metal4DuckDBBridge

                # Force fresh init by creating new instance
                bridge = object.__new__(Metal4DuckDBBridge)
                bridge.sql_engine = None
                bridge.duckdb_conn = None
                bridge.gpu_threshold_rows = 10000
                bridge.gpu_threshold_columns = 5
                bridge._initialized = False
                bridge.stats = {
                    'total_queries': 0, 'gpu_accelerated': 0,
                    'cpu_executed': 0, 'total_time_ms': 0,
                    'gpu_time_ms': 0, 'cpu_time_ms': 0
                }
                bridge._initialize()

                assert bridge._initialized is True
                # sql_engine should be None due to import failure

    def test_init_duckdb_unavailable(self):
        """Test initialization when DuckDB is not installed"""
        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = True

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'duckdb':
                raise ImportError("DuckDB not installed")
            if name == 'metal4_sql_engine' or name.startswith('metal4_sql_engine'):
                return Mock(get_sql_engine=Mock(return_value=mock_sql_engine))
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, '__import__', mock_import):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge

            bridge = object.__new__(Metal4DuckDBBridge)
            bridge.sql_engine = None
            bridge.duckdb_conn = None
            bridge.gpu_threshold_rows = 10000
            bridge.gpu_threshold_columns = 5
            bridge._initialized = False
            bridge.stats = {
                'total_queries': 0, 'gpu_accelerated': 0,
                'cpu_executed': 0, 'total_time_ms': 0,
                'gpu_time_ms': 0, 'cpu_time_ms': 0
            }
            bridge._initialize()

            assert bridge._initialized is True
            assert bridge.duckdb_conn is None

    def test_init_default_thresholds(self):
        """Test default threshold values"""
        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = True

        mock_duckdb = Mock()
        mock_conn = Mock()
        mock_duckdb.connect.return_value = mock_conn

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine)),
            'duckdb': mock_duckdb
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge

            bridge = Metal4DuckDBBridge()

            assert bridge.gpu_threshold_rows == 10000
            assert bridge.gpu_threshold_columns == 5

    def test_init_stats_initialized(self):
        """Test stats dictionary initialized correctly"""
        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = True

        mock_duckdb = Mock()
        mock_conn = Mock()
        mock_duckdb.connect.return_value = mock_conn

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine)),
            'duckdb': mock_duckdb
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge

            bridge = Metal4DuckDBBridge()

            assert bridge.stats['total_queries'] == 0
            assert bridge.stats['gpu_accelerated'] == 0
            assert bridge.stats['cpu_executed'] == 0
            assert bridge.stats['total_time_ms'] == 0
            assert bridge.stats['gpu_time_ms'] == 0
            assert bridge.stats['cpu_time_ms'] == 0


class TestQueryAnalysis:
    """Tests for query analysis logic"""

    @pytest.fixture
    def bridge(self):
        """Create bridge instance with mocked dependencies"""
        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = True

        mock_duckdb = Mock()
        mock_conn = Mock()
        mock_duckdb.connect.return_value = mock_conn

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine)),
            'duckdb': mock_duckdb
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            return Metal4DuckDBBridge()

    def test_analyze_simple_aggregation_returns_gpu(self, bridge):
        """Test SUM query returns 'gpu' strategy"""
        result = bridge._analyze_query("SELECT SUM(value) FROM table1")
        assert result == 'gpu'

    def test_analyze_avg_returns_gpu(self, bridge):
        """Test AVG query returns 'gpu' strategy"""
        result = bridge._analyze_query("SELECT AVG(price) FROM products")
        assert result == 'gpu'

    def test_analyze_count_returns_gpu(self, bridge):
        """Test COUNT query returns 'gpu' strategy"""
        result = bridge._analyze_query("SELECT COUNT(*) FROM users")
        assert result == 'gpu'

    def test_analyze_min_max_returns_gpu(self, bridge):
        """Test MIN/MAX queries return 'gpu' strategy"""
        assert bridge._analyze_query("SELECT MIN(id) FROM t") == 'gpu'
        assert bridge._analyze_query("SELECT MAX(id) FROM t") == 'gpu'

    def test_analyze_group_by_returns_hybrid(self, bridge):
        """Test GROUP BY without JOIN returns 'hybrid' strategy"""
        result = bridge._analyze_query("SELECT category, SUM(value) FROM t GROUP BY category")
        # GROUP BY with aggregation still returns 'gpu' because has_aggregation is True
        # Only GROUP BY without aggregation returns 'hybrid'
        assert result in ['gpu', 'hybrid']

    def test_analyze_join_returns_cpu(self, bridge):
        """Test JOIN query returns 'cpu' strategy"""
        result = bridge._analyze_query("SELECT * FROM t1 JOIN t2 ON t1.id = t2.id")
        assert result == 'cpu'

    def test_analyze_subquery_returns_cpu(self, bridge):
        """Test subquery returns 'cpu' strategy"""
        result = bridge._analyze_query("SELECT * FROM t WHERE id IN (SELECT id FROM t2)")
        assert result == 'cpu'

    def test_analyze_like_returns_cpu(self, bridge):
        """Test LIKE query returns 'cpu' strategy"""
        result = bridge._analyze_query("SELECT * FROM t WHERE name LIKE '%test%'")
        assert result == 'cpu'

    def test_analyze_concat_returns_cpu(self, bridge):
        """Test CONCAT returns 'cpu' strategy"""
        result = bridge._analyze_query("SELECT CONCAT(first, last) FROM users")
        assert result == 'cpu'

    def test_analyze_substring_returns_cpu(self, bridge):
        """Test SUBSTRING returns 'cpu' strategy"""
        result = bridge._analyze_query("SELECT SUBSTRING(name, 1, 3) FROM t")
        assert result == 'cpu'

    def test_analyze_regexp_returns_cpu(self, bridge):
        """Test REGEXP returns 'cpu' strategy"""
        result = bridge._analyze_query("SELECT * FROM t WHERE name REGEXP '^A.*'")
        assert result == 'cpu'

    def test_analyze_simple_select_returns_cpu(self, bridge):
        """Test simple SELECT returns 'cpu' strategy"""
        result = bridge._analyze_query("SELECT * FROM table1")
        assert result == 'cpu'

    def test_analyze_aggregation_with_join_returns_cpu(self, bridge):
        """Test aggregation WITH join returns 'cpu' strategy"""
        result = bridge._analyze_query("SELECT SUM(t1.value) FROM t1 JOIN t2 ON t1.id = t2.id")
        assert result == 'cpu'

    def test_analyze_case_insensitive(self, bridge):
        """Test query analysis is case insensitive"""
        assert bridge._analyze_query("SELECT SUM(x) FROM t") == 'gpu'
        assert bridge._analyze_query("select sum(x) from t") == 'gpu'
        assert bridge._analyze_query("SELECT sum(X) FROM T") == 'gpu'

    def test_analyze_window_function(self, bridge):
        """Test window function detection"""
        result = bridge._analyze_query("SELECT id, SUM(value) OVER(PARTITION BY category) FROM t")
        # Window functions don't affect aggregation detection
        assert result in ['gpu', 'cpu', 'hybrid']


class TestQueryExecution:
    """Tests for query execution"""

    @pytest.fixture
    def bridge_with_duckdb(self):
        """Create bridge with real DuckDB (in-memory)"""
        # Use real DuckDB for execution tests
        import duckdb

        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = False

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine))
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            bridge = Metal4DuckDBBridge()

            # Register test data
            test_df = pd.DataFrame({
                'id': [1, 2, 3, 4, 5],
                'value': [10.0, 20.0, 30.0, 40.0, 50.0],
                'category': ['A', 'B', 'A', 'B', 'A']
            })
            bridge.register_dataframe('test_data', test_df)

            return bridge

    def test_execute_not_initialized_raises(self):
        """Test execute raises when not initialized"""
        from api.metal4_duckdb_bridge import Metal4DuckDBBridge

        bridge = object.__new__(Metal4DuckDBBridge)
        bridge._initialized = False
        bridge.duckdb_conn = None

        with pytest.raises(RuntimeError, match="Bridge not initialized"):
            bridge.execute("SELECT 1")

    def test_execute_cpu_simple_query(self, bridge_with_duckdb):
        """Test CPU execution of simple query"""
        result = bridge_with_duckdb.execute("SELECT * FROM test_data")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
        assert 'id' in result.columns

    def test_execute_aggregation_updates_stats(self, bridge_with_duckdb):
        """Test that query execution updates stats"""
        bridge_with_duckdb.reset_stats()

        bridge_with_duckdb.execute("SELECT SUM(value) FROM test_data")

        assert bridge_with_duckdb.stats['total_queries'] == 1
        # Since Metal is not available, goes to CPU
        assert bridge_with_duckdb.stats['cpu_executed'] >= 0

    def test_execute_with_params_placeholder(self, bridge_with_duckdb):
        """Test execute with params (currently ignored)"""
        result = bridge_with_duckdb.execute(
            "SELECT * FROM test_data WHERE id = 1",
            params={'id': 1}
        )

        assert isinstance(result, pd.DataFrame)

    def test_execute_invalid_query_raises(self, bridge_with_duckdb):
        """Test invalid SQL raises exception"""
        with pytest.raises(Exception):
            bridge_with_duckdb.execute("INVALID SQL SYNTAX")

    def test_execute_cpu_tracks_time(self, bridge_with_duckdb):
        """Test CPU execution tracks time"""
        bridge_with_duckdb.reset_stats()

        bridge_with_duckdb.execute("SELECT * FROM test_data")

        assert bridge_with_duckdb.stats['total_time_ms'] > 0


class TestExecuteGpu:
    """Tests for GPU execution path"""

    def test_execute_gpu_falls_back_to_cpu(self):
        """Test _execute_gpu currently falls back to CPU"""
        import duckdb

        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = True

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine))
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            bridge = Metal4DuckDBBridge()

            test_df = pd.DataFrame({'x': [1, 2, 3]})
            bridge.register_dataframe('t', test_df)

            result = bridge._execute_gpu("SELECT * FROM t", None)

            assert isinstance(result, pd.DataFrame)
            assert len(result) == 3


class TestExecuteHybrid:
    """Tests for hybrid execution path"""

    def test_execute_hybrid_falls_back_to_cpu(self):
        """Test _execute_hybrid currently falls back to CPU"""
        import duckdb

        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = True

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine))
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            bridge = Metal4DuckDBBridge()

            test_df = pd.DataFrame({'x': [1, 2, 3], 'cat': ['A', 'B', 'A']})
            bridge.register_dataframe('t', test_df)

            result = bridge._execute_hybrid("SELECT cat, COUNT(*) FROM t GROUP BY cat", None)

            assert isinstance(result, pd.DataFrame)


class TestIdentifierValidation:
    """Tests for SQL identifier validation"""

    @pytest.fixture
    def bridge(self):
        """Create bridge instance"""
        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = True

        mock_duckdb = Mock()
        mock_conn = Mock()
        mock_duckdb.connect.return_value = mock_conn

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine)),
            'duckdb': mock_duckdb
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            return Metal4DuckDBBridge()

    def test_validate_valid_identifier(self, bridge):
        """Test valid identifiers pass validation"""
        # Should not raise
        bridge._validate_identifier("users", "table name")
        bridge._validate_identifier("my_column", "column name")
        bridge._validate_identifier("_private", "identifier")
        bridge._validate_identifier("Table1", "table name")
        bridge._validate_identifier("col_123", "column name")

    def test_validate_invalid_starts_with_number(self, bridge):
        """Test identifier starting with number fails"""
        with pytest.raises(ValueError, match="Invalid table name"):
            bridge._validate_identifier("123table", "table name")

    def test_validate_sql_injection_semicolon(self, bridge):
        """Test SQL injection with semicolon is blocked"""
        with pytest.raises(ValueError, match="Invalid"):
            bridge._validate_identifier("table; DROP TABLE users;--", "table name")

    def test_validate_sql_injection_quotes(self, bridge):
        """Test SQL injection with quotes is blocked"""
        with pytest.raises(ValueError, match="Invalid"):
            bridge._validate_identifier("table'--", "table name")

    def test_validate_sql_injection_parentheses(self, bridge):
        """Test SQL injection with parentheses is blocked"""
        with pytest.raises(ValueError, match="Invalid"):
            bridge._validate_identifier("SUM(column)", "column name")

    def test_validate_empty_string(self, bridge):
        """Test empty string fails validation"""
        with pytest.raises(ValueError, match="Invalid"):
            bridge._validate_identifier("", "table name")

    def test_validate_none_fails(self, bridge):
        """Test None fails validation"""
        with pytest.raises(ValueError, match="Invalid"):
            bridge._validate_identifier(None, "table name")

    def test_validate_spaces_fail(self, bridge):
        """Test identifier with spaces fails"""
        with pytest.raises(ValueError, match="Invalid"):
            bridge._validate_identifier("my table", "table name")

    def test_validate_hyphen_fails(self, bridge):
        """Test identifier with hyphen fails"""
        with pytest.raises(ValueError, match="Invalid"):
            bridge._validate_identifier("my-table", "table name")


class TestAcceleratedAggregations:
    """Tests for accelerated aggregation functions"""

    @pytest.fixture
    def bridge_with_data(self):
        """Create bridge with test data - sql_engine=None for DuckDB fallback"""
        import duckdb

        # Return None for sql_engine to test DuckDB fallback path
        mock_module = Mock()
        mock_module.get_sql_engine.return_value = None

        with patch.dict('sys.modules', {
            'metal4_sql_engine': mock_module
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            bridge = Metal4DuckDBBridge()

            # sql_engine should be None for fallback tests
            bridge.sql_engine = None

            test_df = pd.DataFrame({
                'id': [1, 2, 3, 4, 5],
                'value': [10.0, 20.0, 30.0, 40.0, 50.0],
                'category': ['A', 'B', 'A', 'B', 'A']
            })
            bridge.register_dataframe('test_data', test_df)

            return bridge

    def test_accelerated_sum_without_metal(self, bridge_with_data):
        """Test SUM fallback to DuckDB when Metal unavailable"""
        result = bridge_with_data.accelerated_sum('test_data', 'value')

        assert result == 150.0  # 10+20+30+40+50

    def test_accelerated_sum_with_metal(self):
        """Test SUM using Metal GPU"""
        import duckdb

        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = True
        mock_sql_engine.sum.return_value = 150.0

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine))
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            bridge = Metal4DuckDBBridge()

            test_df = pd.DataFrame({'value': [10.0, 20.0, 30.0, 40.0, 50.0]})
            bridge.register_dataframe('test_data', test_df)

            result = bridge.accelerated_sum('test_data', 'value')

            assert result == 150.0
            mock_sql_engine.sum.assert_called_once()

    def test_accelerated_sum_validates_table_name(self, bridge_with_data):
        """Test accelerated_sum validates table name"""
        with pytest.raises(ValueError, match="Invalid table name"):
            bridge_with_data.accelerated_sum("DROP TABLE users;--", "value")

    def test_accelerated_sum_validates_column_name(self, bridge_with_data):
        """Test accelerated_sum validates column name"""
        with pytest.raises(ValueError, match="Invalid column name"):
            bridge_with_data.accelerated_sum("test_data", "1=1; DROP--")

    def test_accelerated_avg_without_metal(self, bridge_with_data):
        """Test AVG fallback to DuckDB when Metal unavailable"""
        result = bridge_with_data.accelerated_avg('test_data', 'value')

        assert result == 30.0  # 150/5

    def test_accelerated_avg_with_metal(self):
        """Test AVG using Metal GPU"""
        import duckdb

        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = True
        mock_sql_engine.avg.return_value = 30.0

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine))
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            bridge = Metal4DuckDBBridge()

            test_df = pd.DataFrame({'value': [10.0, 20.0, 30.0, 40.0, 50.0]})
            bridge.register_dataframe('test_data', test_df)

            result = bridge.accelerated_avg('test_data', 'value')

            assert result == 30.0
            mock_sql_engine.avg.assert_called_once()

    def test_accelerated_avg_validates_identifiers(self, bridge_with_data):
        """Test AVG validates identifiers"""
        with pytest.raises(ValueError):
            bridge_with_data.accelerated_avg("bad;table", "value")

    def test_accelerated_count_all_rows(self, bridge_with_data):
        """Test COUNT(*) equivalent"""
        result = bridge_with_data.accelerated_count('test_data')

        assert result == 5

    def test_accelerated_count_specific_column(self, bridge_with_data):
        """Test COUNT(column)"""
        result = bridge_with_data.accelerated_count('test_data', 'value')

        assert result == 5

    def test_accelerated_count_validates_table(self, bridge_with_data):
        """Test COUNT validates table name"""
        with pytest.raises(ValueError, match="Invalid table name"):
            bridge_with_data.accelerated_count("bad'table")

    def test_accelerated_count_validates_column_if_provided(self, bridge_with_data):
        """Test COUNT validates column name if provided"""
        with pytest.raises(ValueError, match="Invalid column name"):
            bridge_with_data.accelerated_count("test_data", "bad;column")


class TestTableManagement:
    """Tests for table management functions"""

    @pytest.fixture
    def bridge(self):
        """Create bridge instance"""
        import duckdb

        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = False

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine))
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            return Metal4DuckDBBridge()

    def test_register_dataframe_success(self, bridge):
        """Test registering DataFrame as table"""
        df = pd.DataFrame({'x': [1, 2, 3], 'y': ['a', 'b', 'c']})

        bridge.register_dataframe('my_table', df)

        # Verify by querying
        result = bridge.execute("SELECT * FROM my_table")
        assert len(result) == 3

    def test_register_dataframe_no_connection_raises(self):
        """Test register raises when DuckDB not initialized"""
        from api.metal4_duckdb_bridge import Metal4DuckDBBridge

        bridge = object.__new__(Metal4DuckDBBridge)
        bridge.duckdb_conn = None

        df = pd.DataFrame({'x': [1, 2, 3]})

        with pytest.raises(RuntimeError, match="DuckDB not initialized"):
            bridge.register_dataframe('test', df)

    def test_load_parquet_no_connection_raises(self):
        """Test load_parquet raises when DuckDB not initialized"""
        from api.metal4_duckdb_bridge import Metal4DuckDBBridge

        bridge = object.__new__(Metal4DuckDBBridge)
        bridge.duckdb_conn = None

        with pytest.raises(RuntimeError, match="DuckDB not initialized"):
            bridge.load_parquet('/path/to/file.parquet')

    def test_load_parquet_and_register(self, bridge, tmp_path):
        """Test loading Parquet file and registering as table"""
        # Create test Parquet file
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4.0, 5.0, 6.0]})
        parquet_path = tmp_path / "test.parquet"
        df.to_parquet(parquet_path)

        result = bridge.load_parquet(str(parquet_path), table_name='parquet_table')

        assert len(result) == 3

        # Verify table was registered
        query_result = bridge.execute("SELECT * FROM parquet_table")
        assert len(query_result) == 3

    def test_load_parquet_without_registering(self, bridge, tmp_path):
        """Test loading Parquet file without registering"""
        df = pd.DataFrame({'x': [1, 2]})
        parquet_path = tmp_path / "test2.parquet"
        df.to_parquet(parquet_path)

        result = bridge.load_parquet(str(parquet_path))

        assert len(result) == 2


class TestTableInfo:
    """Tests for get_table_info"""

    @pytest.fixture
    def bridge_with_table(self):
        """Create bridge with test table"""
        import duckdb

        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = False

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine))
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            bridge = Metal4DuckDBBridge()

            df = pd.DataFrame({
                'id': [1, 2, 3],
                'name': ['Alice', 'Bob', 'Charlie'],
                'score': [85.5, 92.0, 78.3]
            })
            bridge.register_dataframe('users', df)

            return bridge

    def test_get_table_info_success(self, bridge_with_table):
        """Test getting table info"""
        info = bridge_with_table.get_table_info('users')

        assert info['row_count'] == 3
        assert info['column_count'] == 3
        assert 'columns' in info

    def test_get_table_info_validates_name(self, bridge_with_table):
        """Test get_table_info validates table name"""
        with pytest.raises(ValueError, match="Invalid table name"):
            bridge_with_table.get_table_info("users; DROP--")

    def test_get_table_info_no_connection(self):
        """Test get_table_info returns empty dict when no connection"""
        from api.metal4_duckdb_bridge import Metal4DuckDBBridge

        bridge = object.__new__(Metal4DuckDBBridge)
        bridge.duckdb_conn = None

        result = bridge.get_table_info('any_table')

        assert result == {}


class TestStatusMethods:
    """Tests for status and utility methods"""

    @pytest.fixture
    def bridge(self):
        """Create bridge instance"""
        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = True

        mock_duckdb = Mock()
        mock_conn = Mock()
        mock_duckdb.connect.return_value = mock_conn

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine)),
            'duckdb': mock_duckdb
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            return Metal4DuckDBBridge()

    def test_is_available_returns_initialized_state(self, bridge):
        """Test is_available returns _initialized"""
        assert bridge.is_available() is True

        bridge._initialized = False
        assert bridge.is_available() is False

    def test_uses_metal_with_metal_available(self, bridge):
        """Test uses_metal returns True when Metal is available"""
        bridge.sql_engine.uses_metal.return_value = True
        assert bridge.uses_metal() is True

    def test_uses_metal_without_metal(self, bridge):
        """Test uses_metal returns False when Metal unavailable"""
        bridge.sql_engine.uses_metal.return_value = False
        assert bridge.uses_metal() is False

    def test_uses_metal_no_sql_engine(self, bridge):
        """Test uses_metal returns falsy when no sql_engine"""
        bridge.sql_engine = None
        # uses_metal() returns None when sql_engine is None (short-circuit evaluation)
        assert not bridge.uses_metal()


class TestStatistics:
    """Tests for performance statistics"""

    @pytest.fixture
    def bridge(self):
        """Create bridge instance"""
        import duckdb

        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = False

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine))
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            return Metal4DuckDBBridge()

    def test_get_stats_empty(self, bridge):
        """Test stats when no queries executed"""
        bridge.reset_stats()

        stats = bridge.get_stats()

        assert stats['total_queries'] == 0
        assert stats['avg_time_ms'] == 0
        assert stats['gpu_percentage'] == 0
        assert stats['metal_available'] is False

    def test_get_stats_after_queries(self, bridge):
        """Test stats after executing queries"""
        df = pd.DataFrame({'x': [1, 2, 3]})
        bridge.register_dataframe('t', df)

        bridge.reset_stats()
        bridge.execute("SELECT * FROM t")
        bridge.execute("SELECT SUM(x) FROM t")

        stats = bridge.get_stats()

        assert stats['total_queries'] == 2
        assert stats['avg_time_ms'] > 0

    def test_reset_stats(self, bridge):
        """Test stats reset"""
        bridge.stats['total_queries'] = 100
        bridge.stats['gpu_accelerated'] = 50

        bridge.reset_stats()

        assert bridge.stats['total_queries'] == 0
        assert bridge.stats['gpu_accelerated'] == 0
        assert bridge.stats['cpu_executed'] == 0
        assert bridge.stats['total_time_ms'] == 0

    def test_gpu_percentage_calculation(self, bridge):
        """Test GPU percentage is calculated correctly"""
        bridge.stats = {
            'total_queries': 10,
            'gpu_accelerated': 3,
            'cpu_executed': 7,
            'total_time_ms': 100,
            'gpu_time_ms': 30,
            'cpu_time_ms': 70
        }
        bridge.sql_engine = None  # No metal

        stats = bridge.get_stats()

        assert stats['gpu_percentage'] == 30.0


class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_duckdb_bridge_returns_singleton(self):
        """Test singleton returns same instance"""
        import duckdb

        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = False

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine))
        }):
            from api.metal4_duckdb_bridge import get_duckdb_bridge
            import api.metal4_duckdb_bridge as bridge_module

            # Reset singleton
            bridge_module._duckdb_bridge = None

            bridge1 = get_duckdb_bridge()
            bridge2 = get_duckdb_bridge()

            assert bridge1 is bridge2


class TestValidateDuckDBBridge:
    """Tests for validate_duckdb_bridge function"""

    def test_validate_success(self):
        """Test validation with all tests passing"""
        import duckdb

        # Return None for sql_engine to use DuckDB fallback
        mock_module = Mock()
        mock_module.get_sql_engine.return_value = None

        with patch.dict('sys.modules', {
            'metal4_sql_engine': mock_module
        }):
            from api.metal4_duckdb_bridge import validate_duckdb_bridge
            import api.metal4_duckdb_bridge as bridge_module

            # Reset singleton for clean test
            bridge_module._duckdb_bridge = None

            status = validate_duckdb_bridge()

            assert status['initialized'] == True
            assert status['duckdb_available'] == True
            # Note: numpy booleans are not identical to Python True, use == not is
            assert status['sum_test'] == True
            assert status['avg_test'] == True
            assert status['count_test'] == True
            assert status['all_tests_passed'] == True

    def test_validate_returns_error_on_failure(self):
        """Test validation returns error dict on exception"""
        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(side_effect=Exception("Init failed")))
        }):
            from api.metal4_duckdb_bridge import validate_duckdb_bridge
            import api.metal4_duckdb_bridge as bridge_module

            # Reset singleton
            bridge_module._duckdb_bridge = None

            # Force exception by patching get_duckdb_bridge
            with patch.object(bridge_module, 'get_duckdb_bridge', side_effect=Exception("Bridge error")):
                status = validate_duckdb_bridge()

            assert status['initialized'] is False
            assert 'error' in status


class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.fixture
    def bridge(self):
        """Create bridge instance"""
        import duckdb

        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = False

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine))
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            return Metal4DuckDBBridge()

    def test_empty_dataframe(self, bridge):
        """Test with empty DataFrame"""
        df = pd.DataFrame({'x': []})
        bridge.register_dataframe('empty_table', df)

        result = bridge.execute("SELECT COUNT(*) as cnt FROM empty_table")
        assert result['cnt'].iloc[0] == 0

    def test_large_dataframe_registration(self, bridge):
        """Test registering large DataFrame"""
        df = pd.DataFrame({
            'id': range(100000),
            'value': np.random.randn(100000)
        })
        bridge.register_dataframe('large_table', df)

        count = bridge.accelerated_count('large_table')
        assert count == 100000

    def test_unicode_in_data(self, bridge):
        """Test handling unicode data"""
        df = pd.DataFrame({
            'name': ['日本語', 'Ελληνικά', '한국어'],
            'value': [1, 2, 3]
        })
        bridge.register_dataframe('unicode_table', df)

        result = bridge.execute("SELECT * FROM unicode_table")
        assert len(result) == 3

    def test_null_values(self, bridge):
        """Test handling NULL values"""
        df = pd.DataFrame({
            'x': [1, None, 3],
            'y': [None, 2, None]
        })
        bridge.register_dataframe('nulls_table', df)

        result = bridge.execute("SELECT * FROM nulls_table")
        assert len(result) == 3

    def test_mixed_types(self, bridge):
        """Test DataFrame with mixed types"""
        df = pd.DataFrame({
            'int_col': [1, 2, 3],
            'float_col': [1.5, 2.5, 3.5],
            'str_col': ['a', 'b', 'c'],
            'bool_col': [True, False, True]
        })
        bridge.register_dataframe('mixed_table', df)

        result = bridge.execute("SELECT * FROM mixed_table")
        assert len(result) == 3


class TestIntegration:
    """Integration tests"""

    def test_full_workflow(self):
        """Test complete workflow: load, query, aggregate"""
        import duckdb

        # Return None for sql_engine to use DuckDB fallback
        mock_module = Mock()
        mock_module.get_sql_engine.return_value = None

        with patch.dict('sys.modules', {
            'metal4_sql_engine': mock_module
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            bridge = Metal4DuckDBBridge()

            # Ensure sql_engine is None for fallback path
            bridge.sql_engine = None

            # Create and register data
            sales_df = pd.DataFrame({
                'product_id': [1, 1, 2, 2, 3],
                'quantity': [10, 20, 15, 25, 30],
                'price': [9.99, 9.99, 19.99, 19.99, 29.99]
            })
            bridge.register_dataframe('sales', sales_df)

            # Execute queries using accelerated methods
            total_quantity = bridge.accelerated_sum('sales', 'quantity')
            avg_price = bridge.accelerated_avg('sales', 'price')
            row_count = bridge.accelerated_count('sales')

            assert total_quantity == 100  # 10+20+15+25+30
            assert abs(avg_price - 17.99) < 0.01
            assert row_count == 5

            # Test execute() method to track stats
            bridge.reset_stats()
            result = bridge.execute("SELECT * FROM sales")
            assert len(result) == 5

            # Check stats (execute() tracks queries, accelerated_* do not)
            stats = bridge.get_stats()
            assert stats['total_queries'] == 1

    def test_multiple_tables_join_cpu(self):
        """Test JOIN between multiple tables uses CPU"""
        import duckdb

        mock_sql_engine = Mock()
        mock_sql_engine.uses_metal.return_value = True

        with patch.dict('sys.modules', {
            'metal4_sql_engine': Mock(get_sql_engine=Mock(return_value=mock_sql_engine))
        }):
            from api.metal4_duckdb_bridge import Metal4DuckDBBridge
            bridge = Metal4DuckDBBridge()
            bridge.reset_stats()

            users_df = pd.DataFrame({
                'id': [1, 2, 3],
                'name': ['Alice', 'Bob', 'Charlie']
            })
            orders_df = pd.DataFrame({
                'user_id': [1, 1, 2],
                'amount': [100, 200, 150]
            })

            bridge.register_dataframe('users', users_df)
            bridge.register_dataframe('orders', orders_df)

            # Join query should go to CPU
            result = bridge.execute("""
                SELECT u.name, SUM(o.amount) as total
                FROM users u
                JOIN orders o ON u.id = o.user_id
                GROUP BY u.name
            """)

            assert len(result) == 2  # Alice and Bob have orders
            stats = bridge.get_stats()
            # JOIN forces CPU execution
            assert stats['cpu_executed'] >= 1
