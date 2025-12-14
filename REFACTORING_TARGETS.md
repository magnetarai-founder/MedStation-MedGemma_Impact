# Refactoring Targets - Monolithic File Analysis

**Date:** 2025-12-13
**Analysis:** Large monolithic files that should be broken into focused modules

---

## 🎯 Executive Summary

**Backend Python:**
- **30 files** over 668 lines
- **Top 10 files:** 783-1,255 lines each
- **Highest priority:** 1,255 lines (chat/core.py), 1,165 lines (main.py)

**Frontend Swift:**
- **30 files** over 332 lines
- **Top 10 files:** 404-829 lines each
- **Highest priority:** 829 lines (EmergencyModeService.swift), 784 lines (AppContext.swift)

**Total refactoring candidates:** ~60 files

---

## 📊 Backend Python - Top Refactoring Targets

### Critical (>1000 lines) - Break Up Immediately

#### 1. **api/services/chat/core.py** - 1,255 lines ⚠️
**Current State:** Monolithic chat service with everything in one file

**Issues:**
- Too many responsibilities (sessions, messages, models, context)
- Hard to test individual components
- Difficult to navigate and maintain

**Recommended Split:**
```
api/services/chat/
├── core.py (200 lines) - Base ChatService class, coordination
├── sessions.py (250 lines) - Session CRUD operations
├── messages.py (250 lines) - Message handling, streaming
├── models.py (200 lines) - Model selection and management
├── context.py (200 lines) - Context window management
└── memory.py (155 lines) - Memory integration
```

**Benefits:**
- Single responsibility per module
- Easier testing (mock individual components)
- Better code navigation
- Clear separation of concerns

---

#### 2. **api/main.py** - 1,165 lines ⚠️
**Current State:** Monolithic main application file

**Issues:**
- Application setup, router registration, middleware all in one file
- Hard to understand startup sequence
- Difficult to add new routers or middleware

**Recommended Split:**
```
api/
├── main.py (100 lines) - Entry point only
├── app_factory.py (200 lines) - FastAPI app creation
├── router_registry.py (Already exists - 544 lines, keep)
├── middleware_config.py (150 lines) - Middleware setup
├── lifespan.py (200 lines) - Startup/shutdown logic
└── config.py (200 lines) - Configuration loading
```

**Benefits:**
- Clear entry point
- Testable components
- Easy to modify startup logic
- Better organization

---

#### 3. **api/services/vault/core.py** - 1,088 lines ⚠️
**Current State:** Monolithic vault service

**Issues:**
- Combines vault items, encryption, permissions
- Complex cryptography mixed with business logic
- Hard to test encryption separately

**Recommended Split:**
```
api/services/vault/
├── core.py (200 lines) - VaultService coordination
├── items.py (250 lines) - CRUD operations for vault items
├── encryption.py (200 lines) - Encryption/decryption logic
├── permissions.py (200 lines) - Permission checking
├── sharing.py (150 lines) - Sharing and collaboration
└── files.py (Already exists - 736 lines, could split further)
```

**Benefits:**
- Isolated cryptography (easier security review)
- Testable encryption without full vault
- Clear permission model
- Better separation of concerns

---

#### 4. **api/permissions_admin.py** - 1,085 lines ⚠️
**Current State:** Duplicate of api/permissions/admin.py (1,040 lines)

**Issues:**
- Two nearly identical files
- Code duplication
- Unclear which is canonical

**Recommended Action:**
```
1. Determine canonical version (likely api/permissions/admin.py)
2. Delete duplicate (api/permissions_admin.py)
3. Update all imports
4. Split remaining file:
   api/permissions/
   ├── admin.py (300 lines) - Admin operations
   ├── roles.py (250 lines) - Role management
   ├── assignments.py (250 lines) - Permission assignments
   └── checks.py (240 lines) - Permission checking
```

**Benefits:**
- No duplication
- Clear permission model
- Easier to maintain
- Better testability

---

#### 5. **api/workflow_service.py** - 1,020 lines ⚠️
**Current State:** Monolithic workflow orchestration

**Issues:**
- Workflow definition, execution, scheduling all mixed
- Hard to add new workflow types
- Difficult to test execution separately

**Recommended Split:**
```
api/services/workflow/
├── service.py (200 lines) - Main WorkflowService
├── definition.py (250 lines) - Workflow schema & validation
├── execution.py (250 lines) - Execution engine
├── scheduler.py (200 lines) - Scheduling logic
└── templates.py (120 lines) - Workflow templates
```

**Benefits:**
- Testable execution engine
- Easy to add workflow types
- Clear scheduling model
- Better code organization

---

### High Priority (800-1000 lines) - Should Refactor

#### 6. **api/services/team/storage.py** - 1,005 lines
**Split into:** `storage.py` (300), `sync.py` (350), `cache.py` (355)

#### 7. **api/chat_memory.py** - 993 lines
**Split into:** `storage.py` (400), `search.py` (300), `embeddings.py` (293)

