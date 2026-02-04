"""
Terminal Services Package

Provides comprehensive terminal integration:
- PTY-based sessions
- Terminal multiplexing
- Native terminal integrations (iTerm2, Warp)
"""

from .multiplexer import PaneLayout, TerminalMultiplexer, get_multiplexer
from .native_integrations import (
    ITerm2Integration,
    TerminalApp,
    TerminalIntegration,
    WarpIntegration,
    detect_terminal,
    get_terminal_integration,
)
from .pty_session import PTYSessionManager, TerminalSession, get_pty_manager

__all__ = [
    "ITerm2Integration",
    "PTYSessionManager",
    "PaneLayout",
    "TerminalApp",
    "TerminalIntegration",
    "TerminalMultiplexer",
    "TerminalSession",
    "WarpIntegration",
    "detect_terminal",
    "get_multiplexer",
    "get_pty_manager",
    "get_terminal_integration",
]
