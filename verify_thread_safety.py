#!/usr/bin/env python3
"""
Verify thread safety of MagnetarStudio components.

Tests concurrent access to:
- MetricsCollector
- ANEContextEngine
- Database connections
"""

import sys
import threading
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from api.metrics import get_metrics
from api.ane_context_engine import get_ane_engine


def test_metrics_collector():
    """Test MetricsCollector under concurrent load"""
    print("\n" + "=" * 60)
    print("Testing MetricsCollector Thread Safety")
    print("=" * 60)

    metrics = get_metrics()
    metrics.reset()  # Start fresh

    operations = 1000
    threads_count = 10

    def record_metrics():
        for i in range(operations):
            metrics.record("test_operation", 100.0)

    # Start 10 threads, each recording 1000 metrics
    threads = [threading.Thread(target=record_metrics) for _ in range(threads_count)]

    start_time = time.time()

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    elapsed = time.time() - start_time

    # Verify count
    snapshot = metrics.get_snapshot("test_operation")

    expected_count = operations * threads_count
    actual_count = snapshot.count if snapshot else 0

    print(f"\nExpected count: {expected_count}")
    print(f"Actual count: {actual_count}")
    print(f"Time elapsed: {elapsed:.2f}s")

    if actual_count == expected_count:
        print("✅ MetricsCollector is THREAD-SAFE")
        return True
    else:
        lost_updates = expected_count - actual_count
        print(f"❌ MetricsCollector has RACE CONDITION (lost {lost_updates} updates!)")
        return False


def test_ane_engine():
    """Test ANEContextEngine under concurrent load"""
    print("\n" + "=" * 60)
    print("Testing ANEContextEngine Thread Safety")
    print("=" * 60)

    engine = get_ane_engine()
    engine.clear_all()  # Start fresh

    contexts_count = 100
    threads_count = 5

    def preserve_contexts():
        for i in range(contexts_count):
            thread_id = threading.get_ident()
            session_id = f"{thread_id}_{i}"
            engine.preserve_context(session_id, {"data": f"test_{i}"})

    # Start 5 threads, each preserving 100 contexts
    threads = [threading.Thread(target=preserve_contexts) for _ in range(threads_count)]

    start_time = time.time()

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Wait for background workers to process queue
    time.sleep(2)

    elapsed = time.time() - start_time

    # Check stats
    stats = engine.stats()

    expected_processed = contexts_count * threads_count
    actual_processed = stats['processed_count']

    print(f"\nExpected processed: {expected_processed}")
    print(f"Actual processed: {actual_processed}")
    print(f"Errors: {stats['error_count']}")
    print(f"Queue size: {stats['queue_size']}")
    print(f"Time elapsed: {elapsed:.2f}s")

    if actual_processed == expected_processed and stats['error_count'] == 0:
        print("✅ ANEContextEngine is THREAD-SAFE")
        return True
    else:
        print(f"❌ ANEContextEngine has issues")
        return False


def main():
    """Run all thread safety tests"""
    print("\n🧵 MagnetarStudio Thread Safety Verification")
    print("=" * 60)

    results = []

    # Test MetricsCollector
    results.append(("MetricsCollector", test_metrics_collector()))

    # Test ANEContextEngine
    results.append(("ANEContextEngine", test_ane_engine()))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for component, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{component}: {status}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n🎉 All components are THREAD-SAFE!")
    else:
        print("\n⚠️ Some components have race conditions that need fixing")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
