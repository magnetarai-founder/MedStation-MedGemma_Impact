#!/usr/bin/env python3
"""
Neutron Core Performance Sanity Check

Simple performance baseline script to time key neutron_core operations.
Uses time.perf_counter() for accurate timing - no heavy benchmarking framework.

Usage:
    cd /path/to/ElohimOS
    export PYTHONPATH="packages:$PYTHONPATH"
    python3 tools/perf/neutron_core_perf.py

Expected baseline (reference machine):
- Small dataset (100 rows): < 50ms
- Medium dataset (10K rows): < 500ms
- Large dataset (100K rows): < 3000ms
"""

import sys
import time
import tempfile
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages"))

from neutron_core.engine import NeutronEngine


def generate_test_csv(num_rows: int) -> str:
    """Generate synthetic CSV data for testing"""
    csv_lines = ["id,name,value,category,price,quantity,status"]

    for i in range(num_rows):
        csv_lines.append(
            f"{i},"
            f"Product_{i},"
            f"{i * 1.5},"
            f"Category_{i % 10},"
            f"{10.0 + (i % 100)},"
            f"{i % 50 + 1},"
            f"{'active' if i % 2 == 0 else 'inactive'}"
        )

    return "\n".join(csv_lines)


def time_operation(operation_name: str, operation_func):
    """Time an operation and print results"""
    print(f"\n{'='*60}")
    print(f"  {operation_name}")
    print(f"{'='*60}")

    start = time.perf_counter()
    result = operation_func()
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"✓ Completed in {elapsed_ms:.2f}ms")
    return result, elapsed_ms


def run_query_benchmark(size: str, num_rows: int):
    """Benchmark query execution for given dataset size"""
    print(f"\n{'#'*60}")
    print(f"# {size.upper()} DATASET QUERY BENCHMARK ({num_rows:,} rows)")
    print(f"{'#'*60}")

    engine = NeutronEngine()

    # Generate test data
    csv_data = generate_test_csv(num_rows)

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_data)
        csv_path = f.name

    try:
        # Time: Load CSV
        def load_csv():
            return engine.load_csv(csv_path, table_name="test_data")

        load_result, load_time = time_operation("Load CSV", load_csv)

        if load_result.error:
            print(f"❌ Load failed: {load_result.error}")
            return None

        print(f"  - Rows loaded: {load_result.row_count:,}")
        print(f"  - Columns: {len(load_result.column_names)}")

        # Time: Simple SELECT
        def simple_select():
            return engine.execute_sql("SELECT * FROM test_data LIMIT 10")

        select_result, select_time = time_operation("Simple SELECT (LIMIT 10)", simple_select)

        if select_result.error:
            print(f"❌ SELECT failed: {select_result.error}")
        else:
            print(f"  - Rows returned: {select_result.row_count}")

        # Time: Aggregation Query
        def aggregate_query():
            return engine.execute_sql("""
                SELECT category,
                       COUNT(*) as count,
                       CAST(AVG(CAST(value AS DOUBLE)) AS DOUBLE) as avg_value,
                       CAST(SUM(CAST(price AS DOUBLE) * CAST(quantity AS DOUBLE)) AS DOUBLE) as total_revenue
                FROM test_data
                GROUP BY category
                ORDER BY count DESC
            """)

        agg_result, agg_time = time_operation("Aggregation Query (GROUP BY)", aggregate_query)

        if agg_result.error:
            print(f"❌ Aggregation failed: {agg_result.error}")
        else:
            print(f"  - Groups returned: {agg_result.row_count}")

        # Time: Filter Query
        def filter_query():
            return engine.execute_sql("""
                SELECT * FROM test_data
                WHERE status = 'active'
                  AND CAST(value AS DOUBLE) > 100
                ORDER BY CAST(value AS DOUBLE) DESC
                LIMIT 100
            """)

        filter_result, filter_time = time_operation("Filter Query (WHERE + ORDER)", filter_query)

        if filter_result.error:
            print(f"❌ Filter failed: {filter_result.error}")
        else:
            print(f"  - Rows returned: {filter_result.row_count}")

        # Time: Join Query (self-join for simulation)
        def join_query():
            return engine.execute_sql("""
                SELECT a.id, a.name, b.category
                FROM test_data a
                JOIN test_data b ON a.category = b.category
                WHERE a.id < 100
                LIMIT 100
            """)

        join_result, join_time = time_operation("Join Query (self-join)", join_query)

        if join_result.error:
            print(f"❌ Join failed: {join_result.error}")
        else:
            print(f"  - Rows returned: {join_result.row_count}")

        # Time: Export to CSV
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as export_f:
            export_path = export_f.name

        def export_csv():
            result = engine.execute_sql("SELECT * FROM test_data LIMIT 1000")
            return engine.export_results(result, export_path, format='csv')

        export_success, export_time = time_operation("Export to CSV (1000 rows)", export_csv)

        if export_success:
            export_size_kb = Path(export_path).stat().st_size / 1024
            print(f"  - Export size: {export_size_kb:.2f} KB")
        else:
            print(f"❌ Export failed")

        # Cleanup export file
        try:
            Path(export_path).unlink()
        except Exception:
            pass

        # Summary
        total_time = load_time + select_time + agg_time + filter_time + join_time + export_time
        print(f"\n{'─'*60}")
        print(f"TOTAL TIME: {total_time:.2f}ms")
        print(f"{'─'*60}")

        return {
            'size': size,
            'rows': num_rows,
            'load_ms': load_time,
            'select_ms': select_time,
            'aggregate_ms': agg_time,
            'filter_ms': filter_time,
            'join_ms': join_time,
            'export_ms': export_time,
            'total_ms': total_time
        }

    finally:
        # Cleanup temp CSV
        try:
            Path(csv_path).unlink()
        except Exception:
            pass

        # Cleanup engine
        try:
            engine.close()
        except Exception:
            pass


def main():
    """Run all performance benchmarks"""
    print("\n" + "="*60)
    print("  NEUTRON CORE PERFORMANCE SANITY CHECK")
    print("="*60)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    results = []

    # Small dataset
    result = run_query_benchmark("small", 100)
    if result:
        results.append(result)

    # Medium dataset
    result = run_query_benchmark("medium", 10000)
    if result:
        results.append(result)

    # Large dataset
    result = run_query_benchmark("large", 100000)
    if result:
        results.append(result)

    # Print summary table
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    print(f"{'Size':<10} {'Rows':<10} {'Load':<10} {'Select':<10} {'Agg':<10} {'Filter':<10} {'Join':<10} {'Export':<10} {'Total':<12}")
    print("-"*60)

    for r in results:
        print(
            f"{r['size']:<10} "
            f"{r['rows']:<10,} "
            f"{r['load_ms']:<9.1f}ms "
            f"{r['select_ms']:<9.1f}ms "
            f"{r['aggregate_ms']:<9.1f}ms "
            f"{r['filter_ms']:<9.1f}ms "
            f"{r['join_ms']:<9.1f}ms "
            f"{r['export_ms']:<9.1f}ms "
            f"{r['total_ms']:<11.1f}ms"
        )

    print("="*60)
    print("\n✓ Performance sanity check complete")
    print("\nNOTE: These are baseline timings, not rigorous benchmarks.")
    print("      Use for regression detection, not absolute performance claims.")
    print("      DuckDB in-memory execution is very fast - expect sub-second queries.")


if __name__ == "__main__":
    main()
