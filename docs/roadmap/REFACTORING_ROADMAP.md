# ElohimOS Modularization Refactor Roadmap

**Version:** 1.0
**Date:** 2025-11-14
**Status:** Updated — Vault + Router Registry complete; Team partial; Chat pending

---

## Executive Summary

This roadmap addresses technical debt in ElohimOS by progressively modularizing large monolithic files (5k+ lines) into cohesive, maintainable modules while maintaining 100% backwards compatibility and zero runtime disruption.

**Key Metrics:**
- **Files to Refactor:** 8 backend, 4 frontend
- **Total Lines to Modularize:** ~25,000+ lines
- **Estimated Effort:** 40-60 hours (8-12 tickets)
- **Risk Level:** Low (facade pattern ensures compatibility)

---

## Phase 0: Groundwork (Compatibility + Safety)

### Guiding Principles

1. **Keep public API/route behavior identical** - No breaking changes
2. **Introduce new service packages alongside legacy files** - Parallel structure
3. **Add thin proxies in legacy files** - Facade pattern with deprecation warnings
4. **Refactor in small, verifiable steps** - Smoke test after each ticket
5. **Maintain test coverage** - Ensure existing tests pass without modification

### Safety Measures

- ✅ Incremental PRs per ticket (1 ticket = 1 PR)
- ✅ Backwards compatibility via facade modules
- ✅ Deprecation warnings for old import paths
- ✅ Circular import prevention (separate schemas/types)
- ✅ Verification checklist after each ticket

---

## Priority 1: Critical (5k-line files)

### 🔴 Ticket R1: Vault Service Split

**File:** `apps/backend/api/vault_service.py` (5,356 lines)

**Summary:** Break up vault service into cohesive modules with a compatibility facade.

**New Structure:**
```
apps/backend/api/services/vault/
├── __init__.py          # Re-exports for convenience
├── core.py              # CRUD operations (create, read, update, delete)
├── permissions.py       # Access checks, role rules, policy evaluation
├── encryption.py        # Key management, encrypt/decrypt
└── sharing.py           # Share/unshare logic, link generation, permissions propagation
```

