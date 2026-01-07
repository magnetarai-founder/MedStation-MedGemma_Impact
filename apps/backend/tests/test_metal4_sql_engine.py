"""
Comprehensive tests for api/metal4_sql_engine.py

Tests the Metal 4 SQL Acceleration Engine including:
- Metal4SQLEngine initialization
- Aggregation operations (SUM, AVG, COUNT, MIN, MAX)
- WHERE clause filtering
- Column map operations
- Statistics tracking
- Singleton pattern and validation
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch


class TestMetal4SQLEngineInit:
    """Tests for Metal4SQLEngine initialization"""

    def test_init_without_metal(self):
        """Initialize without Metal available"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()

        assert engine._initialized is True
        assert engine._use_metal is False
        assert engine.gpu_threshold_rows == 10000

    def test_init_creates_empty_stats(self):
        """Initialize creates empty stats"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()

        assert engine.stats['queries_executed'] == 0
        assert engine.stats['total_time_ms'] == 0
        assert engine.stats['gpu_time_ms'] == 0
        assert engine.stats['cpu_fallback_count'] == 0
        assert engine.stats['rows_processed'] == 0

    def test_init_creates_empty_pipelines(self):
        """Initialize creates empty pipelines dict"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()

        assert engine.pipelines == {}

    def test_init_sets_gpu_threshold(self):
        """Initialize sets default GPU threshold"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()

        assert engine.gpu_threshold_rows == 10000


class TestMetalCheck:
    """Tests for _check_metal"""

    def test_check_metal_unavailable(self):
        """Metal check returns False when unavailable"""
        from api.metal4_sql_engine import Metal4SQLEngine

        mock_engine = Mock()
        mock_engine.is_available.return_value = False

        with patch.dict('sys.modules', {
            'metal4_engine': Mock(get_metal4_engine=Mock(return_value=mock_engine))
        }):
            engine = Metal4SQLEngine.__new__(Metal4SQLEngine)
            result = engine._check_metal()

        assert result is False

    def test_check_metal_import_error(self):
        """Metal check handles import error"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.dict('sys.modules', {'metal4_engine': None}):
            engine = Metal4SQLEngine.__new__(Metal4SQLEngine)

            with patch('api.metal4_sql_engine.logger'):
                result = engine._check_metal()

        assert result is False


class TestSumOperation:
    """Tests for sum operation"""

    @pytest.fixture
    def engine(self):
        """Create engine with CPU fallback"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()
        return engine

    def test_sum_float32(self, engine):
        """Sum of float32 array"""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)

        result = engine.sum(data)

        assert result == pytest.approx(15.0)

    def test_sum_float64(self, engine):
        """Sum of float64 array"""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)

        result = engine.sum(data)

        assert result == pytest.approx(15.0)

    def test_sum_int32(self, engine):
        """Sum of int32 array"""
        data = np.array([1, 2, 3, 4, 5], dtype=np.int32)

        result = engine.sum(data)

        assert result == pytest.approx(15.0)

    def test_sum_int64(self, engine):
        """Sum of int64 array"""
        data = np.array([1, 2, 3, 4, 5], dtype=np.int64)

        result = engine.sum(data)

        assert result == pytest.approx(15.0)

    def test_sum_empty_array(self, engine):
        """Sum of empty array"""
        data = np.array([], dtype=np.float32)

        result = engine.sum(data)

        assert result == 0.0

    def test_sum_negative_values(self, engine):
        """Sum with negative values"""
        data = np.array([-1.0, 2.0, -3.0, 4.0, -5.0], dtype=np.float32)

        result = engine.sum(data)

        assert result == pytest.approx(-3.0)

    def test_sum_large_array(self, engine):
        """Sum of large array"""
        data = np.ones(100000, dtype=np.float32)

        result = engine.sum(data)

        assert result == pytest.approx(100000.0)

    def test_sum_returns_float(self, engine):
        """Sum always returns float"""
        data = np.array([1, 2, 3], dtype=np.int32)

        result = engine.sum(data)

        assert isinstance(result, float)


class TestCountOperation:
    """Tests for count operation"""

    @pytest.fixture
    def engine(self):
        """Create engine with CPU fallback"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()
        return engine

    def test_count_without_null_mask(self, engine):
        """Count without null mask returns length"""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)

        result = engine.count(data)

        assert result == 5

    def test_count_with_null_mask(self, engine):
        """Count with null mask counts valid values"""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        null_mask = np.array([1, 1, 0, 1, 0], dtype=np.uint8)

        result = engine.count(data, null_mask)

        assert result == 3

    def test_count_all_null(self, engine):
        """Count with all nulls returns 0"""
        data = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        null_mask = np.array([0, 0, 0], dtype=np.uint8)

        result = engine.count(data, null_mask)

        assert result == 0

    def test_count_empty_array(self, engine):
        """Count of empty array returns 0"""
        data = np.array([], dtype=np.float32)

        result = engine.count(data)

        assert result == 0


