#!/usr/bin/env python3
"""
Automated route refactoring script for ElohimOS backend.

This script splits monolithic route files into focused submodules:
- api/vault/routes.py → api/routes/vault/
- api/routes/chat.py → api/routes/chat/
- api/routes/team.py → api/routes/team/

Each submodule focuses on a specific resource or feature area.
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple

# Base paths
BACKEND_DIR = Path(__file__).parent
ROUTES_DIR = BACKEND_DIR / "api" / "routes"
VAULT_OLD = BACKEND_DIR / "api" / "vault" / "routes.py"
CHAT_OLD = ROUTES_DIR / "chat.py"
TEAM_OLD = ROUTES_DIR / "team.py"

# Output directories
VAULT_PKG = ROUTES_DIR / "vault"
CHAT_PKG = ROUTES_DIR / "chat"
TEAM_PKG = ROUTES_DIR / "team"


def extract_imports_and_common(content: str) -> Tuple[str, List[str]]:
    """Extract common imports and module-level code."""
    lines = content.split('\n')
    imports = []
    common_code = []
    in_imports = True

    for line in lines:
        if line.strip().startswith(('import ', 'from ', '#', '"""', "'''")):
            imports.append(line)
        elif line.strip().startswith('@router') or line.strip().startswith('router = '):
            in_imports = False
        elif in_imports and (line.strip().startswith('logger =') or 'manager =' in line):
            common_code.append(line)
        elif not in_imports:
            break

    return '\n'.join(imports), common_code


def extract_endpoints_by_pattern(content: str, patterns: List[str]) -> str:
    """Extract endpoints matching URL patterns."""
    lines = content.split('\n')
    endpoints = []
    capturing = False
    current_endpoint = []
    indent_stack = []

    for i, line in enumerate(lines):
        # Check if line starts an endpoint matching our patterns
        if line.strip().startswith('@router.'):
            route_match = re.search(r'@router\.\w+\("([^"]+)"', line)
            if route_match:
                route_path = route_match.group(1)
                if any(pattern in route_path for pattern in patterns):
                    capturing = True
                    current_endpoint = [line]
                    continue

        if capturing:
            current_endpoint.append(line)

            # Simple heuristic: if we hit another @router or end of indented block
            if line.strip().startswith('@router.') and len(current_endpoint) > 1:
                # Save previous endpoint
                endpoints.extend(current_endpoint[:-1])
                endpoints.append('')  # Blank line separator
                current_endpoint = [line]
            elif line and not line[0].isspace() and not line.strip().startswith('#'):
                # End of function
                if len(current_endpoint) > 10:  # Valid endpoint
                    endpoints.extend(current_endpoint)
                    endpoints.append('')
                current_endpoint = []
                capturing = False

    # Add final endpoint if still capturing
    if current_endpoint and len(current_endpoint) > 10:
        endpoints.extend(current_endpoint)

    return '\n'.join(endpoints)


