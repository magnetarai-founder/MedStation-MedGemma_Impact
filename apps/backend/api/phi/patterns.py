"""
PHI (Protected Health Information) Patterns and Constants

Static data for HIPAA-compliant PHI detection in form fields.
Extracted from phi_detector.py during P2 decomposition.

HIPAA defines 18 identifiers as PHI:
1. Names
2. Dates (birth, admission, discharge, death)
3. Phone numbers
4. Fax numbers
5. Email addresses
6. Social Security numbers
7. Medical record numbers
8. Health plan beneficiary numbers
9. Account numbers
10. Certificate/license numbers
11. Vehicle identifiers
12. Device identifiers
13. URLs
14. IP addresses
15. Biometric identifiers
16. Full face photos
17. Any other unique identifying number
18. Geographic subdivisions smaller than state

Contains:
- PHICategory: Categories of PHI identifiers
- PHIRiskLevel: Risk levels for detected PHI
- PHI_PATTERN_DEFINITIONS: Raw pattern data (without compiled regex)
- HIPAA_COMPLIANCE_GUIDELINES: Compliance guidance by topic
- get_risk_priority(): Convert risk level to numeric priority
"""

import re
from enum import Enum
from typing import List, Dict, Tuple


# ============================================
# PHI ENUMS
# ============================================

class PHICategory(str, Enum):
    """Categories of PHI identifiers per HIPAA"""
    NAME = "name"
    DATE = "date"
    CONTACT = "contact"
    IDENTIFIER = "identifier"
    MEDICAL = "medical"
    LOCATION = "location"
    FINANCIAL = "financial"
    BIOMETRIC = "biometric"


