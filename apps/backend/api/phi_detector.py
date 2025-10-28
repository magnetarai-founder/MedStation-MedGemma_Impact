"""
PHI (Protected Health Information) Detection Service

Detects potential PHI in workflow form fields and shows warnings.
Does not block - only warns users to ensure HIPAA compliance.

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

This service focuses on field name detection (form builder warnings).
"""

import re
from typing import List, Dict, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PHICategory(str, Enum):
    """Categories of PHI identifiers"""
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


class PHIPattern:
    """PHI field name pattern with metadata"""

    def __init__(
        self,
        pattern: str,
        category: PHICategory,
        risk_level: PHIRiskLevel,
        description: str
    ):
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.category = category
        self.risk_level = risk_level
        self.description = description


class PHIDetectionResult:
    """Result of PHI detection"""

    def __init__(
        self,
        is_phi: bool,
        detected_patterns: List[Dict],
        risk_level: PHIRiskLevel,
        warning_message: Optional[str] = None
    ):
        self.is_phi = is_phi
        self.detected_patterns = detected_patterns
        self.risk_level = risk_level
        self.warning_message = warning_message


class PHIDetector:
    """
    Service for detecting potential PHI in form fields
    """

    def __init__(self):
        """Initialize PHI detector with patterns"""
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> List[PHIPattern]:
        """
        Build comprehensive PHI field name patterns

        Returns:
            List of PHI patterns
        """
        return [
            # Names (High Risk)
            PHIPattern(
                r'\b(first|last|full|legal|maiden|nick)?_?name\b',
                PHICategory.NAME,
                PHIRiskLevel.HIGH,
                "Name fields are direct identifiers"
            ),
            PHIPattern(
                r'\b(patient|person|individual|subject)_?(name|id)?\b',
                PHICategory.NAME,
                PHIRiskLevel.HIGH,
                "Patient/person identifiers"
            ),

            # Dates (High Risk)
            PHIPattern(
                r'\b(date|day)_?of_?birth\b',
                PHICategory.DATE,
                PHIRiskLevel.HIGH,
                "Date of birth is a direct identifier"
            ),
            PHIPattern(
                r'\b(dob|birthdate|birthday)\b',
                PHICategory.DATE,
                PHIRiskLevel.HIGH,
                "Birth date abbreviations"
            ),
            PHIPattern(
                r'\b(admission|discharge|death|visit)_?date\b',
                PHICategory.DATE,
                PHIRiskLevel.MEDIUM,
                "Medical service dates"
            ),

            # Contact Information (High Risk)
            PHIPattern(
                r'\b(phone|telephone|mobile|cell|fax)(_?number)?\b',
                PHICategory.CONTACT,
                PHIRiskLevel.HIGH,
                "Phone/fax numbers are direct identifiers"
            ),
            PHIPattern(
                r'\b(email|e_?mail)(_?address)?\b',
                PHICategory.CONTACT,
                PHIRiskLevel.HIGH,
                "Email addresses are direct identifiers"
            ),
            PHIPattern(
                r'\b(street|home|mailing|physical)_?address\b',
                PHICategory.LOCATION,
                PHIRiskLevel.HIGH,
                "Street addresses are direct identifiers"
            ),
            PHIPattern(
                r'\b(zip|postal)_?code\b',
                PHICategory.LOCATION,
                PHIRiskLevel.MEDIUM,
                "ZIP codes (if more specific than first 3 digits)"
            ),
            PHIPattern(
                r'\b(city|town|county|district)\b',
                PHICategory.LOCATION,
                PHIRiskLevel.LOW,
                "Geographic subdivisions smaller than state"
            ),

            # Identifiers (High Risk)
            PHIPattern(
                r'\b(ssn|social_?security(_?number)?)\b',
                PHICategory.IDENTIFIER,
                PHIRiskLevel.HIGH,
                "Social Security numbers are direct identifiers"
            ),
            PHIPattern(
                r'\b(mrn|medical_?record(_?number)?)\b',
                PHICategory.IDENTIFIER,
                PHIRiskLevel.HIGH,
                "Medical record numbers are direct identifiers"
            ),
            PHIPattern(
                r'\b(patient|member|subscriber|account)_?(id|number|num)\b',
                PHICategory.IDENTIFIER,
                PHIRiskLevel.HIGH,
                "Patient/member/account identifiers"
            ),
            PHIPattern(
                r'\b(health_?plan|insurance|policy)(_?number|_?id)?\b',
                PHICategory.FINANCIAL,
                PHIRiskLevel.HIGH,
                "Health plan beneficiary numbers"
            ),
            PHIPattern(
                r'\b(certificate|license|permit)(_?number|_?id)?\b',
                PHICategory.IDENTIFIER,
                PHIRiskLevel.MEDIUM,
                "Certificate/license numbers"
            ),
            PHIPattern(
                r'\b(device|implant|serial)(_?number|_?id)?\b',
                PHICategory.IDENTIFIER,
                PHIRiskLevel.MEDIUM,
                "Device identifiers and serial numbers"
            ),
            PHIPattern(
                r'\b(url|website|web_?address|ip_?address)\b',
                PHICategory.IDENTIFIER,
                PHIRiskLevel.LOW,
                "URLs and IP addresses"
            ),

            # Medical Information (Medium-High Risk)
            PHIPattern(
                r'\b(diagnosis|condition|disease|illness|symptom)\b',
                PHICategory.MEDICAL,
                PHIRiskLevel.MEDIUM,
                "Medical diagnoses and conditions"
            ),
            PHIPattern(
                r'\b(prescription|medication|drug|treatment)\b',
                PHICategory.MEDICAL,
                PHIRiskLevel.MEDIUM,
                "Prescription and treatment information"
            ),
            PHIPattern(
                r'\b(procedure|surgery|operation|test|lab)\b',
                PHICategory.MEDICAL,
                PHIRiskLevel.MEDIUM,
                "Medical procedures and tests"
            ),
            PHIPattern(
                r'\b(allerg(y|ies)|reaction)\b',
                PHICategory.MEDICAL,
                PHIRiskLevel.MEDIUM,
                "Allergy information"
            ),
            PHIPattern(
                r'\b(vital_?signs?|blood_?pressure|heart_?rate|temperature)\b',
                PHICategory.MEDICAL,
                PHIRiskLevel.LOW,
                "Vital signs and measurements"
            ),

            # Biometric (High Risk)
            PHIPattern(
                r'\b(fingerprint|retina|iris|voice_?print|dna)\b',
                PHICategory.BIOMETRIC,
                PHIRiskLevel.HIGH,
                "Biometric identifiers"
            ),
            PHIPattern(
                r'\b(photo|image|picture|scan).*(?:face|facial|full_?body)?\b',
                PHICategory.BIOMETRIC,
                PHIRiskLevel.MEDIUM,
                "Photographic images"
            ),

            # Financial (Medium Risk)
            PHIPattern(
                r'\b(credit_?card|debit_?card|bank|routing)(_?number)?\b',
                PHICategory.FINANCIAL,
                PHIRiskLevel.MEDIUM,
                "Financial account numbers"
            ),
            PHIPattern(
                r'\b(claim|billing|charge|payment)(_?number|_?id)?\b',
                PHICategory.FINANCIAL,
                PHIRiskLevel.LOW,
                "Billing and claim identifiers"
            ),
        ]

    def detect_field(self, field_name: str) -> PHIDetectionResult:
        """
        Detect if a single field name potentially contains PHI

        Args:
            field_name: Field name to check

        Returns:
            PHIDetectionResult with detection details
        """
        detected = []
        max_risk = PHIRiskLevel.NONE

        # Check field name against all patterns
        for phi_pattern in self.patterns:
            if phi_pattern.pattern.search(field_name):
                detected.append({
                    "category": phi_pattern.category.value,
                    "risk_level": phi_pattern.risk_level.value,
                    "description": phi_pattern.description,
                    "matched_pattern": phi_pattern.pattern.pattern
                })

                # Track highest risk level
                if self._risk_priority(phi_pattern.risk_level) > self._risk_priority(max_risk):
                    max_risk = phi_pattern.risk_level

        # Generate warning message
        warning = None
        if detected:
            warning = self._generate_warning(detected, max_risk)

        return PHIDetectionResult(
            is_phi=len(detected) > 0,
            detected_patterns=detected,
            risk_level=max_risk,
            warning_message=warning
        )

    def detect_form(self, field_names: List[str]) -> PHIDetectionResult:
        """
        Detect if a form contains potential PHI fields

        Args:
            field_names: List of field names in the form

        Returns:
            PHIDetectionResult for the entire form
        """
        all_detected = []
        max_risk = PHIRiskLevel.NONE
        phi_field_count = 0

        for field_name in field_names:
            result = self.detect_field(field_name)
            if result.is_phi:
                phi_field_count += 1
                all_detected.extend(result.detected_patterns)

                if self._risk_priority(result.risk_level) > self._risk_priority(max_risk):
                    max_risk = result.risk_level

        # Generate form-level warning
        warning = None
        if all_detected:
            warning = self._generate_form_warning(phi_field_count, len(field_names), max_risk)

        return PHIDetectionResult(
            is_phi=len(all_detected) > 0,
            detected_patterns=all_detected,
            risk_level=max_risk,
            warning_message=warning
        )

    def _risk_priority(self, risk_level: PHIRiskLevel) -> int:
        """
        Get numeric priority for risk level

        Args:
            risk_level: Risk level enum

        Returns:
            Priority value (0-3)
        """
        priority_map = {
            PHIRiskLevel.NONE: 0,
            PHIRiskLevel.LOW: 1,
            PHIRiskLevel.MEDIUM: 2,
            PHIRiskLevel.HIGH: 3
        }
        return priority_map.get(risk_level, 0)

    def _generate_warning(self, detected: List[Dict], risk_level: PHIRiskLevel) -> str:
        """
        Generate warning message for detected PHI

        Args:
            detected: List of detected patterns
            risk_level: Maximum risk level

        Returns:
            Warning message string
        """
        if risk_level == PHIRiskLevel.HIGH:
            return (
                "⚠️ This field may collect Protected Health Information (PHI). "
                "Ensure HIPAA compliance and obtain proper consent before collecting this data."
            )
        elif risk_level == PHIRiskLevel.MEDIUM:
            return (
                "⚠️ This field may contain sensitive health information. "
                "Consider if HIPAA compliance is required for your use case."
            )
        else:
            return (
                "ℹ️ This field may collect personal information. "
                "Ensure you have appropriate privacy protections in place."
            )

    def _generate_form_warning(
        self,
        phi_field_count: int,
        total_fields: int,
        risk_level: PHIRiskLevel
    ) -> str:
        """
        Generate warning message for form with PHI fields

        Args:
            phi_field_count: Number of PHI fields detected
            total_fields: Total number of fields
            risk_level: Maximum risk level

        Returns:
            Form-level warning message
        """
        phi_percentage = (phi_field_count / total_fields * 100) if total_fields > 0 else 0

        if risk_level == PHIRiskLevel.HIGH or phi_percentage > 50:
            return (
                f"⚠️ WARNING: This form collects Protected Health Information (PHI)\n\n"
                f"{phi_field_count} of {total_fields} fields may contain PHI. "
                f"This form is subject to HIPAA regulations.\n\n"
                f"Required actions:\n"
                f"• Obtain BAA (Business Associate Agreement) if handling PHI\n"
                f"• Implement access controls and audit logging\n"
                f"• Ensure encryption at rest and in transit\n"
                f"• Train staff on HIPAA compliance\n"
                f"• Establish breach notification procedures"
            )
        elif risk_level == PHIRiskLevel.MEDIUM:
            return (
                f"⚠️ CAUTION: This form may collect sensitive health information\n\n"
                f"{phi_field_count} of {total_fields} fields detected. "
                f"Consider if HIPAA compliance applies to your use case.\n\n"
                f"Recommended actions:\n"
                f"• Review if you qualify as a covered entity\n"
                f"• Implement appropriate privacy safeguards\n"
                f"• Document your compliance approach"
            )
        else:
            return (
                f"ℹ️ INFO: This form collects personal information\n\n"
                f"{phi_field_count} of {total_fields} fields detected. "
                f"Ensure appropriate privacy protections are in place."
            )

    def get_phi_categories(self) -> List[str]:
        """
        Get list of all PHI categories

        Returns:
            List of category names
        """
        return [cat.value for cat in PHICategory]

    def get_compliance_guidelines(self) -> Dict[str, str]:
        """
        Get HIPAA compliance guidelines

        Returns:
            Dictionary of guidelines by topic
        """
        return {
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
            )
        }


# Global PHI detector instance
_phi_detector: Optional[PHIDetector] = None


def get_phi_detector() -> PHIDetector:
    """
    Get or create global PHI detector instance

    Returns:
        PHIDetector instance
    """
    global _phi_detector

    if _phi_detector is None:
        _phi_detector = PHIDetector()

    return _phi_detector
