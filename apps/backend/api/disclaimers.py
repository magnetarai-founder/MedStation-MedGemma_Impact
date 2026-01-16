"""
Compatibility Shim for Disclaimers Service

The implementation now lives in the `api.disclaimers` package:
- api.disclaimers.service: DisclaimerService class

This shim maintains backward compatibility.
"""

from api.disclaimers.content import (
    DisclaimerType,
    MEDICAL_DISCLAIMER_SHORT,
    MEDICAL_DISCLAIMER_FULL,
    AI_CONTENT_DISCLAIMER,
    LIABILITY_DISCLAIMER,
    EXPORT_CONTROL_NOTICE,
    HIPAA_COMPLIANCE_NOTICE,
    DATA_PRIVACY_NOTICE,
    MEDICAL_TEMPLATE_BANNER,
)
from api.disclaimers.service import DisclaimerService

__all__ = [
    "DisclaimerType",
    "MEDICAL_DISCLAIMER_SHORT",
    "MEDICAL_DISCLAIMER_FULL",
    "AI_CONTENT_DISCLAIMER",
    "LIABILITY_DISCLAIMER",
    "EXPORT_CONTROL_NOTICE",
    "HIPAA_COMPLIANCE_NOTICE",
    "DATA_PRIVACY_NOTICE",
    "MEDICAL_TEMPLATE_BANNER",
    "DisclaimerService",
]
