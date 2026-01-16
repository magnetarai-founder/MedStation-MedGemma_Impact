"""
PHI (Protected Health Information) Detection Service

Detects potential PHI in workflow form fields and shows warnings.
Does not block - only warns users to ensure HIPAA compliance.

Extracted modules (P2 decomposition):
- phi_patterns.py: PHI pattern definitions, enums, and HIPAA guidelines

This service focuses on field name detection (form builder warnings).
"""

import re
from typing import List, Dict, Optional
import logging

# Import from extracted module (P2 decomposition)
from api.phi.patterns import (
    PHICategory,
    PHIRiskLevel,
    PHI_PATTERN_DEFINITIONS,
    HIPAA_COMPLIANCE_GUIDELINES,
    WARNING_FIELD_HIGH,
    WARNING_FIELD_MEDIUM,
    WARNING_FIELD_LOW,
    get_risk_priority,
    get_all_categories,
)

logger = logging.getLogger(__name__)


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
        Build PHI patterns from imported definitions

        Returns:
            List of PHIPattern objects
        """
        return [
            PHIPattern(
                pattern=pattern_str,
                category=category,
                risk_level=risk_level,
                description=description
            )
            for pattern_str, category, risk_level, description in PHI_PATTERN_DEFINITIONS
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
                if get_risk_priority(phi_pattern.risk_level) > get_risk_priority(max_risk):
                    max_risk = phi_pattern.risk_level

        # Generate warning message
        warning = None
        if detected:
            warning = self._generate_warning(max_risk)

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

                if get_risk_priority(result.risk_level) > get_risk_priority(max_risk):
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

    def _generate_warning(self, risk_level: PHIRiskLevel) -> str:
        """
        Generate warning message for detected PHI

        Args:
            risk_level: Maximum risk level

        Returns:
            Warning message string
        """
        if risk_level == PHIRiskLevel.HIGH:
            return WARNING_FIELD_HIGH
        elif risk_level == PHIRiskLevel.MEDIUM:
            return WARNING_FIELD_MEDIUM
        else:
            return WARNING_FIELD_LOW

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
        return get_all_categories()

    def get_compliance_guidelines(self) -> Dict[str, str]:
        """
        Get HIPAA compliance guidelines

        Returns:
            Dictionary of guidelines by topic
        """
        return HIPAA_COMPLIANCE_GUIDELINES


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
