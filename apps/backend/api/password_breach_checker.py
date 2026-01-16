"""
Compatibility Shim for Password Breach Checker

The implementation now lives in the `api.security` package:
- api.security.password_breach: PasswordBreachChecker class

This shim maintains backward compatibility.

Note: Requires 'aiohttp' package to be installed.
"""

try:
    from api.security.password_breach import (
        PasswordBreachChecker,
        get_breach_checker,
        check_password_breach,
        cleanup_breach_checker,
    )
except ImportError:
    PasswordBreachChecker = None
    get_breach_checker = None
    check_password_breach = None
    cleanup_breach_checker = None

__all__ = [
    "PasswordBreachChecker",
    "get_breach_checker",
    "check_password_breach",
    "cleanup_breach_checker",
]