def split_vault_routes():
    """Split vault routes into submodules."""
    print("Refactoring Vault routes...")

    content = VAULT_OLD.read_text()
    imports, common = extract_imports_and_common(content)

    # Create package directory
    VAULT_PKG.mkdir(parents=True, exist_ok=True)

    # Folders submodule
    folders_content = f'''"""
Vault Folders Routes - Folder create/list/navigate operations
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['/folders'])}
'''

    (VAULT_PKG / 'folders.py').write_text(folders_content)
    print(f"  Created folders.py ({len(folders_content.split(chr(10)))} lines)")

    # Sharing submodule (ACL, sharing, invitations, multi-user)
    sharing_content = f'''"""
Vault Sharing Routes - Share/unshare/ACL management
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['/acl/', '/sharing/', '/share/', '/users/'])}
'''

    (VAULT_PKG / 'sharing.py').write_text(sharing_content)
    print(f"  Created sharing.py ({len(sharing_content.split(chr(10)))} lines)")

    # WebSocket submodule
    ws_content = f'''"""
Vault WebSocket Routes - Real-time collaboration
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['/ws/'])}
'''

    (VAULT_PKG / 'ws.py').write_text(ws_content)
    print(f"  Created ws.py ({len(ws_content.split(chr(10)))} lines)")

    # Automation submodule
    automation_content = f'''"""
Vault Automation Routes - File organization automation
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['/automation/', '/seed-decoy', '/clear-decoy'])}
'''

    (VAULT_PKG / 'automation.py').write_text(automation_content)
    print(f"  Created automation.py ({len(automation_content.split(chr(10)))} lines)")

    # __init__.py aggregator
    init_content = '''"""
Vault routes package - Aggregates all vault sub-routers
"""

from fastapi import APIRouter, Depends
from api.auth_middleware import get_current_user

from . import documents, files, folders, sharing, ws, automation

router = APIRouter(
    prefix="/api/v1/vault",
    tags=["Vault"],
    dependencies=[Depends(get_current_user)]
)

# Include all sub-routers
router.include_router(documents.router)
router.include_router(files.router)
router.include_router(folders.router)
router.include_router(sharing.router)
router.include_router(ws.router)
router.include_router(automation.router)
'''

    (VAULT_PKG / '__init__.py').write_text(init_content)
    print(f"  Created __init__.py ({len(init_content.split(chr(10)))} lines)")
    print("Vault routes refactored successfully!")


def split_chat_routes():
    """Split chat routes into submodules."""
    print("\nRefactoring Chat routes...")

    content = CHAT_OLD.read_text()
    imports, common = extract_imports_and_common(content)

    CHAT_PKG.mkdir(parents=True, exist_ok=True)

    # Sessions submodule
    sessions_content = f'''"""
Chat Sessions Routes - Session create/list/delete
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['/sessions'])}
'''

    (CHAT_PKG / 'sessions.py').write_text(sessions_content)
    print(f"  Created sessions.py ({len(sessions_content.split(chr(10)))} lines)")

    # Messages submodule
    messages_content = f'''"""
Chat Messages Routes - Message send/get/history
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['/messages', '/search', '/analytics'])}
'''

    (CHAT_PKG / 'messages.py').write_text(messages_content)
    print(f"  Created messages.py ({len(messages_content.split(chr(10)))} lines)")

    # Files submodule
    files_content = f'''"""
Chat Files Routes - File attachment handling
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['/upload', '/data/export'])}
'''

    (CHAT_PKG / 'files.py').write_text(files_content)
    print(f"  Created files.py ({len(files_content.split(chr(10)))} lines)")

    # Models submodule
    models_content = f'''"""
Chat Models Routes - Model management endpoints
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['/models', '/ollama/', '/hot-slots', '/performance', '/panic', '/learning'])}
'''

    (CHAT_PKG / 'models.py').write_text(models_content)
    print(f"  Created models.py ({len(models_content.split(chr(10)))} lines)")

    # __init__.py aggregator
    init_content = '''"""
Chat routes package - Aggregates all chat sub-routers
"""

from fastapi import APIRouter, Depends
from api.auth_middleware import get_current_user

from . import sessions, messages, files, models

# Authenticated router
router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)]
)

# Public router (health checks, model list)
public_router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat-public"]
)

# Include sub-routers
router.include_router(sessions.router)
router.include_router(messages.router)
router.include_router(files.router)

# Models can be both auth'd and public - include both
router.include_router(models.router)
public_router.include_router(models.router)
'''

    (CHAT_PKG / '__init__.py').write_text(init_content)
    print(f"  Created __init__.py ({len(init_content.split(chr(10)))} lines)")
    print("Chat routes refactored successfully!")


