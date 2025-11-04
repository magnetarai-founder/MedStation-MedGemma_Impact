#!/usr/bin/env python3
"""
Fix all vault endpoints to use authenticated user instead of default_user
Phase 1 completion script
"""

import re
from pathlib import Path

vault_service_path = Path(__file__).parent / "vault_service.py"

# Read the file
with open(vault_service_path, 'r') as f:
    content = f.read()

# Pattern 1: Replace standalone TODO lines with default_user
# Match: # TODO: Get real user_id from auth middleware\n    user_id = "default_user"
pattern1 = r'(\s+)# TODO: Get real user_id from auth middleware\n\s+user_id = "default_user"'
replacement1 = r'\1user_id = current_user["user_id"]'

# Pattern 2: Replace simple default_user assignments (without TODO comment)
# Match: user_id = "default_user"  # TODO: Get from auth
pattern2 = r'(\s+)user_id = "default_user"  # TODO: Get from auth'
replacement2 = r'\1user_id = current_user["user_id"]'

# Pattern 3: Replace simple default_user assignments (no comment)
# Match: user_id = "default_user"
pattern3 = r'(\s+)user_id = "default_user"(?!\w)'  # negative lookahead to avoid matching in strings
replacement3 = r'\1user_id = current_user["user_id"]'

# Apply replacements
content_fixed = re.sub(pattern1, replacement1, content)
content_fixed = re.sub(pattern2, replacement2, content_fixed)
content_fixed = re.sub(pattern3, replacement3, content_fixed)

# Now we need to ensure all affected endpoints have current_user parameter
# Find all endpoint definitions and check if they need current_user added

# Pattern for async def endpoints
endpoint_pattern = r'(@router\.(get|post|put|delete|patch)\([^)]+\)\s*\n\s*async def \w+\s*\([^)]*)\):'

def add_current_user_if_needed(match):
    """Add current_user parameter if the function uses current_user["user_id"] but doesn't have the param"""
    full_match = match.group(0)
    params = match.group(1)

    # Check if current_user is already in params
    if 'current_user' in params:
        return full_match

    # Find the end of the function to see if it uses current_user
    # This is approximate - we'll handle it manually if needed
    return full_match

# We'll need to manually add current_user: Dict = Depends(get_current_user) to endpoints
# Let's just do the text replacements for now and add imports

# Check if get_current_user is imported
if 'from auth_middleware import get_current_user' not in content_fixed:
    # Find the imports section and add it
    import_pattern = r'(from fastapi import[^\n]+\n)'
    import_addition = r'\1from auth_middleware import get_current_user\n'
    content_fixed = re.sub(import_pattern, import_addition, content_fixed, count=1)

# Write back
with open(vault_service_path, 'w') as f:
    f.write(content_fixed)

print(f"✓ Fixed vault_service.py")
print(f"  Replaced default_user with current_user['user_id']")
print(f"\nNOTE: You must manually add 'current_user: Dict = Depends(get_current_user)' to endpoint signatures")
print(f"      that don't already have it. Search for endpoints using current_user['user_id']")
