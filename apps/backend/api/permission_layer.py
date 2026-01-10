#!/usr/bin/env python3
"""
Interactive Permission Layer for Jarvis
User-controlled execution with yes/no/always/never options

Module structure (P2 decomposition):
- permission_layer_risk.py: Pure functions, risk patterns, static data
- permission_layer.py: Main PermissionLayer class (this file)
"""

import json
import os
import re
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import from extracted module (P2 decomposition)
from api.permission_layer_risk import (
    assess_risk_level,
    matches_pattern,
    highlight_dangerous_terms,
    create_similar_pattern,
    COMMAND_EXPLANATIONS,
    FLAG_EXPLANATIONS,
)

# ANSI colors for better visibility
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


class PermissionResponse(Enum):
    """User permission responses"""

    YES = "yes"
    NO = "no"
    YES_TO_ALL = "yes_to_all"
    NO_TO_ALL = "no_to_all"
    YES_TO_SIMILAR = "yes_to_similar"
    EXPLAIN = "explain"
    EDIT = "edit"


class RiskLevel(Enum):
    """Risk levels for operations"""

    SAFE = (0, "🟢", "Safe")
    LOW = (1, "🟡", "Low Risk")
    MEDIUM = (2, "🟠", "Medium Risk")
    HIGH = (3, "🔴", "High Risk")
    CRITICAL = (4, "⚠️", "Critical")

    def __init__(self, value, icon, label):
        self.level = value
        self.icon = icon
        self.label = label


@dataclass
class PermissionRequest:
    """A request for permission"""

    command: str
    operation_type: str
    risk_level: RiskLevel
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PermissionRule:
    """A saved permission rule"""

    pattern: str
    response: PermissionResponse
    operation_type: str
    expires: Optional[datetime] = None
    created: datetime = field(default_factory=datetime.now)