class TestAvgOperation:
    """Tests for avg operation"""

    @pytest.fixture
    def engine(self):
        """Create engine with CPU fallback"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()
        return engine

    def test_avg_simple(self, engine):
        """Average of simple array"""
        data = np.array([2.0, 4.0, 6.0, 8.0, 10.0], dtype=np.float32)

        result = engine.avg(data)

        assert result == pytest.approx(6.0)

    def test_avg_with_null_mask(self, engine):
        """Average with null mask"""
        data = np.array([2.0, 4.0, 6.0, 8.0, 10.0], dtype=np.float32)
        null_mask = np.array([1, 1, 0, 1, 0], dtype=np.uint8)  # 2, 4, 8 are valid

        result = engine.avg(data, null_mask)

        # Average of 2, 4, 8 (masking nulls)
        expected = (2.0 + 4.0 + 8.0) / 3
        assert result == pytest.approx(expected, rel=0.1)

    def test_avg_all_null_returns_zero(self, engine):
        """Average with all nulls returns 0"""
        data = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        null_mask = np.array([0, 0, 0], dtype=np.uint8)

        result = engine.avg(data, null_mask)

        assert result == 0.0

    def test_avg_single_value(self, engine):
        """Average of single value"""
        data = np.array([42.0], dtype=np.float32)

        result = engine.avg(data)

        assert result == pytest.approx(42.0)


class TestMinMaxOperations:
    """Tests for min and max operations"""

    @pytest.fixture
    def engine(self):
        """Create engine with CPU fallback"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()
        return engine

    def test_min_simple(self, engine):
        """Find minimum value"""
        data = np.array([5.0, 2.0, 8.0, 1.0, 9.0], dtype=np.float32)

        result = engine.min(data)

        assert result == pytest.approx(1.0)

    def test_max_simple(self, engine):
        """Find maximum value"""
        data = np.array([5.0, 2.0, 8.0, 1.0, 9.0], dtype=np.float32)

        result = engine.max(data)

        assert result == pytest.approx(9.0)

    def test_min_negative_values(self, engine):
        """Min with negative values"""
        data = np.array([5.0, -2.0, 8.0, -10.0, 9.0], dtype=np.float32)

        result = engine.min(data)

        assert result == pytest.approx(-10.0)

    def test_max_negative_values(self, engine):
        """Max with negative values"""
        data = np.array([-5.0, -2.0, -8.0, -1.0, -9.0], dtype=np.float32)

        result = engine.max(data)

        assert result == pytest.approx(-1.0)

    def test_min_single_value(self, engine):
        """Min of single value"""
        data = np.array([42.0], dtype=np.float32)

        result = engine.min(data)

        assert result == pytest.approx(42.0)

    def test_max_single_value(self, engine):
        """Max of single value"""
        data = np.array([42.0], dtype=np.float32)

        result = engine.max(data)

        assert result == pytest.approx(42.0)


