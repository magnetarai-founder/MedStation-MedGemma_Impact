#!/usr/bin/env python3
"""
Pulsar Core Performance Sanity Check

Simple performance baseline script to time key pulsar_core operations.
Uses time.perf_counter() for accurate timing - no heavy benchmarking framework.

Usage:
    cd /path/to/ElohimOS
    export PYTHONPATH="packages:$PYTHONPATH"
    python3 tools/perf/pulsar_core_perf.py

Expected baseline (reference machine):
- Small JSON (10 records): < 100ms
- Medium JSON (1000 records): < 500ms
- Large JSON (10000 records): < 3000ms
"""

import sys
import time
import json
import tempfile
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages"))

from pulsar_core import JsonToExcelEngine


def generate_test_json(num_records: int) -> dict:
    """Generate synthetic nested JSON data for testing"""
    return {
        "metadata": {
            "generated_at": "2025-11-19T00:00:00Z",
            "record_count": num_records,
            "version": "1.0"
        },
        "data": [
            {
                "id": i,
                "name": f"Record_{i}",
                "value": i * 1.5,
                "category": f"Category_{i % 10}",
                "nested": {
                    "field1": f"value_{i}",
                    "field2": i * 2,
                    "deep": {
                        "level3": f"deep_value_{i}"
                    }
                },
                "tags": [f"tag_{j}" for j in range(i % 5)],
                "metadata": {
                    "created": "2025-01-01",
                    "updated": "2025-11-19",
                    "status": "active" if i % 2 == 0 else "inactive"
                }
            }
            for i in range(num_records)
        ]
    }


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


def run_json_normalization_benchmark(size: str, num_records: int):
    """Benchmark JSON normalization for given size"""
    print(f"\n{'#'*60}")
    print(f"# {size.upper()} JSON NORMALIZATION ({num_records:,} records)")
    print(f"{'#'*60}")

    engine = JsonToExcelEngine()

    # Generate test data
    test_data = generate_test_json(num_records)

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        json_path = f.name

    try:
        # Time: Load JSON
        def load_json():
            return engine.load_json(json_path)

        load_result, load_time = time_operation("Load JSON", load_json)

        if not load_result.get('success'):
            print(f"❌ Load failed: {load_result.get('error')}")
            return None

        print(f"  - Columns detected: {len(load_result.get('columns', []))}")
        print(f"  - Data loaded: {load_result.get('data') is not None}")

        # Time: Normalize/Flatten
        def normalize_json():
            return engine.flatten()

        flatten_result, flatten_time = time_operation("Flatten/Normalize", normalize_json)

        if not flatten_result.get('success'):
            print(f"❌ Flatten failed: {flatten_result.get('error')}")
            return None

        df = flatten_result.get('dataframe')
        print(f"  - Rows: {flatten_result.get('rows', 0):,}")
        print(f"  - Columns: {len(df.columns) if df is not None else 0}")

        # Time: Convert to Excel
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_f:
            excel_path = excel_f.name

        def convert_to_excel():
            return engine.convert(
                input_path=json_path,
                output_path=excel_path,
                sheet_name="Data"
            )

        convert_result, convert_time = time_operation(
            "Full JSON → Excel Conversion",
            convert_to_excel
        )

        if convert_result.get('success'):
            excel_size_kb = Path(excel_path).stat().st_size / 1024
            print(f"  - Excel size: {excel_size_kb:.2f} KB")
            print(f"  - Rows written: {convert_result.get('rows', 0):,}")
        else:
            print(f"❌ Conversion failed: {convert_result.get('error')}")

        # Cleanup
        try:
            Path(excel_path).unlink()
        except Exception:
            pass

        # Summary
        total_time = load_time + flatten_time + convert_time
        print(f"\n{'─'*60}")
        print(f"TOTAL TIME: {total_time:.2f}ms")
        print(f"{'─'*60}")

        return {
            'size': size,
            'records': num_records,
            'load_ms': load_time,
            'flatten_ms': flatten_time,
            'convert_ms': convert_time,
            'total_ms': total_time
        }

    finally:
        # Cleanup temp JSON
        try:
            Path(json_path).unlink()
        except Exception:
            pass


def main():
    """Run all performance benchmarks"""
    print("\n" + "="*60)
    print("  PULSAR CORE PERFORMANCE SANITY CHECK")
    print("="*60)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    results = []

    # Small dataset
    result = run_json_normalization_benchmark("small", 10)
    if result:
        results.append(result)

    # Medium dataset
    result = run_json_normalization_benchmark("medium", 1000)
    if result:
        results.append(result)

    # Large dataset
    result = run_json_normalization_benchmark("large", 10000)
    if result:
        results.append(result)

    # Print summary table
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    print(f"{'Size':<10} {'Records':<10} {'Load':<12} {'Flatten':<12} {'Convert':<12} {'Total':<12}")
    print("-"*60)

    for r in results:
        print(
            f"{r['size']:<10} "
            f"{r['records']:<10,} "
            f"{r['load_ms']:<11.2f}ms "
            f"{r['flatten_ms']:<11.2f}ms "
            f"{r['convert_ms']:<11.2f}ms "
            f"{r['total_ms']:<11.2f}ms"
        )

    print("="*60)
    print("\n✓ Performance sanity check complete")
    print("\nNOTE: These are baseline timings, not rigorous benchmarks.")
    print("      Use for regression detection, not absolute performance claims.")


if __name__ == "__main__":
    main()