class PermissionLayer:
    """
    Interactive permission system that asks user before executing commands
    """

    def __init__(
        self,
        config_path: str = "~/.jarvis_permissions.json",
        non_interactive: bool = False,
        non_interactive_policy: str = "conservative",
    ):
        self.config_path = Path(config_path).expanduser()
        self.session_rules: List[PermissionRule] = []  # Rules for this session
        self.permanent_rules: List[PermissionRule] = []  # Saved rules
        self.history: List[Tuple[PermissionRequest, PermissionResponse]] = []
        self.yes_to_all = False
        self.no_to_all = False
        self.lock = threading.Lock()

        # Non-interactive mode settings
        self.non_interactive = non_interactive or os.environ.get("JARVIS_NON_INTERACTIVE", False)
        self.non_interactive_policy = (
            non_interactive_policy  # "conservative", "permissive", "strict"
        )

        # Bypass mode for testing (disables all permission checks)
        self.bypass_mode = os.environ.get("JARVIS_BYPASS_PERMISSIONS", "").lower() in (
            "1",
            "true",
            "yes",
        )

        # Load saved rules
        self._load_rules()

    def _load_rules(self) -> None:
        """Load saved permission rules"""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    data = json.load(f)
                    # Convert back to PermissionRule objects
                    for rule_data in data.get("rules", []):
                        rule = PermissionRule(
                            pattern=rule_data["pattern"],
                            response=PermissionResponse(rule_data["response"]),
                            operation_type=rule_data["operation_type"],
                            expires=(
                                datetime.fromisoformat(rule_data["expires"])
                                if rule_data.get("expires")
                                else None
                            ),
                            created=datetime.fromisoformat(
                                rule_data.get("created", datetime.now().isoformat())
                            ),
                        )
                        # Only load non-expired rules
                        if not rule.expires or rule.expires > datetime.now():
                            self.permanent_rules.append(rule)
            except Exception as e:
                print(f"{YELLOW}Could not load permission rules: {e}{RESET}")

    def _save_rules(self) -> None:
        """Save permission rules"""
        try:
            data = {
                "rules": [
                    {
                        "pattern": rule.pattern,
                        "response": rule.response.value,
                        "operation_type": rule.operation_type,
                        "expires": rule.expires.isoformat() if rule.expires else None,
                        "created": rule.created.isoformat(),
                    }
                    for rule in self.permanent_rules
                    if not rule.expires or rule.expires > datetime.now()
                ]
            }

            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"{YELLOW}Could not save permission rules: {e}{RESET}")

    def assess_risk(self, command: str, operation_type: str = "command") -> Tuple[RiskLevel, str]:
        """
        Assess the risk level of a command.

        Delegates to extracted pure function (P2 decomposition).
        """
        # Map risk level int to RiskLevel enum
        risk_level_map = {
            0: RiskLevel.SAFE,
            1: RiskLevel.LOW,
            2: RiskLevel.MEDIUM,
            3: RiskLevel.HIGH,
            4: RiskLevel.CRITICAL,
        }

        level_int, reason = assess_risk_level(command)
        return risk_level_map[level_int], reason

    def check_existing_rules(self, request: PermissionRequest) -> Optional[PermissionResponse]:
        """Check if we have an existing rule for this request"""
        # Check session rules first (yes-to-all, no-to-all)
        if self.yes_to_all:
            return PermissionResponse.YES
        if self.no_to_all:
            return PermissionResponse.NO

        # Check temporary session rules
        for rule in self.session_rules:
            if self._matches_rule(request, rule):
                return rule.response

        # Check permanent rules
        for rule in self.permanent_rules:
            if self._matches_rule(request, rule):
                if rule.expires and rule.expires < datetime.now():
                    continue  # Expired rule
                return rule.response

        return None

    def _matches_rule(self, request: PermissionRequest, rule: PermissionRule) -> bool:
        """
        Check if a request matches a rule.

        Delegates to extracted pure function (P2 decomposition).
        """
        return matches_pattern(
            command=request.command,
            pattern=rule.pattern,
            command_operation_type=request.operation_type,
            rule_operation_type=rule.operation_type,
        )

    def check_permission(self, command: str, risk_level: str = "low") -> bool:
        """Check if command is allowed (simplified interface)"""
        # Bypass mode for testing
        if self.bypass_mode:
            return True

        # This is a compatibility method that uses request_permission
        # which handles both interactive and non-interactive modes properly
        return self.request_permission(command, "command")

    def request_permission(
        self,
        command: str,
        operation_type: str = "command",
        details: Optional[Dict] = None,
    ) -> bool:
        """
        Request permission from user to execute a command
        Returns: True if allowed, False if denied
        """
        # Bypass mode for testing
        if self.bypass_mode:
            return True

        # Assess risk
        risk_level, risk_reason = self.assess_risk(command, operation_type)

        # Create request
        request = PermissionRequest(
            command=command,
            operation_type=operation_type,
            risk_level=risk_level,
            reason=risk_reason,
            details=details or {},
        )

        # Check existing rules
        existing_response = self.check_existing_rules(request)
        if existing_response:
            if existing_response in [
                PermissionResponse.YES,
                PermissionResponse.YES_TO_ALL,
            ]:
                self._log_decision(request, existing_response, automatic=True)
                return True
            elif existing_response in [
                PermissionResponse.NO,
                PermissionResponse.NO_TO_ALL,
            ]:
                self._log_decision(request, existing_response, automatic=True)
                return False

        # Ask user
        response = self._prompt_user(request)

        # Process response
        return self._process_response(request, response)

    def _prompt_user(self, request: PermissionRequest) -> PermissionResponse:
        """Prompt user for permission"""
        # Check if we're in non-interactive mode
        if self.non_interactive:
            return self._non_interactive_decision(request)

        # Display request
        print(f"\n{BOLD}{'='*60}{RESET}")
        print(
            f"{BOLD}{request.risk_level.icon} Permission Request {request.risk_level.icon}{RESET}"
        )
        print(f"{BOLD}{'='*60}{RESET}")

        # Show command with syntax highlighting
        print(f"{CYAN}Command:{RESET} {self._highlight_command(request.command)}")
        print(f"{CYAN}Type:{RESET} {request.operation_type}")
        print(f"{CYAN}Risk:{RESET} {request.risk_level.icon} {request.risk_level.label}")
        print(f"{CYAN}Reason:{RESET} {request.reason}")

        # Show additional details if provided
        if request.details:
            print(f"\n{CYAN}Details:{RESET}")
            for key, value in request.details.items():
                print(f"  • {key}: {value}")

        # Show options
        print(f"\n{BOLD}Options:{RESET}")
        print(f"  {GREEN}y{RESET}  - Yes, allow this command")
        print(f"  {RED}n{RESET}  - No, block this command")
        print(f"  {GREEN}a{RESET}  - Yes to all (this session)")
        print(f"  {RED}x{RESET}  - No to all (this session)")
        print(f"  {BLUE}s{RESET}  - Yes to similar commands")
        print(f"  {YELLOW}e{RESET}  - Explain what this does")
        print(f"  {CYAN}m{RESET}  - Modify command")
        print(f"  {DIM}p{RESET}  - Save preference permanently")

        while True:
            try:
                response = input(f"\n{BOLD}Allow? [y/n/a/x/s/e/m/p]:{RESET} ").strip().lower()

                if response in ["y", "yes"]:
                    return PermissionResponse.YES
                elif response in ["n", "no"]:
                    return PermissionResponse.NO
                elif response in ["a", "all", "yes all"]:
                    return PermissionResponse.YES_TO_ALL
                elif response in ["x", "none", "no all"]:
                    return PermissionResponse.NO_TO_ALL
                elif response in ["s", "similar"]:
                    return PermissionResponse.YES_TO_SIMILAR
                elif response in ["e", "explain"]:
                    self._explain_command(request)
                    continue
                elif response in ["m", "modify"]:
                    return PermissionResponse.EDIT
                elif response in ["p", "perm", "permanent"]:
                    self._save_permanent_rule(request)
                    continue
                else:
                    print(f"{YELLOW}Invalid response. Please choose: y/n/a/x/s/e/m/p{RESET}")

            except KeyboardInterrupt:
                print(f"\n{RED}Cancelled by user{RESET}")
                return PermissionResponse.NO
            except EOFError:
                return PermissionResponse.NO

    def _highlight_command(self, command: str) -> str:
        """
        Add color highlighting to dangerous parts of commands.

        Delegates to extracted pure function (P2 decomposition).
        """
        return highlight_dangerous_terms(command, red_code=RED, reset_code=RESET)

    def _non_interactive_decision(self, request: PermissionRequest) -> PermissionResponse:
        """Make decision in non-interactive mode based on policy"""
        risk_level = request.risk_level.level

        if self.non_interactive_policy == "strict":
            # Only allow SAFE operations
            if risk_level == 0:
                print(f"{GREEN}[Non-interactive] Auto-approved SAFE: {request.command[:50]}{RESET}")
                return PermissionResponse.YES
            else:
                print(
                    f"{RED}[Non-interactive] Auto-denied (strict policy): {request.command[:50]}{RESET}"
                )
                return PermissionResponse.NO

        elif self.non_interactive_policy == "permissive":
            # Allow everything except CRITICAL
            if risk_level < 4:
                print(
                    f"{GREEN}[Non-interactive] Auto-approved (risk={risk_level}): {request.command[:50]}{RESET}"
                )
                return PermissionResponse.YES
            else:
                print(f"{RED}[Non-interactive] Auto-denied CRITICAL: {request.command[:50]}{RESET}")
                return PermissionResponse.NO

        else:  # conservative (default)
            # Allow SAFE and LOW risk only
            if risk_level <= 1:
                print(
                    f"{GREEN}[Non-interactive] Auto-approved (risk={risk_level}): {request.command[:50]}{RESET}"
                )
                return PermissionResponse.YES
            else:
                print(
                    f"{YELLOW}[Non-interactive] Auto-denied (risk={risk_level}): {request.command[:50]}{RESET}"
                )
                return PermissionResponse.NO

    def _explain_command(self, request: PermissionRequest) -> None:
        """
        Explain what a command does.

        Uses imported constants from extracted module (P2 decomposition).
        """
        print(f"\n{BOLD}Command Explanation:{RESET}")

        # Parse command for explanation
        cmd_parts = request.command.split()
        if not cmd_parts:
            print("Empty command")
            return

        base_cmd = cmd_parts[0]

        # Use imported command explanations
        if base_cmd in COMMAND_EXPLANATIONS:
            print(f"  {CYAN}{base_cmd}:{RESET} {COMMAND_EXPLANATIONS[base_cmd]}")

        # Explain flags using imported explanations
        flags = [p for p in cmd_parts[1:] if p.startswith("-")]
        if flags:
            print(f"\n  {CYAN}Flags:{RESET}")
            for flag in flags:
                if flag in FLAG_EXPLANATIONS:
                    print(f"    {flag}: {FLAG_EXPLANATIONS[flag]}")
                else:
                    print(f"    {flag}: (flag)")

        # Risk explanation
        print(f"\n  {CYAN}Risk Assessment:{RESET}")
        print(f"    {request.risk_level.icon} {request.risk_level.label}: {request.reason}")

        # What will happen
        print(f"\n  {CYAN}What will happen:{RESET}")
        if "rm -rf /" in request.command:
            print(f"    {RED}⚠️ THIS WILL DELETE YOUR ENTIRE SYSTEM!{RESET}")
        elif "rm -rf" in request.command:
            print(
                f"    {RED}This will permanently delete files/folders without confirmation{RESET}"
            )
        elif "sudo" in request.command:
            print(f"    {YELLOW}This will run with administrator privileges{RESET}")
        else:
            print(f"    This command will: {request.reason}")

    def _process_response(self, request: PermissionRequest, response: PermissionResponse) -> bool:
        """Process user's response"""
        # Log decision
        self._log_decision(request, response)

        if response == PermissionResponse.YES:
            return True

        elif response == PermissionResponse.NO:
            return False

        elif response == PermissionResponse.YES_TO_ALL:
            self.yes_to_all = True
            print(f"{GREEN}✓ Allowing all commands for this session{RESET}")
            return True

        elif response == PermissionResponse.NO_TO_ALL:
            self.no_to_all = True
            print(f"{RED}✗ Blocking all commands for this session{RESET}")
            return False

        elif response == PermissionResponse.YES_TO_SIMILAR:
            # Create a rule for similar commands
            pattern = self._create_similar_pattern(request.command)
            rule = PermissionRule(
                pattern=pattern,
                response=PermissionResponse.YES,
                operation_type=request.operation_type,
            )
            self.session_rules.append(rule)
            print(f"{GREEN}✓ Allowing similar commands: {pattern}{RESET}")
            return True

        elif response == PermissionResponse.EDIT:
            # Allow user to modify the command
            new_command = input(f"{CYAN}Modified command:{RESET} ")
            if new_command:
                request.command = new_command
                # Re-assess and ask again
                return self.request_permission(new_command, request.operation_type, request.details)
            return False

        return False

    def _create_similar_pattern(self, command: str) -> str:
        """
        Create a pattern for similar commands.

        Delegates to extracted pure function (P2 decomposition).
        """
        return create_similar_pattern(command)

    def _save_permanent_rule(self, request: PermissionRequest) -> None:
        """Save a permanent permission rule"""
        print(f"\n{BOLD}Save Permission Rule:{RESET}")
        print("1. Always allow this exact command")
        print(
            f"2. Always allow similar commands ({self._create_similar_pattern(request.command)}*)"
        )
        print("3. Always block this exact command")
        print("4. Always block similar commands")
        print("5. Cancel")

        choice = input(f"\n{BOLD}Choice [1-5]:{RESET} ").strip()

        if choice == "1":
            rule = PermissionRule(
                pattern=request.command,
                response=PermissionResponse.YES,
                operation_type=request.operation_type,
            )
            self.permanent_rules.append(rule)
            self._save_rules()
            print(f"{GREEN}✓ Saved: Always allow '{request.command}'{RESET}")

        elif choice == "2":
            pattern = self._create_similar_pattern(request.command)
            rule = PermissionRule(
                pattern=pattern,
                response=PermissionResponse.YES,
                operation_type=request.operation_type,
            )
            self.permanent_rules.append(rule)
            self._save_rules()
            print(f"{GREEN}✓ Saved: Always allow commands matching '{pattern}*'{RESET}")

        elif choice == "3":
            rule = PermissionRule(
                pattern=request.command,
                response=PermissionResponse.NO,
                operation_type=request.operation_type,
            )
            self.permanent_rules.append(rule)
            self._save_rules()
            print(f"{RED}✓ Saved: Always block '{request.command}'{RESET}")

        elif choice == "4":
            pattern = self._create_similar_pattern(request.command)
            rule = PermissionRule(
                pattern=pattern,
                response=PermissionResponse.NO,
                operation_type=request.operation_type,
            )
            self.permanent_rules.append(rule)
            self._save_rules()
            print(f"{RED}✓ Saved: Always block commands matching '{pattern}*'{RESET}")

    def _log_decision(
        self,
        request: PermissionRequest,
        response: PermissionResponse,
        automatic: bool = False,
    ):
        """Log permission decision"""
        self.history.append((request, response))

        # Log to console if automatic
        if automatic:
            icon = (
                "✓" if response in [PermissionResponse.YES, PermissionResponse.YES_TO_ALL] else "✗"
            )
            print(f"{DIM}[Auto {icon}] {request.command[:50]}...{RESET}")

    def reset_session_rules(self) -> None:
        """Reset session-specific rules"""
        self.session_rules.clear()
        self.yes_to_all = False
        self.no_to_all = False
        print(f"{YELLOW}Session rules reset{RESET}")

    def show_rules(self) -> None:
        """Display current permission rules"""
        print(f"\n{BOLD}Current Permission Rules:{RESET}")

        if self.yes_to_all:
            print(f"  {GREEN}• Yes to all (this session){RESET}")
        if self.no_to_all:
            print(f"  {RED}• No to all (this session){RESET}")

        if self.session_rules:
            print(f"\n{CYAN}Session Rules:{RESET}")
            for rule in self.session_rules:
                icon = "✓" if rule.response == PermissionResponse.YES else "✗"
                print(f"  {icon} {rule.pattern} ({rule.operation_type})")

        if self.permanent_rules:
            print(f"\n{CYAN}Permanent Rules:{RESET}")
            for rule in self.permanent_rules:
                icon = "✓" if rule.response == PermissionResponse.YES else "✗"
                expires = f" [expires: {rule.expires}]" if rule.expires else ""
                print(f"  {icon} {rule.pattern} ({rule.operation_type}){expires}")

    def get_statistics(self) -> Dict:
        """Get permission statistics"""
        total = len(self.history)
        if total == 0:
            return {}

        allowed = sum(
            1
            for _, r in self.history
            if r in [PermissionResponse.YES, PermissionResponse.YES_TO_ALL]
        )
        denied = sum(
            1 for _, r in self.history if r in [PermissionResponse.NO, PermissionResponse.NO_TO_ALL]
        )

        risk_counts = defaultdict(int)
        for req, _ in self.history:
            risk_counts[req.risk_level.label] += 1

        return {
            "total_requests": total,
            "allowed": allowed,
            "denied": denied,
            "allow_rate": (allowed / total * 100) if total > 0 else 0,
            "risk_distribution": dict(risk_counts),
            "permanent_rules": len(self.permanent_rules),
            "session_rules": len(self.session_rules),
        }


def test_permission_layer() -> None:
    """Test the permission layer"""
    print(f"{BOLD}Testing Permission Layer{RESET}")

    permissions = PermissionLayer()

    # Test different risk levels
    test_commands = [
        "ls -la",  # Safe
        "mkdir test_dir",  # Low risk
        "rm test.txt",  # Medium risk
        "sudo apt-get update",  # High risk
        "rm -rf /",  # Critical risk
    ]

    print(f"\n{BOLD}Testing Permission Requests:{RESET}")
    for cmd in test_commands:
        print(f"\n{CYAN}Testing: {cmd}{RESET}")
        # Simulate user interaction (would be interactive in real use)
        allowed = permissions.request_permission(cmd, "command")
        result = f"{GREEN}Allowed{RESET}" if allowed else f"{RED}Denied{RESET}"
        print(f"Result: {result}")

    # Show statistics
    stats = permissions.get_statistics()
    print(f"\n{BOLD}Permission Statistics:{RESET}")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print(f"\n{GREEN}✓ Permission Layer Test Complete{RESET}")


# Alias for compatibility
PermissionSystem = PermissionLayer

if __name__ == "__main__":
    test_permission_layer()
