"""
Type and Size Estimation Utilities

Helpers for estimating data sizes and memory usage to prevent
resource exhaustion during JSON flattening operations.
"""
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


def quick_size_estimate(data: Any, limit: int) -> int:
    """
    Conservative upper-bound estimate by multiplying lengths of lists encountered.

    Short-circuits when product reaches limit to avoid unnecessary computation.

    Args:
        data: JSON data structure to estimate
        limit: Maximum product to calculate before short-circuiting

    Returns:
        Estimated size as product of list lengths
    """
    product = 1

    def walk(obj: Any):
        nonlocal product
        if product >= limit:
            return
        if isinstance(obj, list):
            try:
                n = len(obj) or 1
            except Exception:
                n = 1
            product *= n
            for it in obj[:2]:  # sample a few items
                walk(it)
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)

    walk(data)
    return product


def estimate_rows(data: Any, threshold: int = 100_000, max_inspect: int = 2) -> int:
    """
    Roughly estimate expanded row count, with early cutoff.

    Heuristic rules:
    - For dict: multiply factors of values.
    - For list: multiply by length, then inspect up to max_inspect items to account for nested arrays.
    - For scalars: factor 1.

    Overestimates are fine (we only use this to decide fallbacks).

    Args:
        data: JSON data structure to estimate
        threshold: Early cutoff threshold
        max_inspect: Maximum number of list items to inspect

    Returns:
        Estimated row count after array expansion
    """
    estimate = 1

    def rec(obj: Any):
        nonlocal estimate
        if estimate >= threshold:
            return
        if isinstance(obj, dict):
            for v in obj.values():
                rec(v)
                if estimate >= threshold:
                    return
        elif isinstance(obj, list):
            try:
                length = len(obj)
            except Exception:
                length = 1
            estimate *= max(1, length)
            # Inspect a few items to catch nested arrays
            for item in obj[:max_inspect]:
                rec(item)
                if estimate >= threshold:
                    return
        else:
            return

    rec(data)
    return estimate


def get_memory_usage_mb() -> Optional[int]:
    """
    Best-effort current process memory usage in MB.

    Tries psutil first, then falls back to resource module.

    Returns:
        Memory usage in MB, or None if unable to determine
    """
    try:
        import psutil
        process = psutil.Process()
        return int(process.memory_info().rss / (1024 * 1024))
    except Exception:
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # On Linux, ru_maxrss is in KB; on macOS it's bytes
            if usage < 10_000_000:  # likely KB
                return int(usage / 1024)
            return int(usage / (1024 * 1024))
        except Exception:
            return None
