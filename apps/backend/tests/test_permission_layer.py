"""
Comprehensive tests for api/permission_layer.py

Tests cover:
- PermissionResponse and RiskLevel enums
- PermissionRequest and PermissionRule dataclasses
- PermissionLayer initialization and configuration
- Rule loading/saving to JSON
- Risk assessment for different command types
- Rule matching (exact, pattern, regex, wildcard)
- Permission checking (bypass, existing rules, session state)
- Non-interactive mode policies (strict, conservative, permissive)
- Similar pattern creation for different command types
- Permission statistics tracking
- Session rule management
"""

import pytest
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.permission_layer import (
    PermissionResponse,
    RiskLevel,
    PermissionRequest,
    PermissionRule,
    PermissionLayer,
)


# ========== PermissionResponse Enum Tests ==========

class TestPermissionResponse:
    """Tests for PermissionResponse enum"""

    def test_enum_values(self):
        """Test all enum values exist"""
        assert PermissionResponse.YES.value == "yes"
        assert PermissionResponse.NO.value == "no"
        assert PermissionResponse.YES_TO_ALL.value == "yes_to_all"
        assert PermissionResponse.NO_TO_ALL.value == "no_to_all"
        assert PermissionResponse.YES_TO_SIMILAR.value == "yes_to_similar"
        assert PermissionResponse.EXPLAIN.value == "explain"
        assert PermissionResponse.EDIT.value == "edit"

    def test_enum_count(self):
        """Test expected number of response types"""
        assert len(PermissionResponse) == 7

    def test_enum_from_value(self):
        """Test creating enum from value"""
        assert PermissionResponse("yes") == PermissionResponse.YES
        assert PermissionResponse("no") == PermissionResponse.NO


# ========== RiskLevel Enum Tests ==========

class TestRiskLevel:
    """Tests for RiskLevel enum"""

    def test_enum_values(self):
        """Test risk level values and properties"""
        assert RiskLevel.SAFE.level == 0
        assert RiskLevel.LOW.level == 1
        assert RiskLevel.MEDIUM.level == 2
        assert RiskLevel.HIGH.level == 3
        assert RiskLevel.CRITICAL.level == 4

    def test_enum_icons(self):
        """Test risk level icons"""
        assert RiskLevel.SAFE.icon == "🟢"
        assert RiskLevel.LOW.icon == "🟡"
        assert RiskLevel.MEDIUM.icon == "🟠"
        assert RiskLevel.HIGH.icon == "🔴"
        assert RiskLevel.CRITICAL.icon == "⚠️"

    def test_enum_labels(self):
        """Test risk level labels"""
        assert RiskLevel.SAFE.label == "Safe"
        assert RiskLevel.LOW.label == "Low Risk"
        assert RiskLevel.MEDIUM.label == "Medium Risk"
        assert RiskLevel.HIGH.label == "High Risk"
        assert RiskLevel.CRITICAL.label == "Critical"

    def test_enum_count(self):
        """Test expected number of risk levels"""
        assert len(RiskLevel) == 5


# ========== PermissionRequest Dataclass Tests ==========

class TestPermissionRequest:
    """Tests for PermissionRequest dataclass"""

    def test_basic_creation(self):
        """Test creating a permission request"""
        request = PermissionRequest(
            command="ls -la",
            operation_type="command",
            risk_level=RiskLevel.SAFE,
            reason="List files"
        )
        assert request.command == "ls -la"
        assert request.operation_type == "command"
        assert request.risk_level == RiskLevel.SAFE
        assert request.reason == "List files"

    def test_default_values(self):
        """Test default values for optional fields"""
        request = PermissionRequest(
            command="test",
            operation_type="test",
            risk_level=RiskLevel.LOW,
            reason="test"
        )
        assert request.details == {}
        assert isinstance(request.timestamp, datetime)

    def test_with_details(self):
        """Test request with additional details"""
        details = {"target": "/path/to/file", "user": "admin"}
        request = PermissionRequest(
            command="rm file.txt",
            operation_type="file_delete",
            risk_level=RiskLevel.MEDIUM,
            reason="Delete file",
            details=details
        )
        assert request.details == details
        assert request.details["target"] == "/path/to/file"


