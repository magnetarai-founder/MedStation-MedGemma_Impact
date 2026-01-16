"""
Legal Disclaimers and Compliance Text

Provides standardized disclaimer text for:
- Medical advice disclaimers
- AI-generated content warnings
- Legal liability limitations
- Export control notices

These disclaimers are displayed in UI components (chat, forms, settings).

Module structure (P2 decomposition):
- disclaimer_content.py: DisclaimerType enum and text constants
- disclaimers.py: DisclaimerService class (this file)
"""

from typing import Dict

# Import from extracted module (P2 decomposition)
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


class DisclaimerService:
    """
    Service for managing legal disclaimers and compliance text
    """

    @staticmethod
    def get_medical_disclaimer_short() -> str:
        """
        Get short medical disclaimer for chat UI footer

        Returns:
            Short disclaimer text
        """
        return MEDICAL_DISCLAIMER_SHORT

    @staticmethod
    def get_medical_disclaimer_full() -> str:
        """
        Get full medical disclaimer for Settings → Legal page

        Returns:
            Full disclaimer text
        """
        return MEDICAL_DISCLAIMER_FULL

    @staticmethod
    def get_ai_content_disclaimer() -> str:
        """
        Get AI-generated content disclaimer

        Returns:
            AI content disclaimer text
        """
        return AI_CONTENT_DISCLAIMER

    @staticmethod
    def get_liability_disclaimer() -> str:
        """
        Get general liability disclaimer

        Returns:
            Liability disclaimer text
        """
        return LIABILITY_DISCLAIMER

    @staticmethod
    def get_export_control_notice() -> str:
        """
        Get export control notice for encryption

        Returns:
            Export control notice text
        """
        return EXPORT_CONTROL_NOTICE

    @staticmethod
    def get_hipaa_compliance_notice() -> str:
        """
        Get HIPAA compliance notice

        Returns:
            HIPAA compliance notice text
        """
        return HIPAA_COMPLIANCE_NOTICE

    @staticmethod
    def get_data_privacy_notice() -> str:
        """
        Get data privacy notice

        Returns:
            Data privacy notice text
        """
        return DATA_PRIVACY_NOTICE

    @staticmethod
    def get_all_disclaimers() -> Dict[str, str]:
        """
        Get all disclaimers as a dictionary

        Returns:
            Dictionary mapping disclaimer types to text
        """
        return {
            DisclaimerType.MEDICAL_ADVICE.value: MEDICAL_DISCLAIMER_FULL,
            DisclaimerType.AI_CONTENT.value: AI_CONTENT_DISCLAIMER,
            DisclaimerType.LIABILITY.value: LIABILITY_DISCLAIMER,
            DisclaimerType.EXPORT_CONTROL.value: EXPORT_CONTROL_NOTICE,
            DisclaimerType.HIPAA_COMPLIANCE.value: HIPAA_COMPLIANCE_NOTICE,
            DisclaimerType.DATA_PRIVACY.value: DATA_PRIVACY_NOTICE,
        }

    @staticmethod
    def get_chat_footer_text() -> str:
        """
        Get text for chat UI footer

        Returns:
            Chat footer disclaimer text
        """
        return MEDICAL_DISCLAIMER_SHORT

    @staticmethod
    def get_medical_template_banner() -> str:
        """
        Get banner text for medical workflow templates

        Returns:
            Medical template banner text
        """
        return MEDICAL_TEMPLATE_BANNER


# Re-exports for backwards compatibility (P2 decomposition)
__all__ = [
    # Service
    "DisclaimerService",
    # Re-exported from disclaimer_content
    "DisclaimerType",
]
