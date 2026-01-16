"""
Compatibility Shim for User Isolation Migration

The implementation now lives in the `api.migrations` package:
- api.migrations.add_user_isolation

This shim maintains backward compatibility.
"""

from api.migrations.add_user_isolation import *
