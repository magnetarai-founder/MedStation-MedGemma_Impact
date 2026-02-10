"""
Comprehensive tests for api/disclaimers.py

Tests the legal disclaimers and compliance text service.

Coverage targets:
- DisclaimerType: All enum values
- DisclaimerService: All static methods for retrieving disclaimer text
"""

import pytest
from typing import Dict

from api.disclaimers import DisclaimerType, DisclaimerService


# ========== DisclaimerType Enum Tests ==========

class TestDisclaimerType:
    """Tests for DisclaimerType enum"""

    def test_medical_advice_type(self):
        """Test MEDICAL_ADVICE enum value"""
        assert DisclaimerType.MEDICAL_ADVICE.value == "medical_advice"

    def test_ai_content_type(self):
        """Test AI_CONTENT enum value"""
        assert DisclaimerType.AI_CONTENT.value == "ai_content"

    def test_liability_type(self):
        """Test LIABILITY enum value"""
        assert DisclaimerType.LIABILITY.value == "liability"

    def test_export_control_type(self):
        """Test EXPORT_CONTROL enum value"""
        assert DisclaimerType.EXPORT_CONTROL.value == "export_control"

    def test_hipaa_compliance_type(self):
        """Test HIPAA_COMPLIANCE enum value"""
        assert DisclaimerType.HIPAA_COMPLIANCE.value == "hipaa_compliance"

    def test_data_privacy_type(self):
        """Test DATA_PRIVACY enum value"""
        assert DisclaimerType.DATA_PRIVACY.value == "data_privacy"

    def test_enum_count(self):
        """Test total number of disclaimer types"""
        assert len(DisclaimerType) == 6

    def test_enum_is_str_subclass(self):
        """Test DisclaimerType inherits from str"""
        # This allows direct comparison with strings
        assert isinstance(DisclaimerType.MEDICAL_ADVICE, str)
        assert DisclaimerType.MEDICAL_ADVICE == "medical_advice"


# ========== Medical Disclaimer Tests ==========

class TestMedicalDisclaimer:
    """Tests for medical disclaimer methods"""

    def test_get_medical_disclaimer_short_returns_string(self):
        """Test short disclaimer returns non-empty string"""
        result = DisclaimerService.get_medical_disclaimer_short()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_medical_disclaimer_short_contains_warning(self):
        """Test short disclaimer contains warning indicator"""
        result = DisclaimerService.get_medical_disclaimer_short()

        assert "⚠️" in result or "Not medical advice" in result

    def test_get_medical_disclaimer_short_mentions_professional(self):
        """Test short disclaimer mentions consulting professionals"""
        result = DisclaimerService.get_medical_disclaimer_short()

        assert "professional" in result.lower()

    def test_get_medical_disclaimer_full_returns_string(self):
        """Test full disclaimer returns non-empty string"""
        result = DisclaimerService.get_medical_disclaimer_full()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_medical_disclaimer_full_longer_than_short(self):
        """Test full disclaimer is longer than short"""
        short = DisclaimerService.get_medical_disclaimer_short()
        full = DisclaimerService.get_medical_disclaimer_full()

        assert len(full) > len(short)

    def test_get_medical_disclaimer_full_contains_key_sections(self):
        """Test full disclaimer contains expected sections"""
        result = DisclaimerService.get_medical_disclaimer_full()

        assert "MEDICAL DISCLAIMER" in result
        assert "EMERGENCY DISCLAIMER" in result
        assert "PROFESSIONAL LICENSING" in result

    def test_get_medical_disclaimer_full_fda_notice(self):
        """Test full disclaimer mentions FDA"""
        result = DisclaimerService.get_medical_disclaimer_full()

        assert "FDA" in result

    def test_get_medical_disclaimer_full_emergency_services(self):
        """Test full disclaimer mentions emergency services"""
        result = DisclaimerService.get_medical_disclaimer_full()

        assert "911" in result or "emergency" in result.lower()


# ========== AI Content Disclaimer Tests ==========