#### 8. **api/services/workflow_orchestrator.py** - 955 lines
**Split into:** `orchestrator.py` (300), `tasks.py` (350), `scheduler.py` (305)

#### 9. **api/routes/sql_json.py** - 948 lines
**Split into:** `routes.py` (200), `executor.py` (400), `converter.py` (348)

#### 10. **api/agent/engines/codex_engine.py** - 910 lines
**Split into:** `engine.py` (300), `tools.py` (350), `execution.py` (260)

---

### Medium Priority (700-800 lines) - Consider Refactoring

- `api/terminal_api.py` (904 lines)
- `api/code_operations.py` (891 lines)
- `api/metal4_engine.py` (871 lines)
- `api/workflow_storage.py` (853 lines)
- `api/permissions/engine.py` (836 lines)
- `api/offline_mesh_router.py` (832 lines)
- `api/routes/vault/files/metadata.py` (809 lines)
- `api/p2p_chat_router.py` (805 lines)
- `api/services/team/vault.py` (803 lines)
- `api/services/admin_support.py` (783 lines)

---

## 🍎 Frontend Swift - Top Refactoring Targets

### Critical (>700 lines) - Break Up Immediately

#### 1. **EmergencyModeService.swift** - 829 lines ⚠️
**Current State:** Monolithic emergency/panic mode service

**Issues:**
- Emergency procedures, wipe operations, validation all mixed
- Hard to test wipe operations safely
- Complex state management

**Recommended Split:**
```
Services/EmergencyMode/
├── EmergencyModeService.swift (200 lines) - Main service
├── WipeOperations.swift (200 lines) - File/data wipe logic
├── ValidationRules.swift (150 lines) - Validation checks
├── DecoyMode.swift (150 lines) - Decoy mode handling
└── StateManager.swift (129 lines) - State tracking
```

**Benefits:**
- Isolated wipe logic (easier to test safely)
- Clear validation rules
- Better state management
- Testable without risk

---

#### 2. **AppContext.swift** - 784 lines ⚠️
**Current State:** Monolithic app-wide state container

**Issues:**
- Too many responsibilities (models, teams, vault, chat, settings)
- Global state hard to reason about
- Difficult to test components in isolation

**Recommended Split:**
```
Models/AppContext/
├── AppContext.swift (150 lines) - Main container
├── ChatContext.swift (150 lines) - Chat-specific state
├── VaultContext.swift (150 lines) - Vault-specific state
├── TeamContext.swift (150 lines) - Team-specific state
├── ModelContext.swift (150 lines) - Model management state
└── SettingsContext.swift (34 lines) - App settings
```

**Benefits:**
- Focused state management
- Easier testing (isolated contexts)
- Better SwiftUI performance (fewer updates)
- Clear boundaries

---

### High Priority (600-700 lines) - Should Refactor

#### 3. **ContextBundle.swift** - 690 lines
**Current State:** Context aggregation and bundling

**Recommended Split:**
```
Models/Context/
├── ContextBundle.swift (200 lines) - Bundle creation
├── ContextFilters.swift (200 lines) - Filtering logic
├── ContextPriority.swift (150 lines) - Priority scoring
└── ContextCache.swift (140 lines) - Caching layer
```

#### 4. **ChatStore.swift** - 619 lines
**Current State:** Chat state management

**Recommended Split:**
```
Stores/Chat/
├── ChatStore.swift (200 lines) - Main store
├── MessageStore.swift (200 lines) - Message handling
├── SessionStore.swift (150 lines) - Session management
└── StreamStore.swift (69 lines) - Streaming logic
```

---

### Medium Priority (500-600 lines) - Consider Refactoring

- **AppleFMOrchestrator.swift** (544 lines) - Split into engine/scheduler/queue
- **VaultService.swift** (537 lines) - Split into items/encryption/sharing
- **APIClient.swift** (502 lines) - Split into client/auth/error handling
- **TeamChatComponents.swift** (488 lines) - Split into UI components
- **ModelManagerWindow.swift** (466 lines) - Split into tabs/views
- **TeamService.swift** (461 lines) - Split into members/permissions/sync

---

## 📋 Refactoring Priority Matrix

### Immediate Action (Next Sprint)

| File | Lines | Complexity | Impact | Priority |
|------|-------|------------|--------|----------|
| chat/core.py | 1,255 | High | High | 🔴 Critical |
| main.py | 1,165 | High | High | 🔴 Critical |
| vault/core.py | 1,088 | High | High | 🔴 Critical |
| permissions_admin.py (dup) | 1,085 | Medium | Medium | 🔴 Critical |
| EmergencyModeService.swift | 829 | High | High | 🔴 Critical |
| AppContext.swift | 784 | High | High | 🔴 Critical |

### High Priority (This Month)

| File | Lines | Complexity | Impact | Priority |
|------|-------|------------|--------|----------|
| workflow_service.py | 1,020 | High | Medium | 🟡 High |
| team/storage.py | 1,005 | Medium | Medium | 🟡 High |
| chat_memory.py | 993 | Medium | High | 🟡 High |
| workflow_orchestrator.py | 955 | High | Medium | 🟡 High |
| ContextBundle.swift | 690 | Medium | Medium | 🟡 High |
| ChatStore.swift | 619 | Medium | High | 🟡 High |

