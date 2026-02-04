#!/usr/bin/env python3
"""
Native Terminal Integrations

Deep integrations with macOS terminals:
- iTerm2: AppleScript automation
- Warp: CLI and API integration
- Terminal.app: Basic AppleScript support
"""

import os
import subprocess
from enum import Enum
from typing import Any

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


def sanitize_applescript_string(value: str) -> str:
    """
    Sanitize a string for safe inclusion in AppleScript.

    SECURITY: Prevents command injection by escaping special characters
    that could break out of AppleScript string literals.

    Args:
        value: The untrusted user input

    Returns:
        Escaped string safe for use in AppleScript double-quoted strings
    """
    if not value:
        return value

    # Order matters: escape backslashes first, then other characters
    return (
        value.replace("\\", "\\\\")  # Escape backslashes
        .replace('"', '\\"')  # Escape double quotes
        .replace("\n", "\\n")  # Escape newlines
        .replace("\r", "\\r")  # Escape carriage returns
        .replace("\t", "\\t")  # Escape tabs
    )


class TerminalApp(Enum):
    """Supported terminal applications"""

    ITERM2 = "iTerm2"
    WARP = "Warp"
    TERMINAL = "Terminal"
    UNKNOWN = "unknown"


def detect_terminal() -> TerminalApp:
    """
    Detect which terminal application is currently running

    Returns:
        Detected terminal app
    """
    try:
        # Check running applications
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of processes'],
            capture_output=True,
            text=True,
            timeout=5,
        )

        processes = result.stdout.lower()

        if "iterm" in processes:
            return TerminalApp.ITERM2
        elif "warp" in processes:
            return TerminalApp.WARP
        elif "terminal" in processes:
            return TerminalApp.TERMINAL

    except Exception as e:
        logger.error(f"Error detecting terminal: {e}")

    return TerminalApp.UNKNOWN


class ITerm2Integration:
    """
    iTerm2 integration via AppleScript

    Features:
    - Create new tabs/windows
    - Send commands
    - Get current directory
    - Set tab title
    - Split panes
    """

    @staticmethod
    def is_available() -> bool:
        """Check if iTerm2 is installed"""
        return os.path.exists("/Applications/iTerm.app")

    @staticmethod
    def create_tab(
        command: str | None = None,
        working_dir: str | None = None,
        title: str | None = None,
    ) -> bool:
        """
        Create a new iTerm2 tab

        Args:
            command: Initial command to run
            working_dir: Working directory
            title: Tab title

        Returns:
            True if successful
        """
        script_parts = [
            'tell application "iTerm"',
            "    tell current window",
            "        create tab with default profile",
        ]

        # SECURITY: Sanitize all user inputs before embedding in AppleScript
        if working_dir:
            safe_dir = sanitize_applescript_string(working_dir)
            script_parts.append(f'        tell current session to write text "cd {safe_dir}"')

        if command:
            safe_cmd = sanitize_applescript_string(command)
            script_parts.append(f'        tell current session to write text "{safe_cmd}"')

        if title:
            safe_title = sanitize_applescript_string(title)
            script_parts.append(f'        tell current session to set name to "{safe_title}"')

        script_parts.extend(["    end tell", "end tell"])

        return ITerm2Integration._run_applescript("\n".join(script_parts))

    @staticmethod
    def create_window(command: str | None = None, working_dir: str | None = None) -> bool:
        """Create a new iTerm2 window"""
        script_parts = ['tell application "iTerm"', "    create window with default profile"]

        # SECURITY: Sanitize all user inputs before embedding in AppleScript
        if working_dir:
            safe_dir = sanitize_applescript_string(working_dir)
            script_parts.append(
                f'    tell current session of current window to write text "cd {safe_dir}"'
            )

        if command:
            safe_cmd = sanitize_applescript_string(command)
            script_parts.append(
                f'    tell current session of current window to write text "{safe_cmd}"'
            )

        script_parts.append("end tell")

        return ITerm2Integration._run_applescript("\n".join(script_parts))

    @staticmethod
    def send_command(command: str) -> bool:
        """Send command to current iTerm2 session"""
        # SECURITY: Sanitize command before embedding in AppleScript
        safe_cmd = sanitize_applescript_string(command)
        script = f"""
        tell application "iTerm"
            tell current session of current window
                write text "{safe_cmd}"
            end tell
        end tell
        """

        return ITerm2Integration._run_applescript(script)

    @staticmethod
    def split_pane(direction: str = "horizontal", command: str | None = None) -> bool:
        """
        Split current pane

        Args:
            direction: "horizontal" or "vertical"
            command: Command to run in new pane

        Returns:
            True if successful
        """
        split_type = "horizontally" if direction == "horizontal" else "vertically"

        script = f"""
        tell application "iTerm"
            tell current session of current window
                split {split_type} with default profile
            end tell
        end tell
        """

        success = ITerm2Integration._run_applescript(script)

        if success and command:
            # Send command to new pane
            return ITerm2Integration.send_command(command)

        return success

    @staticmethod
    def get_current_directory() -> str | None:
        """Get current directory from iTerm2"""
        script = """
        tell application "iTerm"
            tell current session of current window
                get variable named "user.current_directory"
            end tell
        end tell
        """

        result = ITerm2Integration._run_applescript_output(script)
        return result.strip() if result else None

    @staticmethod
    def set_tab_title(title: str) -> bool:
        """Set title of current tab"""
        # SECURITY: Sanitize title before embedding in AppleScript
        safe_title = sanitize_applescript_string(title)
        script = f"""
        tell application "iTerm"
            tell current session of current window
                set name to "{safe_title}"
            end tell
        end tell
        """

        return ITerm2Integration._run_applescript(script)

    @staticmethod
    def _run_applescript(script: str) -> bool:
        """Execute AppleScript and return success"""
        try:
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"AppleScript error: {e}")
            return False

    @staticmethod
    def _run_applescript_output(script: str) -> str | None:
        """Execute AppleScript and return output"""
        try:
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception as e:
            logger.error(f"AppleScript error: {e}")
            return None