class TestWhereOperation:
    """Tests for WHERE clause filtering"""

    @pytest.fixture
    def engine(self):
        """Create engine with CPU fallback"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()
        return engine

    @pytest.fixture
    def test_data(self):
        """Test data for filtering"""
        return np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)

    def test_where_equals(self, engine, test_data):
        """WHERE with equality"""
        result = engine.where(test_data, '==', 3.0)

        expected = np.array([False, False, True, False, False])
        np.testing.assert_array_equal(result, expected)

    def test_where_less_than(self, engine, test_data):
        """WHERE with less than"""
        result = engine.where(test_data, '<', 3.0)

        expected = np.array([True, True, False, False, False])
        np.testing.assert_array_equal(result, expected)

    def test_where_greater_than(self, engine, test_data):
        """WHERE with greater than"""
        result = engine.where(test_data, '>', 3.0)

        expected = np.array([False, False, False, True, True])
        np.testing.assert_array_equal(result, expected)

    def test_where_less_equal(self, engine, test_data):
        """WHERE with less than or equal"""
        result = engine.where(test_data, '<=', 3.0)

        expected = np.array([True, True, True, False, False])
        np.testing.assert_array_equal(result, expected)

    def test_where_greater_equal(self, engine, test_data):
        """WHERE with greater than or equal"""
        result = engine.where(test_data, '>=', 3.0)

        expected = np.array([False, False, True, True, True])
        np.testing.assert_array_equal(result, expected)

    def test_where_not_equals(self, engine, test_data):
        """WHERE with not equals"""
        result = engine.where(test_data, '!=', 3.0)

        expected = np.array([True, True, False, True, True])
        np.testing.assert_array_equal(result, expected)

    def test_where_unknown_operator_raises(self, engine, test_data):
        """WHERE with unknown operator raises error"""
        with pytest.raises(ValueError, match="Unknown operator"):
            engine.where(test_data, 'LIKE', 3.0)

    def test_where_returns_boolean_mask(self, engine, test_data):
        """WHERE returns boolean array"""
        result = engine.where(test_data, '>', 0)

        assert result.dtype == bool


class TestColumnMapOperation:
    """Tests for column_map operation"""

    @pytest.fixture
    def engine(self):
        """Create engine with CPU fallback"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()
        return engine

    @pytest.fixture
    def test_data(self):
        """Test data for column operations"""
        return np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)

    def test_column_map_add(self, engine, test_data):
        """Column map add operation"""
        result = engine.column_map(test_data, 'add', 10.0)

        expected = np.array([11.0, 12.0, 13.0, 14.0, 15.0], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_column_map_mul(self, engine, test_data):
        """Column map multiply operation"""
        result = engine.column_map(test_data, 'mul', 2.0)

        expected = np.array([2.0, 4.0, 6.0, 8.0, 10.0], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_column_map_div(self, engine, test_data):
        """Column map divide operation"""
        result = engine.column_map(test_data, 'div', 2.0)

        expected = np.array([0.5, 1.0, 1.5, 2.0, 2.5], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_column_map_sub(self, engine, test_data):
        """Column map subtract operation"""
        result = engine.column_map(test_data, 'sub', 1.0)

        expected = np.array([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_column_map_sqrt(self, engine):
        """Column map sqrt operation"""
        data = np.array([1.0, 4.0, 9.0, 16.0, 25.0], dtype=np.float32)

        result = engine.column_map(data, 'sqrt')

        expected = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_column_map_abs(self, engine):
        """Column map abs operation"""
        data = np.array([-1.0, 2.0, -3.0, 4.0, -5.0], dtype=np.float32)

        result = engine.column_map(data, 'abs')

        expected = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_column_map_unknown_operation_raises(self, engine, test_data):
        """Column map with unknown operation raises error"""
        with pytest.raises(ValueError, match="Unknown operation"):
            engine.column_map(test_data, 'log')


class TestShouldUseGPU:
    """Tests for _should_use_gpu decision logic"""

    @pytest.fixture
    def engine_with_metal(self):
        """Create engine with Metal enabled"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()
            engine._use_metal = True  # Force Metal enabled
        return engine

    @pytest.fixture
    def engine_without_metal(self):
        """Create engine without Metal"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()
        return engine

    def test_should_use_gpu_above_threshold(self, engine_with_metal):
        """Should use GPU when above threshold"""
        assert engine_with_metal._should_use_gpu(15000) is True

    def test_should_not_use_gpu_below_threshold(self, engine_with_metal):
        """Should not use GPU when below threshold"""
        assert engine_with_metal._should_use_gpu(5000) is False

    def test_should_not_use_gpu_without_metal(self, engine_without_metal):
        """Should not use GPU when Metal disabled"""
        assert engine_without_metal._should_use_gpu(15000) is False

    def test_should_use_gpu_at_threshold(self, engine_with_metal):
        """Should use GPU at exactly threshold"""
        assert engine_with_metal._should_use_gpu(10000) is True

    def test_threshold_is_configurable(self, engine_with_metal):
        """Threshold is configurable"""
        engine_with_metal.gpu_threshold_rows = 5000

        assert engine_with_metal._should_use_gpu(4999) is False
        assert engine_with_metal._should_use_gpu(5000) is True


class TestStatistics:
    """Tests for statistics tracking"""

    @pytest.fixture
    def engine(self):
        """Create engine"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()
        return engine

    def test_get_stats_includes_all_fields(self, engine):
        """get_stats returns all expected fields"""
        stats = engine.get_stats()

        assert 'queries_executed' in stats
        assert 'total_time_ms' in stats
        assert 'gpu_time_ms' in stats
        assert 'cpu_fallback_count' in stats
        assert 'rows_processed' in stats
        assert 'avg_time_ms' in stats
        assert 'metal_enabled' in stats
        assert 'gpu_threshold_rows' in stats

    def test_get_stats_avg_time_zero_when_no_queries(self, engine):
        """Average time is 0 when no queries executed"""
        stats = engine.get_stats()

        assert stats['avg_time_ms'] == 0

    def test_reset_stats(self, engine):
        """reset_stats clears all counters"""
        # Set some values
        engine.stats['queries_executed'] = 10
        engine.stats['total_time_ms'] = 1000

        engine.reset_stats()

        assert engine.stats['queries_executed'] == 0
        assert engine.stats['total_time_ms'] == 0


class TestUtilityMethods:
    """Tests for utility methods"""

    def test_is_available_after_init(self):
        """is_available returns True after initialization"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()

        assert engine.is_available() is True

    def test_uses_metal_false_without_metal(self):
        """uses_metal returns False without Metal"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()

        assert engine.uses_metal() is False


class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_sql_engine_returns_instance(self):
        """get_sql_engine returns instance"""
        import api.metal4_sql_engine as module
        module._sql_engine = None

        with patch.object(module.Metal4SQLEngine, '_check_metal', return_value=False):
            engine = module.get_sql_engine()

        assert engine is not None
        assert isinstance(engine, module.Metal4SQLEngine)

    def test_get_sql_engine_returns_same_instance(self):
        """get_sql_engine returns same instance"""
        import api.metal4_sql_engine as module
        module._sql_engine = None

        with patch.object(module.Metal4SQLEngine, '_check_metal', return_value=False):
            engine1 = module.get_sql_engine()
            engine2 = module.get_sql_engine()

        assert engine1 is engine2

    def test_get_metal4_sql_engine_alias(self):
        """get_metal4_sql_engine is alias for get_sql_engine"""
        import api.metal4_sql_engine as module

        assert module.get_metal4_sql_engine is module.get_sql_engine


class TestValidation:
    """Tests for validate_sql_engine"""

    def test_validate_returns_status_dict(self):
        """validate_sql_engine returns status dict"""
        import api.metal4_sql_engine as module
        module._sql_engine = None

        with patch.object(module.Metal4SQLEngine, '_check_metal', return_value=False):
            status = module.validate_sql_engine()

        assert isinstance(status, dict)
        assert 'initialized' in status
        assert 'metal_enabled' in status
        assert 'sum_test' in status
        assert 'avg_test' in status
        assert 'min_test' in status
        assert 'max_test' in status
        assert 'all_tests_passed' in status

    def test_validate_all_tests_pass(self):
        """Validation tests all pass with correct implementation"""
        import api.metal4_sql_engine as module
        module._sql_engine = None

        with patch.object(module.Metal4SQLEngine, '_check_metal', return_value=False):
            status = module.validate_sql_engine()

        assert status['all_tests_passed'] is True

    def test_validate_handles_exception(self):
        """Validation handles exception gracefully"""
        import api.metal4_sql_engine as module
        module._sql_engine = None

        with patch.object(module, 'get_sql_engine', side_effect=Exception("Init failed")):
            status = module.validate_sql_engine()

        assert status['initialized'] is False
        assert 'error' in status


class TestEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    def engine(self):
        """Create engine"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()
        return engine

    def test_sum_very_large_values(self, engine):
        """Sum handles very large values"""
        data = np.array([1e38, 1e38, 1e38], dtype=np.float32)

        result = engine.sum(data)

        assert result > 0  # Just verify no overflow crash

    def test_sum_very_small_values(self, engine):
        """Sum handles very small values"""
        data = np.array([1e-38, 1e-38, 1e-38], dtype=np.float32)

        result = engine.sum(data)

        assert result == pytest.approx(3e-38, rel=1)

    def test_operations_preserve_array_shape(self, engine):
        """Column operations preserve input shape"""
        data = np.array([1.0, 2.0, 3.0], dtype=np.float32)

        result = engine.column_map(data, 'mul', 2.0)

        assert result.shape == data.shape

    def test_where_with_nan(self, engine):
        """WHERE handles NaN values"""
        data = np.array([1.0, np.nan, 3.0], dtype=np.float32)

        result = engine.where(data, '>', 0)

        # NaN comparisons return False
        assert result[0] is np.True_
        assert result[1] is np.False_
        assert result[2] is np.True_

    def test_avg_cpu_with_bool_mask(self, engine):
        """_avg_cpu works with bool mask"""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        null_mask = np.array([True, True, False, True, False], dtype=bool)

        result = engine._avg_cpu(data, null_mask.astype(np.uint8))

        # Average of 1, 2, 4
        assert result == pytest.approx((1.0 + 2.0 + 4.0) / 3)


class TestIntegration:
    """Integration tests"""

    def test_full_query_workflow(self):
        """Test full query workflow"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()

        # Simulate a query: SELECT AVG(price) WHERE price > 10
        prices = np.array([5.0, 15.0, 25.0, 8.0, 30.0, 12.0], dtype=np.float32)

        # Filter
        mask = engine.where(prices, '>', 10.0)

        # Apply filter and calculate average
        filtered_prices = prices[mask]
        avg_price = engine.avg(filtered_prices)

        # Expected: (15 + 25 + 30 + 12) / 4 = 20.5
        assert avg_price == pytest.approx(20.5)

    def test_column_transform_and_aggregate(self):
        """Test column transform followed by aggregation"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()

        # Simulate: SELECT SUM(price * quantity)
        prices = np.array([10.0, 20.0, 30.0], dtype=np.float32)
        quantities = np.array([2.0, 3.0, 1.0], dtype=np.float32)

        # Multiply columns
        totals = prices * quantities  # Using numpy directly

        # Sum
        total = engine.sum(totals)

        # Expected: 10*2 + 20*3 + 30*1 = 20 + 60 + 30 = 110
        assert total == pytest.approx(110.0)

    def test_multiple_aggregations(self):
        """Test multiple aggregations on same data"""
        from api.metal4_sql_engine import Metal4SQLEngine

        with patch.object(Metal4SQLEngine, '_check_metal', return_value=False):
            engine = Metal4SQLEngine()

        data = np.array([10.0, 20.0, 30.0, 40.0, 50.0], dtype=np.float32)

        sum_result = engine.sum(data)
        avg_result = engine.avg(data)
        min_result = engine.min(data)
        max_result = engine.max(data)
        count_result = engine.count(data)

        assert sum_result == pytest.approx(150.0)
        assert avg_result == pytest.approx(30.0)
        assert min_result == pytest.approx(10.0)
        assert max_result == pytest.approx(50.0)
        assert count_result == 5