class PHIRiskLevel(str, Enum):
    """Risk level for PHI detection"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================
# RISK PRIORITY MAPPING
# ============================================

RISK_PRIORITY_MAP: Dict[PHIRiskLevel, int] = {
    PHIRiskLevel.NONE: 0,
    PHIRiskLevel.LOW: 1,
    PHIRiskLevel.MEDIUM: 2,
    PHIRiskLevel.HIGH: 3,
}
"""Numeric priority for risk levels (higher = more severe)"""


def get_risk_priority(risk_level: PHIRiskLevel) -> int:
    """
    Get numeric priority for risk level.

    Args:
        risk_level: Risk level enum

    Returns:
        Priority value (0-3, higher = more severe)

    Examples:
        >>> get_risk_priority(PHIRiskLevel.HIGH)
        3
        >>> get_risk_priority(PHIRiskLevel.NONE)
        0
    """
    return RISK_PRIORITY_MAP.get(risk_level, 0)


# ============================================
# PHI PATTERN DEFINITIONS
# ============================================

# Each tuple: (regex_pattern, category, risk_level, description)
PHI_PATTERN_DEFINITIONS: List[Tuple[str, PHICategory, PHIRiskLevel, str]] = [
    # ===== Names (High Risk) =====
    (
        r'\b(first|last|full|legal|maiden|nick)?_?name\b',
        PHICategory.NAME,
        PHIRiskLevel.HIGH,
        "Name fields are direct identifiers"
    ),
    (
        r'\b(patient|person|individual|subject)_?(name|id)?\b',
        PHICategory.NAME,
        PHIRiskLevel.HIGH,
        "Patient/person identifiers"
    ),

    # ===== Dates (High Risk) =====
    (
        r'\b(date|day)_?of_?birth\b',
        PHICategory.DATE,
        PHIRiskLevel.HIGH,
        "Date of birth is a direct identifier"
    ),
    (
        r'\b(dob|birthdate|birthday)\b',
        PHICategory.DATE,
        PHIRiskLevel.HIGH,
        "Birth date abbreviations"
    ),
    (
        r'\b(admission|discharge|death|visit)_?date\b',
        PHICategory.DATE,
        PHIRiskLevel.MEDIUM,
        "Medical service dates"
    ),

    # ===== Contact Information (High Risk) =====
    (
        r'\b(phone|telephone|mobile|cell|fax)(_?number)?\b',
        PHICategory.CONTACT,
        PHIRiskLevel.HIGH,
        "Phone/fax numbers are direct identifiers"
    ),
    (
        r'\b(email|e_?mail)(_?address)?\b',
        PHICategory.CONTACT,
        PHIRiskLevel.HIGH,
        "Email addresses are direct identifiers"
    ),
    (
        r'\b(street|home|mailing|physical)_?address\b',
        PHICategory.LOCATION,
        PHIRiskLevel.HIGH,
        "Street addresses are direct identifiers"
    ),
    (
        r'\b(zip|postal)_?code\b',
        PHICategory.LOCATION,
        PHIRiskLevel.MEDIUM,
        "ZIP codes (if more specific than first 3 digits)"
    ),
    (
        r'\b(city|town|county|district)\b',
        PHICategory.LOCATION,
        PHIRiskLevel.LOW,
        "Geographic subdivisions smaller than state"
    ),

    # ===== Identifiers (High Risk) =====
    (
        r'\b(ssn|social_?security(_?number)?)\b',
        PHICategory.IDENTIFIER,
        PHIRiskLevel.HIGH,
        "Social Security numbers are direct identifiers"
    ),
    (
        r'\b(mrn|medical_?record(_?number)?)\b',
        PHICategory.IDENTIFIER,
        PHIRiskLevel.HIGH,
        "Medical record numbers are direct identifiers"
    ),
    (
        r'\b(patient|member|subscriber|account)_?(id|number|num)\b',
        PHICategory.IDENTIFIER,
        PHIRiskLevel.HIGH,
        "Patient/member/account identifiers"
    ),
    (
        r'\b(health_?plan|insurance|policy)(_?number|_?id)?\b',
        PHICategory.FINANCIAL,
        PHIRiskLevel.HIGH,
        "Health plan beneficiary numbers"
    ),
    (
        r'\b(certificate|license|permit)(_?number|_?id)?\b',
        PHICategory.IDENTIFIER,
        PHIRiskLevel.MEDIUM,
        "Certificate/license numbers"
    ),
    (
        r'\b(device|implant|serial)(_?number|_?id)?\b',
        PHICategory.IDENTIFIER,
        PHIRiskLevel.MEDIUM,
        "Device identifiers and serial numbers"
    ),
    (
        r'\b(url|website|web_?address|ip_?address)\b',
        PHICategory.IDENTIFIER,
        PHIRiskLevel.LOW,
        "URLs and IP addresses"
    ),

    # ===== Medical Information (Medium-High Risk) =====
    (
        r'\b(diagnosis|condition|disease|illness|symptom)\b',
        PHICategory.MEDICAL,
        PHIRiskLevel.MEDIUM,
        "Medical diagnoses and conditions"
    ),
    (
        r'\b(prescription|medication|drug|treatment)\b',
        PHICategory.MEDICAL,
        PHIRiskLevel.MEDIUM,
        "Prescription and treatment information"
    ),
    (
        r'\b(procedure|surgery|operation|test|lab)\b',
        PHICategory.MEDICAL,
        PHIRiskLevel.MEDIUM,
        "Medical procedures and tests"
    ),
    (
        r'\b(allerg(y|ies)|reaction)\b',
        PHICategory.MEDICAL,
        PHIRiskLevel.MEDIUM,
        "Allergy information"
    ),
    (
        r'\b(vital_?signs?|blood_?pressure|heart_?rate|temperature)\b',
        PHICategory.MEDICAL,
        PHIRiskLevel.LOW,
        "Vital signs and measurements"
    ),

    # ===== Biometric (High Risk) =====
    (
        r'\b(fingerprint|retina|iris|voice_?print|dna)\b',
        PHICategory.BIOMETRIC,
        PHIRiskLevel.HIGH,
        "Biometric identifiers"
    ),
    (
        r'\b(photo|image|picture|scan).*(?:face|facial|full_?body)?\b',
        PHICategory.BIOMETRIC,
        PHIRiskLevel.MEDIUM,
        "Photographic images"
    ),

    # ===== Financial (Medium Risk) =====
    (
        r'\b(credit_?card|debit_?card|bank|routing)(_?number)?\b',
        PHICategory.FINANCIAL,
        PHIRiskLevel.MEDIUM,
        "Financial account numbers"
    ),
    (
        r'\b(claim|billing|charge|payment)(_?number|_?id)?\b',
        PHICategory.FINANCIAL,
        PHIRiskLevel.LOW,
        "Billing and claim identifiers"
    ),
]
"""
PHI field name patterns for HIPAA compliance detection.

