# ElohimOS Refactoring Guide

**Version:** 1.0
**Last Updated:** 2025-11-13
**Status:** Active

---

## Purpose

This guide provides concrete patterns and conventions for refactoring large monolithic files into modular, maintainable services while maintaining 100% backwards compatibility.

---

## Module Organization

All services should follow this package structure:

```
apps/backend/api/services/{domain}/
├── __init__.py          # Package exports
├── core.py              # CRUD operations (create, read, update, delete)
├── {feature}.py         # Domain-specific feature modules
└── schemas.py           # Data models (Pydantic, TypedDict, etc.)
```

**Examples:**

```
services/vault/
├── __init__.py          # Re-exports for convenience
├── core.py              # CRUD operations
├── permissions.py       # Access checks, role rules, policy evaluation
├── encryption.py        # Key management, encrypt/decrypt
└── sharing.py           # Share/unshare logic, link generation

services/team/
├── __init__.py
├── core.py              # Team CRUD, metadata, settings
├── members.py           # Add/remove members, member queries
├── roles.py             # Role/permission assignments
└── invitations.py       # Create/send/accept/expire invitations

services/chat/
├── __init__.py
├── core.py              # Session CRUD, message storage
├── streaming.py         # SSE handling, token counting
└── files.py             # File uploads, attachments
```

---

## Facade Pattern & Deprecation Strategy

Legacy monolithic files (e.g., `vault_service.py`) are converted to **facades** that re-export from the new modular structure with deprecation warnings.

**Example Facade:**

```python
# apps/backend/api/vault_service.py (reduced to ~200 lines)
"""
Legacy facade for vault operations.

DEPRECATED: This module is deprecated and will be removed in v2.0.
Please import from services.vault.* instead:

    from services.vault.core import create_vault_item
    from services.vault.permissions import check_vault_access
    from services.vault.encryption import encrypt_vault_data
    from services.vault.sharing import share_vault_item
"""
import warnings

# Re-export with deprecation warnings
from services.vault.core import *
from services.vault.permissions import *
from services.vault.encryption import *
from services.vault.sharing import *

warnings.warn(
    "vault_service.py is deprecated. Use services.vault.* modules instead.",
    DeprecationWarning,
    stacklevel=2
)
```

**Migration Timeline:**
- **Now → v1.9**: Both old and new imports work (deprecation warnings)
- **v2.0**: Old imports removed (breaking change)

---

## Router Registry Approach

Centralize router registration in a dedicated module to simplify `main.py`.

**File:** `apps/backend/api/router_registry.py`

**Pattern:**
```python
from fastapi import FastAPI
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

def register_routers(app: FastAPI) -> Tuple[List[str], List[str]]:
    """
    Register all API routers to the FastAPI app.

    Returns:
        Tuple of (services_loaded, services_failed)
    """
    services_loaded = []
    services_failed = []

    # Chat API
    try:
        from api.routes import chat as _chat_routes
        app.include_router(_chat_routes.router)
        services_loaded.append("Chat API")
    except Exception as e:
        services_failed.append("Chat API")
        logger.error("Failed to load chat router", exc_info=True)

    # ... (repeat for all routers)

    return services_loaded, services_failed
```

**Usage (guarded by environment variable):**
```python
# apps/backend/api/main.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if os.getenv("ELOHIMOS_USE_ROUTER_REGISTRY") == "1":
        from .router_registry import register_routers
        services_loaded, services_failed = register_routers(app)
        logger.info(f"Loaded: {services_loaded}")
        if services_failed:
            logger.warning(f"Failed: {services_failed}")

    yield

    # Shutdown
    logger.info("ElohimOS API shutting down...")

app = FastAPI(lifespan=lifespan, title="ElohimOS API")
```

---

## Import Conventions

### ✅ Preferred (New Structure)
```python
from services.vault.core import create_vault_item
from services.team.members import add_team_member
from services.chat.streaming import stream_response
```

### ⚠️ Legacy (Deprecated, but still works via facade)
```python
from vault_service import create_vault_item  # Emits deprecation warning
from team_service import add_team_member     # Emits deprecation warning
```

---

## File Size Targets

**Per-Module Targets:**
- Core modules: < 600 lines
- Feature modules: < 400 lines
- Schema modules: < 300 lines
- Legacy facades: < 200 lines (re-exports only)

**CI Quality Gates:**
1. **GitHub Workflow** (`.github/workflows/file-size-check.yml`): Warns on files > 1200 lines (does not fail CI)
2. **Pre-commit Hook**: Blocks commits of new files > 1200 lines (allowlist exempts existing large files)

**Allowlist:** `.precommit_allowlist_large_files.txt` (to be removed as refactoring progresses)

