"""
Permission Layer Package

Interactive permission system for Jarvis command execution:
- User-controlled execution with yes/no/always/never options
- Risk assessment for commands
- Session and permanent rule management
"""

from api.permission_layer.layer import (
    PermissionResponse,
    RiskLevel,
    PermissionRequest,
    PermissionRule,
    PermissionLayer,
    PermissionSystem,
    test_permission_layer,
)
from api.permission_layer.risk import (
    # Risk pattern constants
    CRITICAL_RISK_PATTERNS,
    HIGH_RISK_PATTERNS,
    MEDIUM_RISK_PATTERNS,
    LOW_RISK_PATTERNS,
    # Highlight/explanation constants
    DANGEROUS_TERMS,
    COMMAND_EXPLANATIONS,
    FLAG_EXPLANATIONS,
    # Command type constants
    FILE_OPERATION_COMMANDS,
    PACKAGE_MANAGER_COMMANDS,
    # Pure functions
    assess_risk_level,
    matches_pattern,
    highlight_dangerous_terms,
    create_similar_pattern,
    get_command_explanation,
    get_flag_explanation,
    extract_command_parts,
)

__all__ = [
    # Layer classes
    "PermissionResponse",
    "RiskLevel",
    "PermissionRequest",
    "PermissionRule",
    "PermissionLayer",
    "PermissionSystem",
    "test_permission_layer",
    # Risk pattern constants
    "CRITICAL_RISK_PATTERNS",
    "HIGH_RISK_PATTERNS",
    "MEDIUM_RISK_PATTERNS",
    "LOW_RISK_PATTERNS",
    # Highlight/explanation constants
    "DANGEROUS_TERMS",
    "COMMAND_EXPLANATIONS",
    "FLAG_EXPLANATIONS",
    # Command type constants
    "FILE_OPERATION_COMMANDS",
    "PACKAGE_MANAGER_COMMANDS",
    # Pure functions
    "assess_risk_level",
    "matches_pattern",
    "highlight_dangerous_terms",
    "create_similar_pattern",
    "get_command_explanation",
    "get_flag_explanation",
    "extract_command_parts",
]