Each entry is a tuple of:
- regex_pattern: Pattern to match against field names
- category: PHICategory enum value
- risk_level: PHIRiskLevel enum value
- description: Human-readable explanation
"""


# ============================================
# HIPAA COMPLIANCE GUIDELINES
# ============================================

HIPAA_COMPLIANCE_GUIDELINES: Dict[str, str] = {
    "overview": (
        "HIPAA (Health Insurance Portability and Accountability Act) "
        "protects the privacy and security of individuals' health information. "
        "If you collect, store, or transmit PHI, you must comply with HIPAA."
    ),
    "covered_entities": (
        "Covered entities include: health plans, healthcare clearinghouses, "
        "and healthcare providers who transmit health information electronically."
    ),
    "business_associates": (
        "Business associates are third parties that handle PHI on behalf of "
        "covered entities. They must sign a Business Associate Agreement (BAA)."
    ),
    "technical_safeguards": (
        "Required technical safeguards: access controls, audit controls, "
        "integrity controls, transmission security, and encryption."
    ),
    "administrative_safeguards": (
        "Required administrative safeguards: security management process, "
        "workforce training, contingency planning, and business associate contracts."
    ),
    "physical_safeguards": (
        "Required physical safeguards: facility access controls, "
        "workstation security, and device/media controls."
    ),
    "breach_notification": (
        "Breaches affecting 500+ individuals must be reported to HHS within 60 days. "
        "Smaller breaches must be reported annually."
    ),
    "penalties": (
        "HIPAA violations can result in penalties from $100 to $50,000 per violation, "
        "up to $1.5 million per year. Criminal penalties include fines and imprisonment."
    ),
}
"""
HIPAA compliance guidelines by topic.
These are informational only - consult legal counsel for compliance decisions.
"""


# ============================================
# WARNING MESSAGE TEMPLATES
# ============================================

WARNING_FIELD_HIGH: str = (
    "⚠️ This field may collect Protected Health Information (PHI). "
    "Ensure HIPAA compliance and obtain proper consent before collecting this data."
)

WARNING_FIELD_MEDIUM: str = (
    "⚠️ This field may contain sensitive health information. "
    "Consider if HIPAA compliance is required for your use case."
)

WARNING_FIELD_LOW: str = (
    "ℹ️ This field may collect personal information. "
    "Ensure you have appropriate privacy protections in place."
)

WARNING_FORM_HIGH_TEMPLATE: str = (
    "⚠️ WARNING: This form collects Protected Health Information (PHI)\n\n"
    "{phi_count} of {total_count} fields may contain PHI. "
    "This form is subject to HIPAA regulations.\n\n"
    "Required actions:\n"
    "• Obtain BAA (Business Associate Agreement) if handling PHI\n"
    "• Implement access controls and audit logging\n"
    "• Ensure encryption at rest and in transit\n"
    "• Train staff on HIPAA compliance\n"
    "• Establish breach notification procedures"
)

WARNING_FORM_MEDIUM_TEMPLATE: str = (
    "⚠️ CAUTION: This form may collect sensitive health information\n\n"
    "{phi_count} of {total_count} fields detected. "
    "Consider if HIPAA compliance applies to your use case.\n\n"
    "Recommended actions:\n"
    "• Review if you qualify as a covered entity\n"
    "• Implement appropriate privacy safeguards\n"
    "• Document your compliance approach"
)

WARNING_FORM_LOW_TEMPLATE: str = (
    "ℹ️ INFO: This form collects personal information\n\n"
    "{phi_count} of {total_count} fields detected. "
    "Ensure appropriate privacy protections are in place."
)


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_all_categories() -> List[str]:
    """Get list of all PHI category names."""
    return [cat.value for cat in PHICategory]


def get_all_risk_levels() -> List[str]:
    """Get list of all risk level names."""
    return [level.value for level in PHIRiskLevel]


def get_pattern_count() -> int:
    """Get total number of PHI patterns defined."""
    return len(PHI_PATTERN_DEFINITIONS)


def get_high_risk_patterns() -> List[Tuple[str, PHICategory, PHIRiskLevel, str]]:
    """Get only high-risk PHI patterns."""
    return [p for p in PHI_PATTERN_DEFINITIONS if p[2] == PHIRiskLevel.HIGH]


def get_patterns_by_category(category: PHICategory) -> List[Tuple[str, PHICategory, PHIRiskLevel, str]]:
    """Get PHI patterns for a specific category."""
    return [p for p in PHI_PATTERN_DEFINITIONS if p[1] == category]


__all__ = [
    # Enums
    "PHICategory",
    "PHIRiskLevel",
    # Pattern data
    "PHI_PATTERN_DEFINITIONS",
    "RISK_PRIORITY_MAP",
    # Compliance
    "HIPAA_COMPLIANCE_GUIDELINES",
    # Warning templates
    "WARNING_FIELD_HIGH",
    "WARNING_FIELD_MEDIUM",
    "WARNING_FIELD_LOW",
    "WARNING_FORM_HIGH_TEMPLATE",
    "WARNING_FORM_MEDIUM_TEMPLATE",
    "WARNING_FORM_LOW_TEMPLATE",
    # Functions
    "get_risk_priority",
    "get_all_categories",
    "get_all_risk_levels",
    "get_pattern_count",
    "get_high_risk_patterns",
    "get_patterns_by_category",
]