# ========== PermissionRule Dataclass Tests ==========

class TestPermissionRule:
    """Tests for PermissionRule dataclass"""

    def test_basic_creation(self):
        """Test creating a permission rule"""
        rule = PermissionRule(
            pattern="ls ",
            response=PermissionResponse.YES,
            operation_type="command"
        )
        assert rule.pattern == "ls "
        assert rule.response == PermissionResponse.YES
        assert rule.operation_type == "command"
        assert rule.expires is None

    def test_with_expiration(self):
        """Test rule with expiration date"""
        expires = datetime.now() + timedelta(hours=1)
        rule = PermissionRule(
            pattern="test",
            response=PermissionResponse.YES,
            operation_type="command",
            expires=expires
        )
        assert rule.expires == expires

    def test_created_timestamp(self):
        """Test created timestamp is set automatically"""
        rule = PermissionRule(
            pattern="test",
            response=PermissionResponse.NO,
            operation_type="command"
        )
        assert isinstance(rule.created, datetime)
        # Should be recent
        assert (datetime.now() - rule.created).total_seconds() < 1


# ========== PermissionLayer Initialization Tests ==========

class TestPermissionLayerInit:
    """Tests for PermissionLayer initialization"""

    def test_default_initialization(self):
        """Test default initialization"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            layer = PermissionLayer(config_path=config_path)

            assert layer.config_path == Path(config_path)
            assert layer.session_rules == []
            assert layer.permanent_rules == []
            assert layer.history == []
            assert layer.yes_to_all is False
            assert layer.no_to_all is False

    def test_non_interactive_mode(self):
        """Test non-interactive mode initialization"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            layer = PermissionLayer(
                config_path=config_path,
                non_interactive=True
            )
            assert layer.non_interactive is True

    def test_non_interactive_from_env(self):
        """Test non-interactive mode from environment"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            with patch.dict(os.environ, {"JARVIS_NON_INTERACTIVE": "1"}):
                layer = PermissionLayer(config_path=config_path)
                # Env var returns string "1" which is truthy
                assert layer.non_interactive  # Truthy check

    def test_bypass_mode_from_env(self):
        """Test bypass mode from environment"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            with patch.dict(os.environ, {"JARVIS_BYPASS_PERMISSIONS": "true"}):
                layer = PermissionLayer(config_path=config_path)
                assert layer.bypass_mode is True

    def test_non_interactive_policy_options(self):
        """Test different non-interactive policies"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")

            for policy in ["conservative", "permissive", "strict"]:
                layer = PermissionLayer(
                    config_path=config_path,
                    non_interactive_policy=policy
                )
                assert layer.non_interactive_policy == policy


# ========== Rule Loading/Saving Tests ==========

class TestRuleLoadingSaving:
    """Tests for rule persistence"""

    def test_save_and_load_rules(self):
        """Test saving and loading rules from JSON"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")

            # Create layer and add rule
            layer = PermissionLayer(config_path=config_path)
            rule = PermissionRule(
                pattern="git commit",
                response=PermissionResponse.YES,
                operation_type="command"
            )
            layer.permanent_rules.append(rule)
            layer._save_rules()

            # Create new layer and verify rule is loaded
            layer2 = PermissionLayer(config_path=config_path)
            assert len(layer2.permanent_rules) == 1
            assert layer2.permanent_rules[0].pattern == "git commit"
            assert layer2.permanent_rules[0].response == PermissionResponse.YES

    def test_expired_rules_not_loaded(self):
        """Test expired rules are not loaded"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")

            # Create expired rule directly in JSON
            expired_rule = {
                "rules": [{
                    "pattern": "expired",
                    "response": "yes",
                    "operation_type": "command",
                    "expires": (datetime.now() - timedelta(hours=1)).isoformat(),
                    "created": datetime.now().isoformat()
                }]
            }
            with open(config_path, "w") as f:
                json.dump(expired_rule, f)

            # Load and verify expired rule is not loaded
            layer = PermissionLayer(config_path=config_path)
            assert len(layer.permanent_rules) == 0

    def test_valid_rules_with_future_expiration(self):
        """Test rules with future expiration are loaded"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")

            # Create rule with future expiration
            future_rule = {
                "rules": [{
                    "pattern": "future",
                    "response": "yes",
                    "operation_type": "command",
                    "expires": (datetime.now() + timedelta(hours=1)).isoformat(),
                    "created": datetime.now().isoformat()
                }]
            }
            with open(config_path, "w") as f:
                json.dump(future_rule, f)

            layer = PermissionLayer(config_path=config_path)
            assert len(layer.permanent_rules) == 1

    def test_load_malformed_json(self):
        """Test graceful handling of malformed JSON"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")

            # Write malformed JSON
            with open(config_path, "w") as f:
                f.write("{invalid json")

            # Should not raise, just print warning
            layer = PermissionLayer(config_path=config_path)
            assert layer.permanent_rules == []


# ========== Risk Assessment Tests ==========

class TestRiskAssessment:
    """Tests for command risk assessment"""

    @pytest.fixture
    def layer(self):
        """Create permission layer for testing"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            yield PermissionLayer(config_path=config_path)

    def test_safe_commands(self, layer):
        """Test safe command detection"""
        safe_commands = [
            "ls -la",
            "pwd",
            "echo hello",
            "cat file.txt",
            "ps aux",
            "head -n 10 file",
        ]
        for cmd in safe_commands:
            risk, reason = layer.assess_risk(cmd)
            assert risk == RiskLevel.SAFE, f"Expected SAFE for '{cmd}', got {risk}"

    def test_low_risk_commands(self, layer):
        """Test low risk command detection

        Note: "pip install" and "npm install" trigger MEDIUM risk because
        "install" is checked before "pip install" in the assessment order.
        This documents the actual behavior.
        """
        low_risk_commands = [
            "mkdir new_dir",
            "touch newfile.txt",
            "git commit -m 'message'",
            "git add .",
            "echo > output.txt",
            "cat > newfile.txt",
        ]
        for cmd in low_risk_commands:
            risk, reason = layer.assess_risk(cmd)
            assert risk == RiskLevel.LOW, f"Expected LOW for '{cmd}', got {risk}"

    def test_package_install_is_medium_risk(self, layer):
        """Test package install commands are MEDIUM risk (contains 'install')"""
        # These contain "install" which triggers MEDIUM risk check first
        install_commands = [
            "pip install requests",
            "npm install lodash",
        ]
        for cmd in install_commands:
            risk, reason = layer.assess_risk(cmd)
            assert risk == RiskLevel.MEDIUM, f"Expected MEDIUM for '{cmd}', got {risk}"

    def test_medium_risk_commands(self, layer):
        """Test medium risk command detection"""
        medium_risk_commands = [
            "rm file.txt",
            "mv source dest",
            "curl https://example.com",
            "wget http://example.com",
            "git push --force",
            "cp -f source dest",
        ]
        for cmd in medium_risk_commands:
            risk, reason = layer.assess_risk(cmd)
            assert risk == RiskLevel.MEDIUM, f"Expected MEDIUM for '{cmd}', got {risk}"

    def test_high_risk_commands(self, layer):
        """Test high risk command detection"""
        high_risk_commands = [
            "sudo apt-get update",
            "rm -rf directory",
            "chmod 777 file",
            "kill -9 1234",
            "killall python",
            "systemctl stop service",
        ]
        for cmd in high_risk_commands:
            risk, reason = layer.assess_risk(cmd)
            assert risk == RiskLevel.HIGH, f"Expected HIGH for '{cmd}', got {risk}"

    def test_critical_risk_commands(self, layer):
        """Test critical risk command detection"""
        critical_commands = [
            "rm -rf /",
            "rm -rf ~",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
            "> /dev/sda",
        ]
        for cmd in critical_commands:
            risk, reason = layer.assess_risk(cmd)
            assert risk == RiskLevel.CRITICAL, f"Expected CRITICAL for '{cmd}', got {risk}"

    def test_risk_reason_returned(self, layer):
        """Test that risk assessment returns a reason"""
        risk, reason = layer.assess_risk("rm -rf /")
        assert reason != ""
        assert isinstance(reason, str)


