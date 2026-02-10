"""
Security Headers Middleware

Adds security headers to all HTTP responses to protect against common
web vulnerabilities: clickjacking, MIME sniffing, XSS, and more.

Based on OWASP Secure Headers Project recommendations.
"""

import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses

    Headers added:
    - X-Content-Type-Options: Prevents MIME sniffing attacks
    - X-Frame-Options: Prevents clickjacking attacks
    - X-XSS-Protection: Legacy XSS protection (browsers)
    - Referrer-Policy: Controls referrer information leakage
    - Content-Security-Policy: Prevents XSS and data injection attacks
    - Permissions-Policy: Controls browser feature access
    - Strict-Transport-Security: Enforces HTTPS (production only)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add security headers to response"""
        response: Response = await call_next(request)

        # Determine if production mode
        env = os.getenv('MEDSTATION_ENV', 'production').lower()
        is_production = env == 'production'

        # X-Content-Type-Options: Prevent MIME sniffing
        # OWASP: Always set to 'nosniff' to prevent browsers from interpreting
        # files as a different MIME type than declared
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: Prevent clickjacking
        # OWASP: Use 'DENY' unless you need to frame your own content
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection: Legacy XSS filter for older browsers
        # Note: Modern browsers rely on CSP, but this helps older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy: Control referrer information
        # 'strict-origin-when-cross-origin': Send origin for cross-origin,
        # full URL for same-origin, nothing for downgrade (HTTPS → HTTP)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content-Security-Policy: Prevent XSS and injection attacks
        # Different policies for dev vs production
        if is_production:
            # Production: Strict CSP
            csp_directives = [
                "default-src 'self'",  # Only load resources from same origin
                "script-src 'self'",   # Only scripts from same origin
                "style-src 'self' 'unsafe-inline'",  # Allow inline styles (for React/Vue)
                "img-src 'self' data: https:",  # Images from self, data URIs, HTTPS
                "font-src 'self' data:",  # Fonts from self and data URIs
                "connect-src 'self'",  # API calls to same origin only
                "frame-ancestors 'none'",  # Don't allow framing (redundant with X-Frame-Options)
                "base-uri 'self'",  # Prevent base tag injection
                "form-action 'self'",  # Forms only submit to same origin
                "upgrade-insecure-requests"  # Upgrade HTTP to HTTPS automatically
            ]
        else:
            # Development: Relaxed CSP for easier debugging
            csp_directives = [
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Allow eval for dev tools
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https: http:",  # Allow HTTP images in dev
                "font-src 'self' data:",
                "connect-src 'self' ws: wss: http://localhost:* http://127.0.0.1:*",  # WebSocket + dev servers
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'"
            ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Permissions-Policy: Control browser features
        # Disable unnecessary features to reduce attack surface
        permissions_directives = [
            "geolocation=()",  # No geolocation
            "microphone=()",   # No microphone
            "camera=()",       # No camera
            "payment=()",      # No payment APIs
            "usb=()",          # No USB access
            "magnetometer=()", # No magnetometer
            "gyroscope=()",    # No gyroscope
            "accelerometer=()" # No accelerometer
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_directives)

        # Strict-Transport-Security: Enforce HTTPS (production only)
        # OWASP: Only add if serving over HTTPS
        # HIGH-05 FIX: Check X-Forwarded-Proto header for reverse proxy support
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
        is_https = request.url.scheme == "https" or forwarded_proto.lower() == "https"

        if is_production and is_https:
            # max-age=31536000: 1 year in seconds
            # includeSubDomains: Apply to all subdomains
            # preload: Allow submission to browser preload lists
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response


def add_security_headers(app: FastAPI) -> None:
    """
    Add security headers middleware to FastAPI application

    Args:
        app: FastAPI application instance

    Usage:
        from fastapi import FastAPI
        from middleware.security_headers import add_security_headers

        app = FastAPI()
        add_security_headers(app)
    """
    app.add_middleware(SecurityHeadersMiddleware)