**Facade File:**
```python
# apps/backend/api/vault_service.py (reduced to ~200 lines)
"""
Legacy facade for vault operations.
DEPRECATED: Import from services.vault.* instead.
"""
import warnings
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

**Implementation Steps:**

1. **Phase 1.1:** Create `services/vault/` directory structure
2. **Phase 1.2:** Extract and move core CRUD functions to `core.py`
3. **Phase 1.3:** Extract permission logic to `permissions.py`
4. **Phase 1.4:** Extract encryption functions to `encryption.py`
5. **Phase 1.5:** Extract sharing logic to `sharing.py`
6. **Phase 1.6:** Create facade with re-exports and deprecation warnings
7. **Phase 1.7:** Update internal imports progressively

**Acceptance Criteria:**

- [x] All vault routes behave identically (GET/POST/PUT/DELETE)
- [x] No runtime errors or import failures
- [x] New modules import without circular dependencies
- [x] Vault audit logs continue to work
- [x] File size of `vault_service.py` reduced by >80% (split across services/vault/*)
- [x] All vault unit tests pass unchanged

**File Touchpoints:**
- `apps/backend/api/vault_service.py` (split + facade)
- `apps/backend/api/services/vault/*` (new)
- `apps/backend/api/routes/vault*.py` (verify imports)

**Estimated Effort:** 8-12 hours

---

### 🔴 Ticket R2: Team Service Split + De-duplication

**Files:**
- `apps/backend/api/team_service.py` (5,145 lines)
- `apps/backend/api/services/team.py` (2,911 lines - DUPLICATE)

**Summary:** Split team service into modules and consolidate duplication.

**New Structure:**
```
apps/backend/api/services/team/
├── __init__.py          # Re-exports
├── core.py              # Team CRUD, metadata, settings
├── members.py           # Add/remove members, member queries
├── roles.py             # Role/permission assignments, role hierarchy
└── invitations.py       # Create/send/accept/expire invitations
```

**Facade File:**
```python
# apps/backend/api/team_service.py (reduced to ~200 lines)
"""
Legacy facade for team operations.
DEPRECATED: Import from services.team.* instead.
"""
import warnings
from services.team.core import *
from services.team.members import *
from services.team.roles import *
from services.team.invitations import *

warnings.warn(
    "team_service.py is deprecated. Use services.team.* modules instead.",
    DeprecationWarning,
    stacklevel=2
)
```

**Implementation Steps:**

1. **Phase 2.1:** Analyze duplication between `team_service.py` and `services/team.py`
2. **Phase 2.2:** Create `services/team/` directory structure
3. **Phase 2.3:** Extract team CRUD to `core.py` (consolidate duplicates)
4. **Phase 2.4:** Extract member management to `members.py`
5. **Phase 2.5:** Extract role logic to `roles.py`
6. **Phase 2.6:** Extract invitation logic to `invitations.py`
7. **Phase 2.7:** Create facade and remove duplicate `services/team.py`
8. **Phase 2.8:** Update route and background job imports

**Acceptance Criteria:**

- [ ] All team routes behave identically
- [ ] Team invitation flow works end-to-end
- [ ] Role assignment and permission checks function correctly
- [ ] Background jobs (cleanup, reminders) continue to work
- [ ] No duplicate code paths between old files
- [ ] File size reductions: `team_service.py` >80%, `services/team.py` eliminated
- [ ] All team unit tests pass unchanged

**File Touchpoints:**
- `apps/backend/api/team_service.py` (split + facade)
- `apps/backend/api/services/team.py` (remove/consolidate)
- `apps/backend/api/services/team/*` (new)
- `apps/backend/api/routes/team*.py` (verify imports)
- `apps/backend/api/background_jobs.py` (update team-related jobs)

**Estimated Effort:** 10-14 hours

---

## Priority 2: High (2k-3k line files)

### 🟡 Ticket R3: Chat Service Split

**File:** `apps/backend/api/chat_service.py` (2,231 lines)

**Summary:** Break chat service into streaming, file handling, and core session management.

**New Structure:**
```
apps/backend/api/services/chat/
├── __init__.py          # Re-exports (already exists, extend it)
├── core.py              # Session CRUD, message storage, memory management
├── streaming.py         # SSE handling, token counting, streaming logic
└── files.py             # File uploads, attachments, document processing
```

**Note:** `services/chat.py` already exists (1,751 lines) - extend it into a package.

**Facade File:**
```python
# apps/backend/api/chat_service.py (reduced to ~300 lines)
"""
Legacy facade for chat operations.
DEPRECATED: Import from services.chat.* instead.
"""
import warnings
from services.chat.core import *
from services.chat.streaming import *
from services.chat.files import *

warnings.warn(
    "chat_service.py is deprecated. Use services.chat.* modules instead.",
    DeprecationWarning,
    stacklevel=2
)
```

**Implementation Steps:**

1. **Phase 3.1:** Rename `services/chat.py` → `services/chat/legacy.py`
2. **Phase 3.2:** Create `services/chat/__init__.py` with package structure
3. **Phase 3.3:** Extract file operations to `files.py`
4. **Phase 3.4:** Extract streaming logic to `streaming.py`
5. **Phase 3.5:** Consolidate core session/message logic in `core.py`
6. **Phase 3.6:** Create facade in `chat_service.py`
7. **Phase 3.7:** Update route imports progressively

**Acceptance Criteria:**

- [ ] All chat endpoints work (session creation, messaging, streaming)
- [ ] File upload and attachment handling functions correctly
- [ ] SSE streaming maintains proper format and timing
- [ ] Message history and context retrieval work
- [ ] No degradation in streaming performance
- [ ] File size of `chat_service.py` reduced by >70%
- [ ] All chat unit tests pass unchanged

**File Touchpoints:**
- `apps/backend/api/chat_service.py` (split + facade)
- `apps/backend/api/services/chat.py` → `services/chat/legacy.py`
- `apps/backend/api/services/chat/*` (new)
- `apps/backend/api/routes/chat.py` (verify imports)

**Estimated Effort:** 8-10 hours

---

### 🟡 Ticket R4: main.py Modularization

**File:** `apps/backend/api/main.py` (2,192 lines)

**Summary:** Extract router registration to dedicated module to simplify main.py.

**New Structure:**
```
apps/backend/api/
├── main.py              # App initialization, lifespan, middleware (~500 lines)
└── router_registry.py   # All router registration logic (new)
```

**Implementation:**

```python
# apps/backend/api/router_registry.py
"""
Centralized router registration for FastAPI app.
Maintains service loading status and error handling.
"""
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

    # Vault API
    try:
        from api.routes import vault as _vault_routes
        app.include_router(_vault_routes.router)
        services_loaded.append("Vault API")
    except Exception as e:
        services_failed.append("Vault API")
        logger.error("Failed to load vault router", exc_info=True)

    # ... (all other routers)

    return services_loaded, services_failed
```

**Simplified main.py:**
```python
# apps/backend/api/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from router_registry import register_routers

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("ElohimOS API starting...")
    services_loaded, services_failed = register_routers(app)
    logger.info(f"Loaded: {services_loaded}")
    if services_failed:
        logger.warning(f"Failed: {services_failed}")

    yield

    # Shutdown
    logger.info("ElohimOS API shutting down...")

app = FastAPI(lifespan=lifespan, title="ElohimOS API")
```

**Implementation Steps:**

1. **Phase 4.1:** Create `router_registry.py` with router registration logic
2. **Phase 4.2:** Extract all `app.include_router()` calls to registry
3. **Phase 4.3:** Preserve service loading status tracking
4. **Phase 4.4:** Update `main.py` to call `register_routers()`
5. **Phase 4.5:** Verify lifespan events and middleware remain intact

**Acceptance Criteria:**

- [x] Same set/order of routers mounted
- [x] App boots normally with all services loaded
- [x] Service status logging works (loaded/failed)
- [x] Lifespan events (startup/shutdown) function correctly
- [x] Background jobs start/stop as expected
- [x] Middleware chain remains intact
- [x] File size of `main.py` reduced by >60%

**File Touchpoints:**
- `apps/backend/api/main.py` (simplify)
- `apps/backend/api/router_registry.py` (new)
- Verify all routers import and mount correctly

**Estimated Effort:** 4-6 hours

---

## Priority 3: Medium (Frontend 1k-4k line files)

### 🟠 Ticket R5: VaultWorkspace Component Split

**File:** `apps/frontend/src/components/VaultWorkspace.tsx` (4,119 lines)

**Summary:** Break monolithic component into subcomponents for maintainability.

**New Structure:**
```
apps/frontend/src/components/VaultWorkspace/
├── index.tsx            # Main composition + layout (~300 lines)
├── FileList.tsx         # File listing with virtualization
├── FilePreview.tsx      # Preview pane (PDF, images, markdown, code)
├── ShareDialog.tsx      # Sharing UI (permissions, links, members)
├── Toolbar.tsx          # Action toolbar (upload, new folder, search)
├── FileContextMenu.tsx  # Right-click context menu
└── types.ts             # Shared types and interfaces
```

**Implementation Steps:**

1. **Phase 5.1:** Create directory structure
2. **Phase 5.2:** Extract types and interfaces to `types.ts`
3. **Phase 5.3:** Extract file list component to `FileList.tsx`
4. **Phase 5.4:** Extract preview pane to `FilePreview.tsx`
5. **Phase 5.5:** Extract sharing dialog to `ShareDialog.tsx`
6. **Phase 5.6:** Extract toolbar to `Toolbar.tsx`
7. **Phase 5.7:** Create main `index.tsx` composition
8. **Phase 5.8:** Update imports throughout app

**Acceptance Criteria:**

- [ ] No UI changes or regressions
- [ ] Same behavior and performance
- [ ] All keyboard shortcuts work
- [ ] Drag-and-drop upload functions correctly
- [ ] File preview renders all supported formats
- [ ] Sharing flow works end-to-end
- [ ] Props appropriately typed with TypeScript
- [ ] Component tree maintains proper state management

**File Touchpoints:**
- `apps/frontend/src/components/VaultWorkspace.tsx` (remove)
- `apps/frontend/src/components/VaultWorkspace/*` (new)
- Update all imports of `VaultWorkspace`

**Estimated Effort:** 8-10 hours

---

### 🟠 Ticket R6: ProfileSettings Component Split

**File:** `apps/frontend/src/components/ProfileSettings.tsx` (982 lines)

**Summary:** Break profile settings into section-based subcomponents.

**New Structure:**
```
apps/frontend/src/components/ProfileSettings/
├── index.tsx            # Main layout + section navigation
├── IdentitySection.tsx  # Name, email, avatar
├── SecuritySection.tsx  # Password, 2FA, sessions
├── AppearanceSection.tsx # Theme, language, preferences
└── NotificationsSection.tsx # Notification preferences
```

**Implementation Steps:**

1. **Phase 6.1:** Create directory structure
2. **Phase 6.2:** Extract identity section
3. **Phase 6.3:** Extract security section
4. **Phase 6.4:** Extract appearance section
5. **Phase 6.5:** Extract notifications section
6. **Phase 6.6:** Create main composition with navigation
7. **Phase 6.7:** Update imports

**Acceptance Criteria:**

- [ ] No UI changes
- [ ] All form validations work
- [ ] Settings save correctly to backend
- [ ] Section navigation functions properly
- [ ] Keyboard accessibility maintained

**File Touchpoints:**
- `apps/frontend/src/components/ProfileSettings.tsx` (remove)
- `apps/frontend/src/components/ProfileSettings/*` (new)

**Estimated Effort:** 4-6 hours

---

### 🟠 Ticket R7: Automation/Workflow Components Split

**Files:**
- `AutomationTab.tsx` (902 lines)
- `WorkflowBuilder.tsx` (893 lines)

**Summary:** Modularize automation and workflow UI components.

**New Structure:**
```
apps/frontend/src/components/Automation/
├── index.tsx            # Main automation tab layout
├── WorkflowList.tsx     # List of workflows
├── WorkflowEditor.tsx   # Workflow editing panel
└── TriggerConfig.tsx    # Trigger configuration

apps/frontend/src/components/WorkflowBuilder/
├── index.tsx            # Main builder composition
├── Canvas.tsx           # Visual workflow canvas
├── NodePalette.tsx      # Available node types
├── PropertyInspector.tsx # Node property editor
└── ConnectionManager.tsx # Edge/connection logic
```

**Implementation Steps:**

Similar to R5/R6 - extract sections into focused subcomponents.

**Acceptance Criteria:**

- [ ] Workflow creation/editing works
- [ ] Drag-and-drop node placement functions
- [ ] Node connections render correctly
- [ ] Property editing updates workflow
- [ ] No performance degradation

**File Touchpoints:**
- `apps/frontend/src/components/AutomationTab.tsx` (remove)
- `apps/frontend/src/components/Automation/*` (new)
- `apps/frontend/src/components/WorkflowBuilder.tsx` (remove)
- `apps/frontend/src/components/WorkflowBuilder/*` (new)

**Estimated Effort:** 10-12 hours

---

## Risk Mitigation & Process

### Incremental PR Strategy

**Per-Ticket Process:**

1. **Create feature branch:** `refactor/ticket-r{N}-{description}`
2. **Implement changes** following ticket steps
3. **Run verification checklist** (see below)
4. **Create PR** with detailed description
5. **Review + merge** to main
6. **Deploy to staging** and smoke test
7. **Monitor logs** for deprecation warnings

**PR Template:**
```markdown
## Refactor Ticket: R{N} - {Title}

### Changes
- [ ] Created new module structure
- [ ] Added facade with deprecation warnings
- [ ] Updated internal imports
- [ ] All tests pass

### Verification
- [ ] Smoke tested critical flows
- [ ] No circular imports
- [ ] No runtime errors
- [ ] Logs clean (no unexpected warnings)

### File Size Reductions
- Before: {X} lines
- After: {Y} lines
- Reduction: {Z}%

### Breaking Changes
None - maintains backwards compatibility via facade.
```

### Verification Checklist (Run After Each Ticket)

**Backend Verification:**

```bash
# 1. Start server
cd apps/backend
python3 -m uvicorn api.main:app --reload

# 2. Check startup logs
# - All services should load
# - Check for deprecation warnings
# - No import errors

# 3. Test core flows
# Vault:
curl -X GET http://localhost:8000/api/v1/vault/files
curl -X POST http://localhost:8000/api/v1/vault/files -d '{...}'

# Team:
curl -X GET http://localhost:8000/api/v1/teams
curl -X POST http://localhost:8000/api/v1/teams/{id}/members

# Chat:
curl -X POST http://localhost:8000/api/v1/chat/sessions
curl -X POST http://localhost:8000/api/v1/chat/sessions/{id}/messages

# 4. Check audit logs
# - Vault operations logged correctly
# - Team changes logged
# - Chat sessions tracked

# 5. Run tests
pytest apps/backend/tests/
```

**Frontend Verification:**

```bash
# 1. Build
cd apps/frontend
npm run build

# 2. Start dev server
npm run dev

# 3. Visual smoke tests
# - Navigate to each affected component
# - Verify UI renders correctly
# - Test interactions (clicks, forms, drag-drop)
# - Check console for errors

# 4. Test user flows
# - Vault: upload file, preview, share
# - Team: create team, invite member, change role
# - Chat: start session, send message, upload file
# - Automation: create workflow, add nodes, save

# 5. Check bundle size
npm run build
# Verify no significant size increase
```

### Backwards Compatibility Strategy

**Facade Pattern:**
```python
# Example: vault_service.py (facade)
"""
Legacy vault service facade.

DEPRECATED: This module is deprecated and will be removed in v2.0.
Please import from services.vault.* instead:

    from services.vault.core import create_vault_item
    from services.vault.permissions import check_vault_access
    from services.vault.encryption import encrypt_vault_data
    from services.vault.sharing import share_vault_item
"""
import warnings
import functools

def deprecated(new_path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated. Import from {new_path} instead.",
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Re-export with deprecation warnings
from services.vault.core import (
    create_vault_item as _create_vault_item,
    read_vault_item as _read_vault_item,
    # ...
)

@deprecated("services.vault.core")
def create_vault_item(*args, **kwargs):
    return _create_vault_item(*args, **kwargs)

@deprecated("services.vault.core")
def read_vault_item(*args, **kwargs):
    return _read_vault_item(*args, **kwargs)

# ... etc
```

**Gradual Import Migration:**
```python
# Phase 1: Old imports still work (via facade)
from api.vault_service import create_vault_item  # ⚠️ Deprecation warning

# Phase 2: Update to new imports
from api.services.vault.core import create_vault_item  # ✅ Preferred

# Phase 3: Remove facade (v2.0)
# Old imports break, forcing migration
```

### Circular Import Prevention

**Strategy 1: Separate Schema/Types Module**
```python
# services/vault/schemas.py
from pydantic import BaseModel

class VaultItem(BaseModel):
    id: str
    name: str
    # ...

# services/vault/core.py
from .schemas import VaultItem  # No circular dependency

# services/vault/permissions.py
from .schemas import VaultItem  # No circular dependency
```

**Strategy 2: Late Imports**
```python
# Use late imports for heavy dependencies
def process_vault_item(item_id: str):
    from services.vault.encryption import decrypt_vault_data
    # ... use decrypt_vault_data
```

**Strategy 3: Dependency Injection**
```python
# Pass dependencies explicitly
def share_vault_item(item_id: str, encryption_service):
    encrypted = encryption_service.encrypt(item_id)
    # ...
```

---

## Post-Refactor Improvements (Nice-to-Have)

### 1. Enhanced Deprecation Warnings

```python
# More informative warnings
import warnings
import inspect

def emit_deprecation_warning(old_module, new_module, func_name):
    caller_frame = inspect.stack()[2]
    caller_file = caller_frame.filename
    caller_line = caller_frame.lineno

    warnings.warn(
        f"\n{'='*70}\n"
        f"DEPRECATION WARNING\n"
        f"{'='*70}\n"
        f"Function: {func_name}\n"
        f"Old Import: from {old_module} import {func_name}\n"
        f"New Import: from {new_module} import {func_name}\n"
        f"Called From: {caller_file}:{caller_line}\n"
        f"{'='*70}\n",
        DeprecationWarning,
        stacklevel=3
    )
```

### 2. Smoke Test Suite

```python
# tests/smoke/test_refactored_modules.py
"""
Smoke tests to verify refactored modules import correctly
and have no circular dependencies.
"""
import pytest

def test_vault_modules_importable():
    """Verify all vault modules can be imported"""
    from services.vault import core, permissions, encryption, sharing
    assert core is not None
    assert permissions is not None
    assert encryption is not None
    assert sharing is not None

def test_team_modules_importable():
    """Verify all team modules can be imported"""
    from services.team import core, members, roles, invitations
    assert core is not None
    assert members is not None
    assert roles is not None
    assert invitations is not None

def test_chat_modules_importable():
    """Verify all chat modules can be imported"""
    from services.chat import core, streaming, files
    assert core is not None
    assert streaming is not None
    assert files is not None

def test_no_circular_imports():
    """Ensure no circular import errors"""
    import sys
    import importlib

    modules = [
        'services.vault.core',
        'services.vault.permissions',
        'services.team.core',
        'services.team.members',
        'services.chat.core',
    ]

    for module_name in modules:
        # Clear module cache
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Import should succeed without errors
        module = importlib.import_module(module_name)
        assert module is not None
```

### 3. CI Linting for File Size

**.github/workflows/lint.yml**
```yaml
name: Code Quality Checks

on: [push, pull_request]

jobs:
  check-file-sizes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check for oversized files
        run: |
          # Find files larger than 1200 lines
          oversized=$(find apps/backend/api -name "*.py" -exec wc -l {} + | \
                     awk '$1 > 1200 {print $2 " (" $1 " lines)"}')

          if [ -n "$oversized" ]; then
            echo "⚠️  Warning: Large files detected:"
            echo "$oversized"
            echo ""
            echo "Consider refactoring files larger than 1200 lines."
            exit 1
          fi

          echo "✅ All files are appropriately sized"
```

**pre-commit hook** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: local
    hooks:
      - id: check-file-size
        name: Check file size
        entry: bash -c 'if [ $(wc -l < $1) -gt 1200 ]; then echo "File too large (>1200 lines): $1"; exit 1; fi' --
        language: system
        files: \.(py|tsx?)$
```

### 4. Documentation Updates

**docs/architecture/refactoring-guide.md**
```markdown
# Module Organization Guide

## Service Layer Structure

All services should follow this pattern:

```
services/{domain}/
├── __init__.py          # Package exports
├── core.py              # CRUD operations
├── {feature}.py         # Domain-specific features
└── schemas.py           # Data models
```

## Import Conventions

✅ **Preferred:**
```python
from services.vault.core import create_vault_item
from services.team.members import add_team_member
```

❌ **Deprecated (use new structure):**
```python
from vault_service import create_vault_item  # Legacy facade
from team_service import add_team_member     # Legacy facade
```

## Adding New Services

1. Create service package: `services/{domain}/`
2. Add `core.py` with CRUD operations
3. Add domain-specific modules as needed
4. Export public API in `__init__.py`
5. Register routes in `router_registry.py`
```

---

## Success Metrics

### Quantitative Goals

| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| Largest backend file | 5,356 lines | <1,200 lines | P1 |
| Largest frontend file | 4,119 lines | <800 lines | P3 |
| Files >2,000 lines | 8 files | 0 files | P1-P2 |
| Circular imports | Unknown | 0 | All |
| Module import time | Baseline | <10% increase | All |
| Test coverage | Current | Maintain | All |

### Qualitative Goals

- ✅ Single Responsibility: Each module has one clear purpose
- ✅ Ease of Navigation: Developers can find code quickly
- ✅ Test Isolation: Modules can be tested independently
- ✅ Parallel Development: Multiple developers can work without conflicts
- ✅ Onboarding Speed: New developers understand structure faster

---

## Timeline & Prioritization

### Sprint-Based Approach

**Sprint 1 (Week 1-2): Critical Files**
- ✅ Ticket R1: Vault Service Split (8-12 hours)
- ✅ Ticket R2: Team Service Split (10-14 hours)
- **Total:** ~20 hours

**Sprint 2 (Week 3-4): High Priority Backend**
- ✅ Ticket R3: Chat Service Split (8-10 hours)
- ✅ Ticket R4: main.py Modularization (4-6 hours)
- **Total:** ~14 hours

**Sprint 3 (Week 5-6): Frontend Refactoring**
- ✅ Ticket R5: VaultWorkspace Split (8-10 hours)
- ✅ Ticket R6: ProfileSettings Split (4-6 hours)
- **Total:** ~14 hours

**Sprint 4 (Week 7-8): Remaining Frontend + Polish**
- ✅ Ticket R7: Automation/Workflow Split (10-12 hours)
- ✅ Post-refactor improvements (smoke tests, docs)
- **Total:** ~14 hours

**Total Estimated Effort:** 60-70 hours (1.5-2 months at 2 sprints/month)

### Parallel Work Strategy

If multiple developers:
- **Backend Team:** R1, R2, R3, R4 (can work in parallel after R1)
- **Frontend Team:** R5, R6, R7 (can work in parallel)
- **DevOps/QA:** CI setup, smoke tests (parallel to all)

---

## Rollback Strategy

If a ticket causes issues:

1. **Immediate:** Revert the PR/commit
2. **Analyze:** Review logs and error traces
3. **Fix Forward:** Create hotfix PR with targeted fix
4. **Re-test:** Run full verification checklist
5. **Re-deploy:** Merge when stable

**Rollback Commands:**
```bash
# Revert last commit
git revert HEAD

# Revert specific PR merge
git revert -m 1 <merge-commit-hash>

# Deploy previous version
git checkout <previous-tag>
docker-compose up -d
```

---

## Communication Plan

### Stakeholder Updates

**Weekly Status Report:**
```markdown
## Refactoring Progress - Week X

### Completed This Week
- ✅ Ticket R1: Vault Service Split
  - Reduced from 5,356 → 1,200 lines (77% reduction)
  - All vault routes tested and working
  - Zero runtime errors

### In Progress
- 🔄 Ticket R2: Team Service Split (60% complete)
  - Core module extracted
  - Members module in review

### Blockers
- None

### Next Week
- Complete R2
- Begin R3 (Chat Service)
```

### Developer Notifications

**Announce deprecations:**
```markdown
# 📢 Announcement: Vault Service Refactoring

Hello team,

We've refactored the vault service for better maintainability.

**What changed:**
- `vault_service.py` is now deprecated
- New modular structure: `services/vault/*`

**Action required:**
- Update imports in your feature branches:
  ```python
  # Old (still works, but deprecated)
  from vault_service import create_vault_item

  # New (preferred)
  from services.vault.core import create_vault_item
  ```

**Timeline:**
- Now → v1.9: Both work (deprecation warnings)
- v2.0: Old imports removed

**Questions?** Ask in #backend-refactoring

Thanks!
```

---

## Appendix: File Size Analysis

### Current State (Before Refactoring)

**Backend (Top 10):**
1. vault_service.py - 5,356 lines 🔴
2. team_service.py - 5,145 lines 🔴
3. services/team.py - 2,911 lines 🟡
4. chat_service.py - 2,231 lines 🟡
5. main.py - 2,192 lines 🟡
6. services/chat.py - 1,751 lines 🟡
7. routes/team.py - 1,442 lines 🟡
8. routes/chat.py - 1,355 lines 🟡
9. template_library_full.py - 1,676 lines 🟡
10. core_nlp_templates.py - 1,183 lines 🟠

**Frontend (Top 10):**
1. VaultWorkspace.tsx - 4,119 lines 🔴
2. ProfileSettings.tsx - 982 lines 🟡
3. AutomationTab.tsx - 902 lines 🟡
4. WorkflowBuilder.tsx - 893 lines 🟡
5. settings/SettingsTab.tsx - 862 lines 🟠
6. ProjectLibraryModal.tsx - 798 lines 🟠
7. ProfileSettingsModal.tsx - 773 lines 🟠
8. LibraryModal.tsx - 726 lines 🟠
9. TeamChatWindow.tsx - 720 lines 🟠
10. DocumentEditor.tsx - 660 lines 🟠

### Target State (After Refactoring)

**Expected Reductions:**

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| vault_service.py | 5,356 | ~800 | 85% |
| team_service.py | 5,145 | ~800 | 84% |
| services/team.py | 2,911 | 0 (merged) | 100% |
| chat_service.py | 2,231 | ~600 | 73% |
| main.py | 2,192 | ~500 | 77% |
| VaultWorkspace.tsx | 4,119 | ~300 | 93% |
| AutomationTab.tsx | 902 | ~200 | 78% |
| WorkflowBuilder.tsx | 893 | ~200 | 78% |

**New Module Sizes (Target):**

All new modules should be <600 lines:
- `services/vault/core.py` - ~400 lines
- `services/vault/permissions.py` - ~300 lines
- `services/vault/encryption.py` - ~250 lines
- `services/vault/sharing.py` - ~350 lines
- (Similar for team, chat)

---

## Getting Started

### For Implementers

1. **Read this roadmap fully** - Understand the approach
2. **Set up development environment:**
   ```bash
   git checkout -b refactor/ticket-r1-vault-split
   cd apps/backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Pick a ticket** - Start with R1 or R2 (highest impact)
4. **Follow the steps** - Implement incrementally
5. **Run verification** - Use the checklist
6. **Create PR** - Use the template
7. **Deploy to staging** - Smoke test before production

### For Reviewers

**Review Checklist:**

- [ ] Code follows new module structure
- [ ] Facade includes deprecation warnings
- [ ] No circular imports introduced
- [ ] Tests pass (run `pytest`)
- [ ] Smoke test results provided
- [ ] File size reductions meet targets
- [ ] Breaking changes documented (should be none)
- [ ] PR description complete

---

## FAQ

**Q: Will this break existing deployments?**
A: No. The facade pattern ensures 100% backwards compatibility. Old imports continue to work.

**Q: When will old imports stop working?**
A: Not until v2.0 (TBD). You'll have at least one full release cycle to migrate.

**Q: Do I need to update my feature branch?**
A: Eventually, yes. But the facade means your code will work without changes initially.

**Q: What if I find a circular import?**
A: Extract shared types to a separate `schemas.py` module, or use late imports inside functions.

**Q: Can I work on multiple tickets at once?**
A: Not recommended. Complete and merge one ticket before starting the next to avoid conflicts.

**Q: How do I handle merge conflicts during refactoring?**
A: Rebase frequently. If conflicts arise, the facade makes it easy - just add the function to the facade.

**Q: What if tests fail after refactoring?**
A: Check imports first. Then verify the logic wasn't accidentally changed. Rollback if needed.

---

## Conclusion

This refactoring plan systematically addresses the technical debt in ElohimOS while maintaining zero downtime and backwards compatibility. By following the incremental, ticket-based approach, we can:

- ✅ Reduce largest files by 70-90%
- ✅ Improve code maintainability and readability
- ✅ Enable parallel development without conflicts
- ✅ Prevent circular imports and dependency issues
- ✅ Maintain test coverage and system stability

**Let's build a more maintainable, scalable codebase together!** 🚀

---

**Document Version:** 1.0
**Last Updated:** 2025-11-13
**Maintained By:** ElohimOS Core Team
**Questions?** Open an issue or ask in #backend-refactoring