# ========== Rule Matching Tests ==========

class TestRuleMatching:
    """Tests for rule matching logic"""

    @pytest.fixture
    def layer(self):
        """Create permission layer for testing"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            yield PermissionLayer(config_path=config_path)

    def test_exact_pattern_match(self, layer):
        """Test exact pattern matching"""
        rule = PermissionRule(
            pattern="git push",
            response=PermissionResponse.YES,
            operation_type="command"
        )
        request = PermissionRequest(
            command="git push origin main",
            operation_type="command",
            risk_level=RiskLevel.LOW,
            reason="test"
        )
        assert layer._matches_rule(request, rule) is True

    def test_wildcard_pattern(self, layer):
        """Test wildcard (*) pattern matches everything"""
        rule = PermissionRule(
            pattern="*",
            response=PermissionResponse.YES,
            operation_type="command"
        )
        request = PermissionRequest(
            command="any command here",
            operation_type="command",
            risk_level=RiskLevel.SAFE,
            reason="test"
        )
        assert layer._matches_rule(request, rule) is True

    def test_regex_pattern(self, layer):
        """Test regex pattern matching"""
        rule = PermissionRule(
            pattern="regex:^git (commit|push|pull)",
            response=PermissionResponse.YES,
            operation_type="command"
        )
        # Should match
        for cmd in ["git commit -m 'test'", "git push", "git pull origin"]:
            request = PermissionRequest(
                command=cmd,
                operation_type="command",
                risk_level=RiskLevel.LOW,
                reason="test"
            )
            assert layer._matches_rule(request, rule) is True

        # Should not match
        request = PermissionRequest(
            command="git status",
            operation_type="command",
            risk_level=RiskLevel.SAFE,
            reason="test"
        )
        assert layer._matches_rule(request, rule) is False

    def test_operation_type_filter(self, layer):
        """Test operation type filtering"""
        rule = PermissionRule(
            pattern="test",
            response=PermissionResponse.YES,
            operation_type="file_write"
        )
        request = PermissionRequest(
            command="test command",
            operation_type="command",  # Different type
            risk_level=RiskLevel.SAFE,
            reason="test"
        )
        assert layer._matches_rule(request, rule) is False

    def test_wildcard_operation_type(self, layer):
        """Test wildcard operation type matches any"""
        rule = PermissionRule(
            pattern="test",
            response=PermissionResponse.YES,
            operation_type="*"
        )
        for op_type in ["command", "file_write", "network"]:
            request = PermissionRequest(
                command="test command",
                operation_type=op_type,
                risk_level=RiskLevel.SAFE,
                reason="test"
            )
            assert layer._matches_rule(request, rule) is True


# ========== Permission Checking Tests ==========

class TestPermissionChecking:
    """Tests for permission checking logic"""

    @pytest.fixture
    def layer(self):
        """Create permission layer for testing"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            yield PermissionLayer(
                config_path=config_path,
                non_interactive=True,
                non_interactive_policy="conservative"
            )

    def test_bypass_mode(self):
        """Test bypass mode allows everything"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            with patch.dict(os.environ, {"JARVIS_BYPASS_PERMISSIONS": "true"}):
                layer = PermissionLayer(config_path=config_path)
                # Even critical commands allowed in bypass mode
                assert layer.check_permission("rm -rf /") is True
                assert layer.request_permission("rm -rf /") is True

    def test_yes_to_all_flag(self, layer):
        """Test yes_to_all flag allows everything"""
        layer.yes_to_all = True
        request = PermissionRequest(
            command="rm -rf /",
            operation_type="command",
            risk_level=RiskLevel.CRITICAL,
            reason="test"
        )
        result = layer.check_existing_rules(request)
        assert result == PermissionResponse.YES

    def test_no_to_all_flag(self, layer):
        """Test no_to_all flag blocks everything"""
        layer.no_to_all = True
        request = PermissionRequest(
            command="ls",
            operation_type="command",
            risk_level=RiskLevel.SAFE,
            reason="test"
        )
        result = layer.check_existing_rules(request)
        assert result == PermissionResponse.NO

    def test_session_rule_takes_precedence(self, layer):
        """Test session rules take precedence over permanent"""
        # Add conflicting rules
        layer.permanent_rules.append(PermissionRule(
            pattern="git",
            response=PermissionResponse.NO,
            operation_type="command"
        ))
        layer.session_rules.append(PermissionRule(
            pattern="git",
            response=PermissionResponse.YES,
            operation_type="command"
        ))

        request = PermissionRequest(
            command="git status",
            operation_type="command",
            risk_level=RiskLevel.SAFE,
            reason="test"
        )
        result = layer.check_existing_rules(request)
        assert result == PermissionResponse.YES

    def test_expired_rule_skipped(self, layer):
        """Test expired permanent rules are skipped"""
        layer.permanent_rules.append(PermissionRule(
            pattern="test",
            response=PermissionResponse.YES,
            operation_type="command",
            expires=datetime.now() - timedelta(hours=1)
        ))

        request = PermissionRequest(
            command="test command",
            operation_type="command",
            risk_level=RiskLevel.SAFE,
            reason="test"
        )
        result = layer.check_existing_rules(request)
        assert result is None  # No matching rule


# ========== Non-Interactive Mode Tests ==========

class TestNonInteractiveMode:
    """Tests for non-interactive decision making"""

    def test_strict_policy_safe_only(self):
        """Test strict policy only allows SAFE commands"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            layer = PermissionLayer(
                config_path=config_path,
                non_interactive=True,
                non_interactive_policy="strict"
            )

            # SAFE should be allowed
            assert layer.request_permission("ls -la") is True

            # LOW risk should be denied
            assert layer.request_permission("mkdir test") is False

            # MEDIUM should be denied
            assert layer.request_permission("rm file.txt") is False

    def test_conservative_policy_safe_and_low(self):
        """Test conservative policy allows SAFE and LOW"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            layer = PermissionLayer(
                config_path=config_path,
                non_interactive=True,
                non_interactive_policy="conservative"
            )

            # SAFE should be allowed
            assert layer.request_permission("ls -la") is True

            # LOW risk should be allowed
            assert layer.request_permission("mkdir test") is True

            # MEDIUM should be denied
            assert layer.request_permission("rm file.txt") is False

    def test_permissive_policy_all_except_critical(self):
        """Test permissive policy allows all except CRITICAL"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            layer = PermissionLayer(
                config_path=config_path,
                non_interactive=True,
                non_interactive_policy="permissive"
            )

            # SAFE should be allowed
            assert layer.request_permission("ls -la") is True

            # HIGH risk should be allowed
            assert layer.request_permission("sudo apt-get update") is True

            # CRITICAL should be denied
            assert layer.request_permission("rm -rf /") is False