class TestAIContentDisclaimer:
    """Tests for AI content disclaimer"""

    def test_returns_string(self):
        """Test returns non-empty string"""
        result = DisclaimerService.get_ai_content_disclaimer()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_title(self):
        """Test contains AI content disclaimer title"""
        result = DisclaimerService.get_ai_content_disclaimer()

        assert "AI-GENERATED CONTENT" in result

    def test_mentions_large_language_models(self):
        """Test mentions LLMs"""
        result = DisclaimerService.get_ai_content_disclaimer()

        assert "language models" in result.lower()

    def test_mentions_accuracy(self):
        """Test mentions accuracy concerns"""
        result = DisclaimerService.get_ai_content_disclaimer()

        assert "accuracy" in result.lower()

    def test_mentions_user_responsibility(self):
        """Test mentions user responsibility"""
        result = DisclaimerService.get_ai_content_disclaimer()

        assert "responsible" in result.lower()

    def test_mentions_verification(self):
        """Test mentions verification requirement"""
        result = DisclaimerService.get_ai_content_disclaimer()

        assert "verify" in result.lower()

    def test_mentions_bias(self):
        """Test mentions potential biases"""
        result = DisclaimerService.get_ai_content_disclaimer()

        assert "bias" in result.lower()


# ========== Liability Disclaimer Tests ==========

class TestLiabilityDisclaimer:
    """Tests for liability disclaimer"""

    def test_returns_string(self):
        """Test returns non-empty string"""
        result = DisclaimerService.get_liability_disclaimer()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_title(self):
        """Test contains liability disclaimer title"""
        result = DisclaimerService.get_liability_disclaimer()

        assert "LIABILITY DISCLAIMER" in result

    def test_contains_as_is_clause(self):
        """Test contains AS IS clause"""
        result = DisclaimerService.get_liability_disclaimer()

        assert "AS IS" in result

    def test_mentions_warranties(self):
        """Test mentions warranties"""
        result = DisclaimerService.get_liability_disclaimer()

        assert "warrant" in result.lower()

    def test_contains_user_responsibility_section(self):
        """Test contains user responsibility section"""
        result = DisclaimerService.get_liability_disclaimer()

        assert "USER RESPONSIBILITY" in result

    def test_contains_prohibited_uses_section(self):
        """Test contains prohibited uses section"""
        result = DisclaimerService.get_liability_disclaimer()

        assert "PROHIBITED USES" in result

    def test_prohibits_life_critical(self):
        """Test prohibits life-critical uses without safeguards"""
        result = DisclaimerService.get_liability_disclaimer()

        assert "life-critical" in result.lower() or "Life-critical" in result


# ========== Export Control Notice Tests ==========

class TestExportControlNotice:
    """Tests for export control notice"""

    def test_returns_string(self):
        """Test returns non-empty string"""
        result = DisclaimerService.get_export_control_notice()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_title(self):
        """Test contains export control title"""
        result = DisclaimerService.get_export_control_notice()

        assert "EXPORT CONTROL" in result

    def test_mentions_encryption_types(self):
        """Test mentions encryption technologies"""
        result = DisclaimerService.get_export_control_notice()

        assert "AES-256" in result
        assert "TLS" in result

    def test_mentions_ear(self):
        """Test mentions Export Administration Regulations"""
        result = DisclaimerService.get_export_control_notice()

        assert "EAR" in result or "Export Administration Regulations" in result

    def test_mentions_wassenaar(self):
        """Test mentions Wassenaar Arrangement"""
        result = DisclaimerService.get_export_control_notice()

        assert "Wassenaar" in result

    def test_mentions_pbkdf2(self):
        """Test mentions PBKDF2 key derivation"""
        result = DisclaimerService.get_export_control_notice()

        assert "PBKDF2" in result

    def test_mentions_bis(self):
        """Test mentions Bureau of Industry and Security"""
        result = DisclaimerService.get_export_control_notice()

        assert "BIS" in result or "Bureau of Industry and Security" in result

    def test_contains_bis_url(self):
        """Test contains BIS website URL"""
        result = DisclaimerService.get_export_control_notice()

        assert "bis.doc.gov" in result


# ========== HIPAA Compliance Notice Tests ==========

