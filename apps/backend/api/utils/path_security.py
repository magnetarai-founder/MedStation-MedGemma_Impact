"""
Path and URL security utilities to prevent path traversal and SSRF attacks.

Centralized validation logic used across multiple API endpoints.
"""

import ipaddress
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException


# ==============================================================================
# SSRF Protection
# ==============================================================================

# IPs that should be blocked to prevent SSRF attacks
_BLOCKED_IP_RANGES = [
    ipaddress.ip_network("169.254.0.0/16"),  # AWS/Cloud metadata service
    ipaddress.ip_network("100.100.100.0/24"),  # Alibaba Cloud metadata
    ipaddress.ip_network("192.0.0.0/24"),  # IETF protocol assignments
]

# Hostnames that should always be blocked
_BLOCKED_HOSTNAMES = {
    "metadata.google.internal",  # GCP metadata
    "metadata.goog",
    "169.254.169.254",  # AWS/Azure/GCP metadata
}


def validate_url_for_ssrf(
    url: str,
    allow_localhost: bool = True,
    allow_private: bool = False,
    context: str = "URL",
) -> str:
    """
    Validate a URL to prevent SSRF attacks.

    Args:
        url: The URL to validate
        allow_localhost: Whether to allow localhost/127.0.0.1 (default: True)
        allow_private: Whether to allow private IP ranges (default: False)
        context: Description for error messages

    Returns:
        The validated URL

    Raises:
        ValueError: If URL is potentially dangerous
    """
    if not url:
        raise ValueError(f"Empty {context} not allowed")

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid {context}: {e}")

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid {context} scheme: '{parsed.scheme}'. Only http/https allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"Invalid {context}: no hostname specified")

    # Check for blocked hostnames
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Blocked {context}: '{hostname}' is not allowed")

    # Resolve hostname to check IP
    try:
        # Get all IPs for hostname
        addr_infos = socket.getaddrinfo(hostname, parsed.port or 80, type=socket.SOCK_STREAM)
        ips = [info[4][0] for info in addr_infos]
    except socket.gaierror:
        # Can't resolve - might be intentional for localhost-only services
        # Only allow if it's localhost
        if hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError(f"Cannot resolve {context} hostname: '{hostname}'")
        return url

    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        # Check for loopback
        if ip.is_loopback:
            if not allow_localhost:
                raise ValueError(
                    f"Localhost not allowed in {context}: '{hostname}' resolves to {ip_str}"
                )
            continue

        # Check for private ranges
        if ip.is_private:
            if not allow_private:
                raise ValueError(
                    f"Private IP not allowed in {context}: '{hostname}' resolves to {ip_str}"
                )
            continue

        # Check for blocked ranges (metadata services, etc.)
        for blocked in _BLOCKED_IP_RANGES:
            if ip in blocked:
                raise ValueError(
                    f"Blocked IP range in {context}: '{hostname}' resolves to {ip_str}"
                )

    return url


def validate_ollama_url(url: str) -> str:
    """
    Validate Ollama base URL with appropriate SSRF protection.

    Ollama is designed to run on localhost, so we:
    - Allow localhost/127.0.0.1 (the normal case)
    - Block cloud metadata services
    - Warn but allow private IPs if ALLOW_PRIVATE_OLLAMA is set

    Args:
        url: The Ollama base URL to validate

    Returns:
        The validated URL

    Raises:
        ValueError: If URL is dangerous
    """
    allow_private = os.getenv("ALLOW_PRIVATE_OLLAMA", "").lower() in ("true", "1", "yes")

    return validate_url_for_ssrf(
        url,
        allow_localhost=True,
        allow_private=allow_private,
        context="Ollama URL",
    )


def validate_workspace_path(workspace_path: str, file_path: str) -> Path:
    """
    Validate that file_path is within workspace_path (security check).

    Args:
        workspace_path: Root workspace directory
        file_path: Relative file path to validate

    Returns:
        Resolved absolute path if valid

    Raises:
        HTTPException: If path is outside workspace or invalid
    """
    workspace = Path(workspace_path).resolve()
    full_path = (workspace / file_path).resolve()

    # Security: Ensure file is within workspace
    try:
        full_path.relative_to(workspace)
    except ValueError:
        raise HTTPException(status_code=403, detail=f"Path outside workspace: {file_path}")

    return full_path


def sanitize_file_path(file_path: str) -> str:
    """
    Sanitize file path to prevent directory traversal.

    Args:
        file_path: File path to sanitize

    Returns:
        Sanitized path with dangerous patterns removed

    Raises:
        HTTPException: If path contains dangerous patterns
    """
    # Check for dangerous patterns
    dangerous_patterns = [
        "..",  # Parent directory
        "~",  # Home directory
        "/etc/",  # System directories
        "/var/",
        "/usr/",
        "/bin/",
        "/sbin/",
    ]

    path_lower = file_path.lower()
    for pattern in dangerous_patterns:
        if pattern in path_lower:
            raise HTTPException(
                status_code=400, detail=f"Invalid path: contains forbidden pattern '{pattern}'"
            )

    # Additional security checks
    if file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Absolute paths are not allowed")

    return file_path


def check_file_exists(file_path: Path, resource_name: str = "File") -> None:
    """
    Check if file exists, raise standardized error if not.

    Args:
        file_path: Path to check
        resource_name: Name of resource for error message

    Raises:
        HTTPException: 404 if file doesn't exist
    """
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"{resource_name} not found: {file_path.name}")


def check_is_file(file_path: Path) -> None:
    """
    Check if path is a file (not directory), raise error if not.

    Args:
        file_path: Path to check

    Raises:
        HTTPException: 400 if not a file
    """
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {file_path.name}")


def check_file_size(file_path: Path, max_size: int = 1024 * 1024) -> None:
    """
    Check if file size is within limit.

    Args:
        file_path: Path to check
        max_size: Maximum file size in bytes (default: 1MB)

    Raises:
        HTTPException: 413 if file too large
    """
    size = file_path.stat().st_size
    if size > max_size:
        raise HTTPException(
            status_code=413, detail=f"File too large: {size} bytes (max: {max_size})"
        )


def validate_file_for_reading(
    workspace_path: str, file_path: str, max_size: int | None = None
) -> Path:
    """
    Complete validation for reading a file.

    Combines all common validations:
    - Path traversal check
    - File exists check
    - Is file check
    - Size check (optional)

    Args:
        workspace_path: Root workspace directory
        file_path: Relative file path
        max_size: Optional maximum file size in bytes

    Returns:
        Validated absolute file path

    Raises:
        HTTPException: If any validation fails
    """
    # Validate path is within workspace
    full_path = validate_workspace_path(workspace_path, file_path)

    # Check file exists
    check_file_exists(full_path)

    # Check is a file
    check_is_file(full_path)

    # Check size if limit specified
    if max_size:
        check_file_size(full_path, max_size)

    return full_path
