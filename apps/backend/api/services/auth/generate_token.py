#!/usr/bin/env python3
"""
Token Generation Utility

Generate JWT tokens for API authentication.

Usage:
    python generate_token.py <client_id> [description]

Example:
    python generate_token.py magnetar-studio "MedStation integration"

Environment Variables:
    JWT_SECRET_KEY - Secret key for signing tokens (auto-generated if not set)
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES - Access token expiration (default: 60)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS - Refresh token expiration (default: 7)
"""
# ruff: noqa: T201  # Print statements are intentional for CLI output

import json
import sys

from jwt_auth import create_api_token


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_token.py <client_id> [description]")
        print("\nExample:")
        print('  python generate_token.py magnetar-studio "MedStation integration"')
        sys.exit(1)

    client_id = sys.argv[1]
    description = sys.argv[2] if len(sys.argv) > 2 else None

    # Generate tokens
    tokens = create_api_token(client_id, description)

    # Pretty print
    print("\n" + "=" * 60)
    print("JWT TOKENS GENERATED")
    print("=" * 60)
    print(f"\nClient ID: {client_id}")
    if description:
        print(f"Description: {description}")
    print("\n" + "-" * 60)
    print("ACCESS TOKEN (expires in 1 hour):")
    print("-" * 60)
    print(tokens["access_token"])
    print("\n" + "-" * 60)
    print("REFRESH TOKEN (expires in 7 days):")
    print("-" * 60)
    print(tokens["refresh_token"])
    print("\n" + "-" * 60)
    print("\nUSAGE:")
    print("-" * 60)
    print("Include in Authorization header:")
    print(f'  Authorization: Bearer {tokens["access_token"][:50]}...')
    print("\nWhen access token expires, refresh using:")
    print("  POST /bridge/token/refresh")
    print(f'  {{"refresh_token": "{tokens["refresh_token"][:50]}..."}}"')
    print("\n" + "=" * 60)
    print("\nJSON Output:")
    print(json.dumps(tokens, indent=2))
    print()


if __name__ == "__main__":
    main()