class TestHIPAAComplianceNotice:
    """Tests for HIPAA compliance notice"""

    def test_returns_string(self):
        """Test returns non-empty string"""
        result = DisclaimerService.get_hipaa_compliance_notice()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_title(self):
        """Test contains HIPAA title"""
        result = DisclaimerService.get_hipaa_compliance_notice()

        assert "HIPAA" in result

    def test_mentions_phi(self):
        """Test mentions Protected Health Information"""
        result = DisclaimerService.get_hipaa_compliance_notice()

        assert "PHI" in result or "Protected Health Information" in result

    def test_contains_organizational_requirements(self):
        """Test contains organizational requirements section"""
        result = DisclaimerService.get_hipaa_compliance_notice()

        assert "ORGANIZATIONAL REQUIREMENTS" in result

    def test_contains_technical_safeguards(self):
        """Test contains technical safeguards section"""
        result = DisclaimerService.get_hipaa_compliance_notice()

        assert "TECHNICAL SAFEGUARDS" in result

    def test_mentions_encryption(self):
        """Test mentions encryption"""
        result = DisclaimerService.get_hipaa_compliance_notice()

        assert "encryption" in result.lower()

    def test_mentions_audit_logging(self):
        """Test mentions audit logging"""
        result = DisclaimerService.get_hipaa_compliance_notice()

        assert "audit" in result.lower()

    def test_mentions_baa(self):
        """Test mentions Business Associate Agreement"""
        result = DisclaimerService.get_hipaa_compliance_notice()

        assert "BAA" in result or "Business Associate" in result

    def test_no_guarantee_clause(self):
        """Test includes no guarantee of compliance"""
        result = DisclaimerService.get_hipaa_compliance_notice()

        assert "NO GUARANTEE" in result or "does not guarantee" in result.lower()


# ========== Data Privacy Notice Tests ==========

class TestDataPrivacyNotice:
    """Tests for data privacy notice"""

    def test_returns_string(self):
        """Test returns non-empty string"""
        result = DisclaimerService.get_data_privacy_notice()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_title(self):
        """Test contains data privacy title"""
        result = DisclaimerService.get_data_privacy_notice()

        assert "DATA PRIVACY" in result

    def test_mentions_local_first(self):
        """Test mentions local-first architecture"""
        result = DisclaimerService.get_data_privacy_notice()

        assert "LOCAL-FIRST" in result or "local-first" in result

    def test_mentions_no_data_collection(self):
        """Test emphasizes no data collection"""
        result = DisclaimerService.get_data_privacy_notice()

        assert "does not collect" in result.lower()

    def test_mentions_sqlite_encryption(self):
        """Test mentions SQLite database encryption"""
        result = DisclaimerService.get_data_privacy_notice()

        assert "SQLite" in result

    def test_mentions_secure_enclave(self):
        """Test mentions Secure Enclave"""
        result = DisclaimerService.get_data_privacy_notice()

        assert "Secure Enclave" in result

    def test_mentions_gdpr(self):
        """Test mentions GDPR compliance"""
        result = DisclaimerService.get_data_privacy_notice()

        assert "GDPR" in result

    def test_mentions_ccpa(self):
        """Test mentions CCPA"""
        result = DisclaimerService.get_data_privacy_notice()

        assert "CCPA" in result

    def test_mentions_third_party(self):
        """Test mentions third-party services"""
        result = DisclaimerService.get_data_privacy_notice()

        assert "third-party" in result.lower() or "third party" in result.lower()


# ========== Aggregate Methods Tests ==========

