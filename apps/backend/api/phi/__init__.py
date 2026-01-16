"""
PHI Detection Package

HIPAA-compliant PHI (Protected Health Information) detection:
- Detects all 18 HIPAA-defined identifiers
- Form field warning system
- Risk-level based alerting
"""

from api.phi.patterns import (
    PHICategory,
    PHIRiskLevel,
    RISK_PRIORITY_MAP,
    PHI_PATTERN_DEFINITIONS,
    HIPAA_COMPLIANCE_GUIDELINES,
    WARNING_FIELD_HIGH,
    WARNING_FIELD_MEDIUM,
    WARNING_FIELD_LOW,
    get_risk_priority,
    get_all_categories,
)
from api.phi.detector import (
    PHIPattern,
    PHIDetectionResult,
    PHIDetector,
)

__all__ = [
    # Enums
    "PHICategory",
    "PHIRiskLevel",
    # Constants
    "RISK_PRIORITY_MAP",
    "PHI_PATTERN_DEFINITIONS",
    "HIPAA_COMPLIANCE_GUIDELINES",
    "WARNING_FIELD_HIGH",
    "WARNING_FIELD_MEDIUM",
    "WARNING_FIELD_LOW",
    # Helper functions
    "get_risk_priority",
    "get_all_categories",
    # Detector classes
    "PHIPattern",
    "PHIDetectionResult",
    "PHIDetector",
]
