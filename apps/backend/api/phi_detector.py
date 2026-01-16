"""
Compatibility Shim for PHI Detector

The implementation now lives in the `api.phi` package:
- api.phi.detector: PHIDetector class and related types

This shim maintains backward compatibility.
"""

# Re-export everything from the new package location
from api.phi.detector import (
    PHIPattern,
    PHIDetectionResult,
    PHIDetector,
)

# Re-export commonly used items from patterns for convenience
from api.phi.patterns import (
    PHICategory,
    PHIRiskLevel,
)

__all__ = [
    "PHIPattern",
    "PHIDetectionResult",
    "PHIDetector",
    "PHICategory",
    "PHIRiskLevel",
]