class TestAggregateMethods:
    """Tests for aggregate disclaimer methods"""

    def test_get_all_disclaimers_returns_dict(self):
        """Test get_all_disclaimers returns dictionary"""
        result = DisclaimerService.get_all_disclaimers()

        assert isinstance(result, dict)

    def test_get_all_disclaimers_contains_all_types(self):
        """Test all disclaimer types are present"""
        result = DisclaimerService.get_all_disclaimers()

        assert DisclaimerType.MEDICAL_ADVICE.value in result
        assert DisclaimerType.AI_CONTENT.value in result
        assert DisclaimerType.LIABILITY.value in result
        assert DisclaimerType.EXPORT_CONTROL.value in result
        assert DisclaimerType.HIPAA_COMPLIANCE.value in result
        assert DisclaimerType.DATA_PRIVACY.value in result

    def test_get_all_disclaimers_count(self):
        """Test all disclaimers dict has correct count"""
        result = DisclaimerService.get_all_disclaimers()

        assert len(result) == 6

    def test_get_all_disclaimers_values_are_strings(self):
        """Test all values in dict are strings"""
        result = DisclaimerService.get_all_disclaimers()

        for key, value in result.items():
            assert isinstance(value, str)
            assert len(value) > 0

    def test_get_chat_footer_text_returns_short_disclaimer(self):
        """Test chat footer returns short medical disclaimer"""
        result = DisclaimerService.get_chat_footer_text()
        expected = DisclaimerService.get_medical_disclaimer_short()

        assert result == expected

    def test_get_medical_template_banner_returns_string(self):
        """Test medical template banner returns non-empty string"""
        result = DisclaimerService.get_medical_template_banner()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_medical_template_banner_contains_warning(self):
        """Test medical template banner contains warning"""
        result = DisclaimerService.get_medical_template_banner()

        assert "⚠️" in result or "DISCLAIMER" in result

    def test_get_medical_template_banner_mentions_informational(self):
        """Test medical template banner mentions informational purposes"""
        result = DisclaimerService.get_medical_template_banner()

        assert "informational" in result.lower()


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    def test_all_disclaimers_match_individual_methods(self):
        """Test get_all_disclaimers values match individual method returns"""
        all_disclaimers = DisclaimerService.get_all_disclaimers()

        assert all_disclaimers[DisclaimerType.MEDICAL_ADVICE.value] == DisclaimerService.get_medical_disclaimer_full()
        assert all_disclaimers[DisclaimerType.AI_CONTENT.value] == DisclaimerService.get_ai_content_disclaimer()
        assert all_disclaimers[DisclaimerType.LIABILITY.value] == DisclaimerService.get_liability_disclaimer()
        assert all_disclaimers[DisclaimerType.EXPORT_CONTROL.value] == DisclaimerService.get_export_control_notice()
        assert all_disclaimers[DisclaimerType.HIPAA_COMPLIANCE.value] == DisclaimerService.get_hipaa_compliance_notice()
        assert all_disclaimers[DisclaimerType.DATA_PRIVACY.value] == DisclaimerService.get_data_privacy_notice()

    def test_enum_values_used_as_dict_keys(self):
        """Test enum values can be used as dictionary keys"""
        all_disclaimers = DisclaimerService.get_all_disclaimers()

        # Access using enum value (string)
        medical = all_disclaimers[DisclaimerType.MEDICAL_ADVICE.value]
        assert isinstance(medical, str)

        # Access using raw string (since enum is str subclass)
        medical2 = all_disclaimers["medical_advice"]
        assert medical == medical2

    def test_static_methods_are_callable(self):
        """Test all methods are static and callable"""
        methods = [
            DisclaimerService.get_medical_disclaimer_short,
            DisclaimerService.get_medical_disclaimer_full,
            DisclaimerService.get_ai_content_disclaimer,
            DisclaimerService.get_liability_disclaimer,
            DisclaimerService.get_export_control_notice,
            DisclaimerService.get_hipaa_compliance_notice,
            DisclaimerService.get_data_privacy_notice,
            DisclaimerService.get_all_disclaimers,
            DisclaimerService.get_chat_footer_text,
            DisclaimerService.get_medical_template_banner,
        ]

        for method in methods:
            result = method()
            assert result is not None


# ========== Edge Cases ==========

class TestEdgeCases:
    """Edge case tests"""

    def test_disclaimers_immutable_on_multiple_calls(self):
        """Test disclaimers return same content on multiple calls"""
        result1 = DisclaimerService.get_medical_disclaimer_full()
        result2 = DisclaimerService.get_medical_disclaimer_full()

        assert result1 == result2

    def test_all_disclaimers_returns_fresh_dict(self):
        """Test get_all_disclaimers returns new dict each call"""
        result1 = DisclaimerService.get_all_disclaimers()
        result2 = DisclaimerService.get_all_disclaimers()

        # Should be equal in content
        assert result1 == result2
        # Should be different objects (not shared reference)
        assert result1 is not result2

    def test_disclaimer_text_is_multiline(self):
        """Test full disclaimers contain newlines for formatting"""
        full = DisclaimerService.get_medical_disclaimer_full()

        assert "\n" in full

    def test_disclaimer_uses_consistent_product_name(self):
        """Test disclaimers consistently use MedStation"""
        disclaimers = [
            DisclaimerService.get_medical_disclaimer_full(),
            DisclaimerService.get_ai_content_disclaimer(),
            DisclaimerService.get_liability_disclaimer(),
            DisclaimerService.get_export_control_notice(),
            DisclaimerService.get_hipaa_compliance_notice(),
            DisclaimerService.get_data_privacy_notice(),
        ]

        for disclaimer in disclaimers:
            assert "MedStation" in disclaimer

    def test_disclaimer_bullet_points_consistent(self):
        """Test disclaimers use consistent bullet point format"""
        full = DisclaimerService.get_medical_disclaimer_full()

        # Uses • for bullet points
        assert "•" in full