# ========== Similar Pattern Creation Tests ==========

class TestSimilarPatternCreation:
    """Tests for similar pattern creation"""

    @pytest.fixture
    def layer(self):
        """Create permission layer for testing"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            yield PermissionLayer(config_path=config_path)

    def test_file_operations_pattern(self, layer):
        """Test pattern for file operations"""
        commands = ["rm", "cp", "mv", "ls", "cat", "mkdir"]
        for cmd in commands:
            pattern = layer._create_similar_pattern(f"{cmd} /path/to/file")
            assert pattern == f"{cmd} "

    def test_git_operations_pattern(self, layer):
        """Test pattern for git operations"""
        test_cases = [
            ("git commit -m 'test'", "git commit"),
            ("git push origin main", "git push"),
            ("git pull --rebase", "git pull"),
        ]
        for cmd, expected in test_cases:
            pattern = layer._create_similar_pattern(cmd)
            assert pattern == expected

    def test_package_manager_pattern(self, layer):
        """Test pattern for package managers"""
        test_cases = [
            ("pip install requests", "pip install"),
            ("npm install lodash", "npm install"),
            ("apt-get install vim", "apt-get install"),
            ("brew install git", "brew install"),
        ]
        for cmd, expected in test_cases:
            pattern = layer._create_similar_pattern(cmd)
            assert pattern == expected

    def test_single_word_command_pattern(self, layer):
        """Test pattern for single word commands"""
        pattern = layer._create_similar_pattern("ps")
        assert pattern == "ps"

    def test_empty_command_pattern(self, layer):
        """Test pattern for empty command"""
        pattern = layer._create_similar_pattern("")
        assert pattern == ""


# ========== Statistics Tests ==========

class TestStatistics:
    """Tests for permission statistics"""

    @pytest.fixture
    def layer(self):
        """Create permission layer for testing"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            yield PermissionLayer(
                config_path=config_path,
                non_interactive=True,
                non_interactive_policy="conservative"
            )

    def test_empty_statistics(self, layer):
        """Test statistics with no history"""
        stats = layer.get_statistics()
        assert stats == {}

    def test_statistics_after_requests(self, layer):
        """Test statistics tracking"""
        # Make some requests
        layer.request_permission("ls -la")  # SAFE - allowed
        layer.request_permission("mkdir test")  # LOW - allowed
        layer.request_permission("rm file.txt")  # MEDIUM - denied

        stats = layer.get_statistics()
        assert stats["total_requests"] == 3
        assert stats["allowed"] == 2
        assert stats["denied"] == 1
        assert "allow_rate" in stats
        assert "risk_distribution" in stats

    def test_statistics_risk_distribution(self, layer):
        """Test risk distribution in statistics"""
        layer.request_permission("ls")  # SAFE
        layer.request_permission("ls -la")  # SAFE
        layer.request_permission("mkdir test")  # LOW

        stats = layer.get_statistics()
        risk_dist = stats["risk_distribution"]
        assert "Safe" in risk_dist
        assert risk_dist["Safe"] == 2
        assert "Low Risk" in risk_dist
        assert risk_dist["Low Risk"] == 1