class WarpIntegration:
    """
    Warp terminal integration

    Features:
    - Open in Warp
    - Send commands via CLI
    - Deep links
    """

    @staticmethod
    def is_available() -> bool:
        """Check if Warp is installed"""
        return os.path.exists("/Applications/Warp.app")

    @staticmethod
    def open_directory(working_dir: str) -> bool:
        """
        Open directory in Warp

        Args:
            working_dir: Directory to open

        Returns:
            True if successful
        """
        try:
            subprocess.run(["open", "-a", "Warp", working_dir], check=True, timeout=10)
            return True
        except Exception as e:
            logger.error(f"Error opening Warp: {e}")
            return False

    @staticmethod
    def create_deep_link(working_dir: str, command: str | None = None) -> str:
        """
        Create Warp deep link

        Args:
            working_dir: Working directory
            command: Command to run

        Returns:
            Deep link URL
        """
        # Warp deep link format: warp://action?path=/path&command=command
        import urllib.parse

        params = {"path": working_dir}
        if command:
            params["command"] = command

        query = urllib.parse.urlencode(params)
        return f"warp://action?{query}"

    @staticmethod
    def send_command(command: str) -> bool:
        """
        Send command to Warp (via AppleScript as fallback)

        Args:
            command: Command to execute

        Returns:
            True if successful
        """
        # SECURITY: Sanitize command before embedding in AppleScript
        safe_cmd = sanitize_applescript_string(command)
        script = f"""
        tell application "Warp"
            activate
            tell application "System Events"
                keystroke "{safe_cmd}"
                key code 36
            end tell
        end tell
        """

        try:
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error sending command to Warp: {e}")
            return False


class TerminalIntegration:
    """
    Unified terminal integration

    Automatically detects and uses the appropriate terminal
    """

    def __init__(self):
        self.current_terminal = detect_terminal()

    def create_tab(
        self,
        command: str | None = None,
        working_dir: str | None = None,
        title: str | None = None,
    ) -> bool:
        """Create new tab in detected terminal"""
        if self.current_terminal == TerminalApp.ITERM2:
            return ITerm2Integration.create_tab(command, working_dir, title)

        elif self.current_terminal == TerminalApp.WARP and working_dir:
            return WarpIntegration.open_directory(working_dir)

        return False

    def create_window(
        self, command: str | None = None, working_dir: str | None = None
    ) -> bool:
        """Create new window in detected terminal"""
        if self.current_terminal == TerminalApp.ITERM2:
            return ITerm2Integration.create_window(command, working_dir)

        elif self.current_terminal == TerminalApp.WARP and working_dir:
            return WarpIntegration.open_directory(working_dir)

        return False

    def send_command(self, command: str) -> bool:
        """Send command to current terminal"""
        if self.current_terminal == TerminalApp.ITERM2:
            return ITerm2Integration.send_command(command)

        elif self.current_terminal == TerminalApp.WARP:
            return WarpIntegration.send_command(command)

        return False

    def split_pane(self, direction: str = "horizontal", command: str | None = None) -> bool:
        """Split pane in current terminal"""
        if self.current_terminal == TerminalApp.ITERM2:
            return ITerm2Integration.split_pane(direction, command)

        # Warp doesn't support programmatic pane splitting yet
        return False

    def get_capabilities(self) -> dict[str, bool]:
        """Get capabilities of current terminal"""
        caps = {
            "create_tab": False,
            "create_window": False,
            "send_command": False,
            "split_pane": False,
            "get_directory": False,
            "set_title": False,
        }

        if self.current_terminal == TerminalApp.ITERM2:
            caps.update(
                {
                    "create_tab": True,
                    "create_window": True,
                    "send_command": True,
                    "split_pane": True,
                    "get_directory": True,
                    "set_title": True,
                }
            )

        elif self.current_terminal == TerminalApp.WARP:
            caps.update({"create_window": True, "send_command": True})

        return caps

    def get_terminal_info(self) -> dict[str, Any]:
        """Get information about detected terminal"""
        return {
            "terminal": self.current_terminal.value,
            "is_iterm": self.current_terminal == TerminalApp.ITERM2,
            "is_warp": self.current_terminal == TerminalApp.WARP,
            "iterm_available": ITerm2Integration.is_available(),
            "warp_available": WarpIntegration.is_available(),
            "capabilities": self.get_capabilities(),
        }


# Global instance
_terminal_integration: TerminalIntegration | None = None


def get_terminal_integration() -> TerminalIntegration:
    """Get or create global terminal integration"""
    global _terminal_integration
    if _terminal_integration is None:
        _terminal_integration = TerminalIntegration()
    return _terminal_integration