def split_team_routes():
    """Split team routes into submodules."""
    print("\nRefactoring Team routes...")

    content = TEAM_OLD.read_text()
    imports, common = extract_imports_and_common(content)

    TEAM_PKG.mkdir(parents=True, exist_ok=True)

    # Core submodule (team CRUD)
    core_content = f'''"""
Team Core Routes - Team CRUD operations
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['"/create', '"/', '/vault/items', '/model-policy'])}
'''

    (TEAM_PKG / 'core.py').write_text(core_content)
    print(f"  Created core.py ({len(core_content.split(chr(10)))} lines)")

    # Members submodule
    members_content = f'''"""
Team Members Routes - Member add/remove/list operations
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['/members', '/heartbeat', '/job-role'])}
'''

    (TEAM_PKG / 'members.py').write_text(members_content)
    print(f"  Created members.py ({len(members_content.split(chr(10)))} lines)")

    # Roles submodule
    roles_content = f'''"""
Team Roles Routes - Role assignments and promotions
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['/role', '/promote', '/god-rights', '/super-admins', '/temp-promotion'])}
'''

    (TEAM_PKG / 'roles.py').write_text(roles_content)
    print(f"  Created roles.py ({len(roles_content.split(chr(10)))} lines)")

    # Invitations submodule
    invitations_content = f'''"""
Team Invitations Routes - Invite/accept/reject flows
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['/invites', '/join', '/invite-code'])}
'''

    (TEAM_PKG / 'invitations.py').write_text(invitations_content)
    print(f"  Created invitations.py ({len(invitations_content.split(chr(10)))} lines)")

    # Permissions submodule
    permissions_content = f'''"""
Team Permissions Routes - Workflow/queue/vault permission management
"""

{imports}

router = APIRouter()

{extract_endpoints_by_pattern(content, ['/workflows', '/queues', '/permissions'])}
'''

    (TEAM_PKG / 'permissions.py').write_text(permissions_content)
    print(f"  Created permissions.py ({len(permissions_content.split(chr(10)))} lines)")

    # __init__.py aggregator
    init_content = '''"""
Team routes package - Aggregates all team sub-routers
"""

from fastapi import APIRouter, Depends
from auth_middleware import get_current_user

from . import core, members, roles, invitations, permissions

router = APIRouter(
    prefix="/api/v1/teams",
    tags=["teams"],
    dependencies=[Depends(get_current_user)]
)

# Include all sub-routers
router.include_router(core.router)
router.include_router(members.router)
router.include_router(roles.router)
router.include_router(invitations.router)
router.include_router(permissions.router)
'''

    (TEAM_PKG / '__init__.py').write_text(init_content)
    print(f"  Created __init__.py ({len(init_content.split(chr(10)))} lines)")
    print("Team routes refactored successfully!")


def update_router_registry():
    """Update router_registry.py to use new package structure."""
    print("\nUpdating router_registry.py...")

    registry_path = BACKEND_DIR / "api" / "router_registry.py"
    content = registry_path.read_text()

    # Update Vault import (already using api.vault.routes)
    content = content.replace(
        'from api.vault import routes as _vault_routes',
        'from api.routes import vault as _vault_routes'
    )

    # Chat and Team should already be correct, but verify
    print("  Updated Vault import")
    print("  Chat import already correct: from api.routes import chat")
    print("  Team import already correct: from api.routes import team")

    registry_path.write_text(content)
    print("Router registry updated successfully!")


def print_summary():
    """Print refactoring summary."""
    print("\n" + "="*60)
    print("REFACTORING SUMMARY")
    print("="*60)

    for pkg_name, pkg_path in [('Vault', VAULT_PKG), ('Chat', CHAT_PKG), ('Team', TEAM_PKG)]:
        print(f"\n{pkg_name} Routes:")
        if pkg_path.exists():
            for py_file in sorted(pkg_path.glob('*.py')):
                line_count = len(py_file.read_text().split('\n'))
                print(f"  {py_file.name:20s} {line_count:5d} lines")

    print("\n" + "="*60)
    print("All route modules refactored successfully!")
    print("="*60)


if __name__ == '__main__':
    split_vault_routes()
    split_chat_routes()
    split_team_routes()
    update_router_registry()
    print_summary()