---

## 🎯 Recommended Refactoring Approach

### Phase 1: Backend Critical Files (Week 1-2)

**Order:**
1. **api/main.py** (1,165 lines)
   - Start here - cleanest split, clear benefits
   - Creates app_factory.py pattern for others to follow

2. **api/permissions_admin.py** duplicate (1,085 lines)
   - Quick win - delete duplicate, consolidate
   - Reduces codebase immediately

3. **api/services/chat/core.py** (1,255 lines)
   - High impact - core service used everywhere
   - Test thoroughly after split

4. **api/services/vault/core.py** (1,088 lines)
   - Security-critical - careful refactoring
   - Isolate cryptography for security review

### Phase 2: Frontend Critical Files (Week 3)

**Order:**
1. **AppContext.swift** (784 lines)
   - Foundation for other refactorings
   - Improves SwiftUI performance

2. **EmergencyModeService.swift** (829 lines)
   - Security-critical - isolate wipe operations
   - Easier to test safely when split

3. **ContextBundle.swift** (690 lines)
   - Complements AppContext refactoring
   - Better performance

### Phase 3: High Priority (Week 4)

**Backend:**
- workflow_service.py (1,020 lines)
- chat_memory.py (993 lines)

**Frontend:**
- ChatStore.swift (619 lines)
- AppleFMOrchestrator.swift (544 lines)

---

## 📐 Refactoring Patterns

### Backend Pattern (Python)

**Before:**
```python
# api/services/monolith.py (1000+ lines)
class MonolithService:
    def operation_a(self): ...
    def operation_b(self): ...
    def operation_c(self): ...
    # ... 50 more methods
```

**After:**
```python
# api/services/monolith/
# __init__.py
from .service import MonolithService

# service.py (200 lines)
class MonolithService:
    def __init__(self):
        self.module_a = ModuleA()
        self.module_b = ModuleB()

# module_a.py (250 lines)
class ModuleA:
    def operation_a(self): ...

# module_b.py (250 lines)
class ModuleB:
    def operation_b(self): ...
```

### Frontend Pattern (Swift)

**Before:**
```swift
// Services/MonolithService.swift (800+ lines)
class MonolithService: ObservableObject {
    // State
    @Published var state1: Type1
    @Published var state2: Type2

    // Operations
    func operation1() { ... }
    func operation2() { ... }
    // ... 30 more methods
}
```

**After:**
```swift
// Services/Monolith/
// MonolithService.swift (150 lines)
class MonolithService: ObservableObject {
    private let module1 = Module1()
    private let module2 = Module2()

    func coordinatedOperation() {
        module1.operation1()
        module2.operation2()
    }
}

// Module1.swift (200 lines)
class Module1 {
    func operation1() { ... }
}

// Module2.swift (200 lines)
class Module2 {
    func operation2() { ... }
}
```

---

## ✅ Refactoring Checklist

For each file being refactored:

### Planning
- [ ] Identify logical module boundaries
- [ ] Map dependencies between modules
- [ ] Design new file structure
- [ ] Plan migration path

### Execution
- [ ] Create new module files
- [ ] Move code to focused modules
- [ ] Update imports
- [ ] Test after each module move

### Validation
- [ ] All tests pass
- [ ] No regressions in functionality
- [ ] Performance maintained or improved
- [ ] Code coverage maintained

### Documentation
- [ ] Update README if needed
- [ ] Add module-level docstrings
- [ ] Update architecture docs

---

## 📊 Expected Benefits

### Code Quality
- **Reduced complexity:** 1000+ line files → 200-300 line focused modules
- **Better testability:** Test modules in isolation
- **Easier navigation:** Find code faster
- **Clear responsibilities:** Single purpose per module

### Developer Experience
- **Faster onboarding:** Smaller files easier to understand
- **Parallel development:** Multiple devs can work on different modules
- **Better IDE performance:** Faster autocomplete, fewer hangs
- **Easier code review:** Smaller, focused PRs

### Maintainability
- **Easier debugging:** Smaller surface area
- **Safer refactoring:** Change one module at a time
- **Better reusability:** Extract common functionality
- **Clearer architecture:** Visible module boundaries

---

## 🚀 Next Steps

1. **Review this document** - Validate priorities and approach
2. **Start with api/main.py** - Easiest high-impact refactoring
3. **Create refactoring branch** - Work safely
4. **Test thoroughly** - Ensure no regressions
5. **Migrate incrementally** - One file at a time

---

**Total Files to Refactor:** ~60 files
**Total Lines to Reorganize:** ~40,000 lines
**Estimated Effort:** 4-6 weeks (1-2 files per day)
**Expected Outcome:** More maintainable, testable, and scalable codebase

**Status:** ✅ Analysis complete, ready to execute
**Date:** 2025-12-13