---

## R1–R7 Migration Checklist

### R1: Vault Service Split
- [ ] Create `services/vault/` package
- [ ] Extract core CRUD → `core.py`
- [ ] Extract permissions → `permissions.py`
- [ ] Extract encryption → `encryption.py`
- [ ] Extract sharing → `sharing.py`
- [ ] Create facade in `vault_service.py`
- [ ] Update internal imports
- [ ] All vault routes behave identically
- [ ] Vault audit logs continue to work
- [ ] File size of `vault_service.py` reduced by >80%

### R2: Team Service Split + De-duplication
- [ ] Analyze duplication between `team_service.py` and `services/team.py`
- [ ] Create `services/team/` package
- [ ] Extract team CRUD → `core.py`
- [ ] Extract member management → `members.py`
- [ ] Extract role logic → `roles.py`
- [ ] Extract invitation logic → `invitations.py`
- [ ] Create facade and remove duplicate `services/team.py`
- [ ] All team routes behave identically
- [ ] File size reductions: `team_service.py` >80%, `services/team.py` eliminated

### R3: Chat Service Split
- [ ] Rename `services/chat.py` → `services/chat/legacy.py`
- [ ] Create `services/chat/` package
- [ ] Extract file operations → `files.py`
- [ ] Extract streaming logic → `streaming.py`
- [ ] Consolidate core session/message logic → `core.py`
- [ ] Create facade in `chat_service.py`
- [ ] All chat endpoints work (streaming, file upload, history)
- [ ] File size of `chat_service.py` reduced by >70%

### R4: main.py Modularization
- [ ] Create `router_registry.py` with registration logic
- [ ] Extract all `app.include_router()` calls to registry
- [ ] Preserve service loading status tracking
- [ ] Update `main.py` to call `register_routers()` (behind env guard)
- [ ] App boots normally with all services loaded
- [ ] File size of `main.py` reduced by >60%

### R5: VaultWorkspace Component Split
- [ ] Create `components/VaultWorkspace/` directory
- [ ] Extract types → `types.ts`
- [ ] Extract file list → `FileList.tsx`
- [ ] Extract preview pane → `FilePreview.tsx`
- [ ] Extract sharing dialog → `ShareDialog.tsx`
- [ ] Extract toolbar → `Toolbar.tsx`
- [ ] Create main composition → `index.tsx`
- [ ] No UI changes or regressions
- [ ] All keyboard shortcuts work

### R6: ProfileSettings Component Split
- [ ] Create `components/ProfileSettings/` directory
- [ ] Extract identity section → `IdentitySection.tsx`
- [ ] Extract security section → `SecuritySection.tsx`
- [ ] Extract appearance section → `AppearanceSection.tsx`
- [ ] Extract notifications section → `NotificationsSection.tsx`
- [ ] Create main composition → `index.tsx`
- [ ] All form validations work

### R7: Automation/Workflow Components Split
- [ ] Create `components/Automation/` directory
- [ ] Extract workflow list → `WorkflowList.tsx`
- [ ] Extract workflow editor → `WorkflowEditor.tsx`
- [ ] Extract trigger config → `TriggerConfig.tsx`
- [ ] Create `components/WorkflowBuilder/` directory
- [ ] Extract canvas → `Canvas.tsx`
- [ ] Extract node palette → `NodePalette.tsx`
- [ ] Extract property inspector → `PropertyInspector.tsx`
- [ ] Drag-and-drop node placement functions correctly

---

## Circular Import Prevention

**Strategy 1: Separate Schema Module**
```python
# services/vault/schemas.py
from pydantic import BaseModel

class VaultItem(BaseModel):
    id: str
    name: str

# services/vault/core.py
from .schemas import VaultItem  # No circular dependency

# services/vault/permissions.py
from .schemas import VaultItem  # No circular dependency
```

**Strategy 2: Late Imports**
```python
def process_vault_item(item_id: str):
    from services.vault.encryption import decrypt_vault_data
    # Use decrypt_vault_data
```

**Strategy 3: Dependency Injection**
```python
def share_vault_item(item_id: str, encryption_service):
    encrypted = encryption_service.encrypt(item_id)
```

---

## Verification Checklist

After each refactor ticket:
- [ ] All existing tests pass unchanged
- [ ] No runtime errors or import failures
- [ ] API endpoints behave identically
- [ ] Audit logs continue to work
- [ ] File size targets met
- [ ] No circular imports (test with fresh import)
- [ ] Deprecation warnings emit correctly

---

**Reference:** `/Users/indiedevhipps/Desktop/ElohimOS-Refactor-Roadmap.md` for detailed acceptance criteria per ticket.