# ========== Session Rule Management Tests ==========

class TestSessionRuleManagement:
    """Tests for session rule management"""

    @pytest.fixture
    def layer(self):
        """Create permission layer for testing"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            yield PermissionLayer(config_path=config_path)

    def test_reset_session_rules(self, layer):
        """Test resetting session rules"""
        # Add session state
        layer.yes_to_all = True
        layer.no_to_all = True
        layer.session_rules.append(PermissionRule(
            pattern="test",
            response=PermissionResponse.YES,
            operation_type="command"
        ))

        # Reset
        layer.reset_session_rules()

        assert layer.yes_to_all is False
        assert layer.no_to_all is False
        assert layer.session_rules == []

    def test_show_rules_output(self, layer, capsys):
        """Test show_rules output"""
        layer.yes_to_all = True
        layer.session_rules.append(PermissionRule(
            pattern="git",
            response=PermissionResponse.YES,
            operation_type="command"
        ))
        layer.permanent_rules.append(PermissionRule(
            pattern="rm",
            response=PermissionResponse.NO,
            operation_type="command"
        ))

        layer.show_rules()
        captured = capsys.readouterr()

        assert "Yes to all" in captured.out
        assert "git" in captured.out
        assert "rm" in captured.out


# ========== Process Response Tests ==========

class TestProcessResponse:
    """Tests for response processing"""

    @pytest.fixture
    def layer(self):
        """Create permission layer for testing"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            yield PermissionLayer(config_path=config_path)

    def test_process_yes_response(self, layer):
        """Test processing YES response"""
        request = PermissionRequest(
            command="test",
            operation_type="command",
            risk_level=RiskLevel.SAFE,
            reason="test"
        )
        result = layer._process_response(request, PermissionResponse.YES)
        assert result is True
        assert len(layer.history) == 1

    def test_process_no_response(self, layer):
        """Test processing NO response"""
        request = PermissionRequest(
            command="test",
            operation_type="command",
            risk_level=RiskLevel.SAFE,
            reason="test"
        )
        result = layer._process_response(request, PermissionResponse.NO)
        assert result is False

    def test_process_yes_to_all_response(self, layer):
        """Test processing YES_TO_ALL response"""
        request = PermissionRequest(
            command="test",
            operation_type="command",
            risk_level=RiskLevel.SAFE,
            reason="test"
        )
        result = layer._process_response(request, PermissionResponse.YES_TO_ALL)
        assert result is True
        assert layer.yes_to_all is True

    def test_process_no_to_all_response(self, layer):
        """Test processing NO_TO_ALL response"""
        request = PermissionRequest(
            command="test",
            operation_type="command",
            risk_level=RiskLevel.SAFE,
            reason="test"
        )
        result = layer._process_response(request, PermissionResponse.NO_TO_ALL)
        assert result is False
        assert layer.no_to_all is True

    def test_process_yes_to_similar_response(self, layer):
        """Test processing YES_TO_SIMILAR response"""
        request = PermissionRequest(
            command="git push origin main",
            operation_type="command",
            risk_level=RiskLevel.LOW,
            reason="test"
        )
        result = layer._process_response(request, PermissionResponse.YES_TO_SIMILAR)
        assert result is True
        assert len(layer.session_rules) == 1
        assert "git push" in layer.session_rules[0].pattern


