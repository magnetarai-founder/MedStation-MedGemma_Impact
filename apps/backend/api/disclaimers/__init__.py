"""
Disclaimers Package

Legal disclaimers for ElohimOS:
- Medical advice disclaimers
- AI content warnings
- Liability limitations
- Export control notices
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
    # Types
    "DisclaimerType",
    # Content
    "MEDICAL_DISCLAIMER_SHORT",
    "MEDICAL_DISCLAIMER_FULL",
    "AI_CONTENT_DISCLAIMER",
    "LIABILITY_DISCLAIMER",
    "EXPORT_CONTROL_NOTICE",
    "HIPAA_COMPLIANCE_NOTICE",
    "DATA_PRIVACY_NOTICE",
    "MEDICAL_TEMPLATE_BANNER",
    # Service
    "DisclaimerService",
]