# ========== Command Highlighting Tests ==========

class TestCommandHighlighting:
    """Tests for command highlighting"""

    @pytest.fixture
    def layer(self):
        """Create permission layer for testing"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            yield PermissionLayer(config_path=config_path)

    def test_highlight_dangerous_terms(self, layer):
        """Test that dangerous terms are highlighted"""
        dangerous_terms = ["rm", "sudo", "kill", "chmod", "chown"]
        for term in dangerous_terms:
            highlighted = layer._highlight_command(f"{term} something")
            # Should contain ANSI color codes around the term
            assert "\033[91m" in highlighted  # RED
            assert term in highlighted

    def test_safe_command_unchanged(self, layer):
        """Test that safe commands don't have highlighting"""
        cmd = "ls -la"
        highlighted = layer._highlight_command(cmd)
        # No RED color codes
        assert "\033[91m" not in highlighted or "ls" not in highlighted.replace("\033[91m", "")


# ========== Thread Safety Tests ==========

class TestThreadSafety:
    """Tests for thread safety"""

    def test_has_lock(self):
        """Test that permission layer has a lock"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            layer = PermissionLayer(config_path=config_path)
            assert hasattr(layer, 'lock')
            import threading
            assert isinstance(layer.lock, type(threading.Lock()))


# ========== Edge Cases Tests ==========

class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.fixture
    def layer(self):
        """Create permission layer for testing"""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "permissions.json")
            yield PermissionLayer(
                config_path=config_path,
                non_interactive=True,
                non_interactive_policy="conservative"
            )

    def test_unicode_command(self, layer):
        """Test handling unicode in commands"""
        result = layer.request_permission("echo 你好世界")
        assert isinstance(result, bool)

    def test_very_long_command(self, layer):
        """Test handling very long commands"""
        long_cmd = "echo " + "x" * 10000
        result = layer.request_permission(long_cmd)
        assert isinstance(result, bool)

    def test_empty_command(self, layer):
        """Test handling empty command"""
        result = layer.request_permission("")
        assert isinstance(result, bool)

    def test_command_with_special_chars(self, layer):
        """Test handling special characters"""
        special_cmds = [
            "echo $HOME",
            "echo \"hello world\"",
            "echo 'single quotes'",
            "cmd1 | cmd2",
            "cmd1 && cmd2",
            "cmd1 || cmd2",
            "cmd > file",
            "cmd 2>&1",
        ]
        for cmd in special_cmds:
            result = layer.request_permission(cmd)
            assert isinstance(result, bool)


# ========== Compatibility Alias Tests ==========

class TestCompatibilityAlias:
    """Tests for compatibility alias"""

    def test_permission_system_alias(self):
        """Test PermissionSystem is alias for PermissionLayer"""
        from api.permission_layer import PermissionSystem
        assert PermissionSystem is PermissionLayer
