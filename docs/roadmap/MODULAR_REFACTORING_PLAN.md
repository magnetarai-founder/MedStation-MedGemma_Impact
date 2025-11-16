# ElohimOS Modular Refactoring Plan

**Created:** 2025-11-16
**Status:** Planning Phase
**Team:** Claude, User, Codex
**Priority:** High - Foundation for future scalability

---

## Executive Summary

This document outlines a comprehensive plan to refactor all large files in the ElohimOS codebase into smaller, more modular components. This refactoring will improve:

- **Maintainability**: Easier to understand and modify individual modules
- **Testability**: Smaller units are easier to test in isolation
- **Collaboration**: Multiple developers can work on different modules without conflicts
- **Performance**: Better code splitting and lazy loading opportunities
- **Onboarding**: New developers can understand individual modules faster

---

## Large Files Analysis

### Backend Files (Threshold: >1000 lines)

#### Critical Priority (>2000 lines)

| File | Lines | Current Responsibility | Refactoring Complexity |
|------|-------|------------------------|------------------------|
| `api/services/team/core.py` | 2,872 | Team collaboration services | HIGH |
| `api/services/vault/core.py` | 2,780 | Encrypted vault operations | HIGH |

#### High Priority (1500-2000 lines)

| File | Lines | Current Responsibility | Refactoring Complexity |
|------|-------|------------------------|------------------------|
| `api/main.py` | 1,920 | FastAPI app + all route registration | MEDIUM |
| `api/services/chat/core.py` | 1,751 | AI chat orchestration | HIGH |
| `api/template_library_full.py` | 1,676 | SQL template library (256 templates) | LOW |
| `api/routes/vault/files.py` | 1,565 | Vault file operations endpoints | MEDIUM |
| `api/routes/team.py` | 1,443 | Team collaboration endpoints (52 routes) | MEDIUM |

#### Medium Priority (1000-1500 lines)

| File | Lines | Current Responsibility | Refactoring Complexity |
|------|-------|------------------------|------------------------|
| `api/core_nlp_templates.py` | 1,183 | Natural language SQL templates | LOW |
| `api/p2p_chat_service.py` | 1,151 | P2P chat service | MEDIUM |
| `api/permissions_admin.py` | 1,077 | Admin permission management | MEDIUM |
| `api/code_editor_service.py` | 1,064 | Code editor backend logic | MEDIUM |
| `api/permission_engine.py` | 1,052 | RBAC permission engine | MEDIUM |
| `api/services/permissions.py` | 1,050 | Permission service layer | MEDIUM |
| `api/admin_service.py` | 1,049 | Admin operations | MEDIUM |
| `api/code_operations.py` | 1,036 | Code file operations | MEDIUM |

### Frontend Files (Threshold: >500 lines)

#### Critical Priority (>900 lines)

| File | Lines | Current Responsibility | Refactoring Complexity |
|------|-------|------------------------|------------------------|
| `components/VaultWorkspace.tsx` | 4,119 | Entire vault UI (ALREADY PARTIALLY REFACTORED) | MEDIUM |
| `components/VaultWorkspace/index.tsx` | 942 | Vault main component | LOW |
| `components/settings/SettingsTab.tsx` | 862 | Settings tab coordination | MEDIUM |
| `components/ProjectLibraryModal.tsx` | 798 | Project library modal | MEDIUM |
| `components/ProfileSettingsModal.tsx` | 773 | User profile settings | MEDIUM |
| `components/LibraryModal.tsx` | 726 | Library modal | MEDIUM |
| `components/TeamChatWindow.tsx` | 725 | Team chat interface | HIGH |

#### High Priority (600-900 lines)

| File | Lines | Current Responsibility | Refactoring Complexity |
|------|-------|------------------------|------------------------|
| `components/DocumentEditor.tsx` | 660 | Document editing | MEDIUM |
| `components/Automation/shared/templates.ts` | 652 | Automation templates (data) | LOW |
| `components/CodeEditorPanel.tsx` | 593 | Code editor panel | MEDIUM |
| `components/settings/DangerZoneTab.tsx` | 587 | Danger zone settings | LOW |
| `components/Automation/index.tsx` | 585 | Automation workspace | MEDIUM |
| `components/NetworkSelector.tsx` | 580 | Network selection UI | MEDIUM |
| `components/WorkflowDesigner.tsx` | 578 | Workflow visual designer | HIGH |
| `components/Header.tsx` | 571 | Main app header | MEDIUM |
| `components/CodeEditor.tsx` | 568 | Monaco editor wrapper | MEDIUM |
| `components/VaultWorkspace/hooks.ts` | 567 | Vault custom hooks | LOW |
| `components/CodeEditorTab.tsx` | 558 | Code editor tab | MEDIUM |

#### Medium Priority (500-600 lines)

| File | Lines | Current Responsibility | Refactoring Complexity |
|------|-------|------------------------|------------------------|
| `App.tsx` | 555 | Main app component + routing | HIGH |
| `components/SpreadsheetEditor.tsx` | 551 | Spreadsheet editor | MEDIUM |
| `components/settings/AdminTab.tsx` | 542 | Admin settings tab | MEDIUM |
| `stores/docsStore.ts` | 541 | Documents Zustand store | LOW |
| `components/data/PatternDiscoveryPanel.tsx` | 531 | Data pattern discovery | MEDIUM |
| `components/ModelManagementSidebar.tsx` | 527 | AI model management | MEDIUM |
| `components/settings/AppSettingsTab.tsx` | 516 | App settings tab | MEDIUM |

### Package Files (Threshold: >500 lines)

| File | Lines | Current Responsibility | Refactoring Complexity |
|------|-------|------------------------|------------------------|
| `packages/pulsar_core/engine.py` | 980 | JSON normalization engine | HIGH |
| `packages/neutron_core/engine.py` | 875 | DuckDB SQL engine ("dumb core") | HIGH |

---

## Refactoring Strategy

### Phase-Based Approach

We'll tackle this in **6 phases**, prioritizing by:
1. **Impact**: High-traffic files first
2. **Dependencies**: Leaf modules before core modules
3. **Complexity**: Start with easier wins to build momentum
4. **Team coordination**: Backend and frontend can work in parallel

### General Refactoring Principles

#### For Backend Files:
1. **Service Layer Pattern**: Split into multiple focused services
2. **Single Responsibility**: Each module does ONE thing well
3. **Dependency Injection**: Pass dependencies explicitly
4. **Interface Segregation**: Define clear interfaces between modules
5. **Testing**: Each new module gets unit tests

#### For Frontend Files:
1. **Component Composition**: Break into smaller, reusable components
2. **Custom Hooks**: Extract logic into custom hooks
3. **Context/Store Splitting**: Separate concerns in state management
4. **Code Splitting**: Use React.lazy() for route-based splitting
5. **Type Safety**: Maintain strong TypeScript typing

## Non-Goals

- No intentional changes to external API contracts (HTTP routes, request/response schemas, or auth flows).
- No new product features shipped as part of refactor PRs; feature work lives on separate branches.
- No functional changes to database schemas beyond mechanical migrations required to support module splits.
- No performance optimizations that alter observable behavior; performance tuning happens after refactors stabilize.

---

## Detailed Refactoring Plans

### PHASE 1: Quick Wins (Data/Template Files)
**Goal**: Build momentum with low-complexity refactors
**Duration**: 2-3 days
**Risk**: LOW

**Success Criteria**:
- Template, NLP, and Automation template files are split into the new module structures with all imports updated.
- Backend and frontend builds/tests pass with no public API or route changes.

**Testing Requirements**:
- Unit tests for each new template/NLP module.
- Smoke tests (automated or manual) for Automation flows that consume the shared templates.

#### Backend Tasks:

##### 1.1 Split `api/template_library_full.py` (1,676 lines)
**Current**: 256 SQL templates in one massive file
**Target Structure**:
```
api/templates/
├── __init__.py                 # Template registry
├── analytics.py                # Analytics templates (20 templates)
├── data_quality.py             # Data quality templates (30 templates)
├── transformations.py          # ETL templates (40 templates)
├── aggregations.py             # Aggregation templates (30 templates)
├── joins.py                    # Join templates (25 templates)
├── window_functions.py         # Window function templates (20 templates)
├── date_time.py                # Date/time templates (25 templates)
├── string_operations.py        # String templates (20 templates)
├── advanced_analytics.py       # ML/stats templates (20 templates)
└── utilities.py                # Utility templates (26 templates)
```

**Refactoring Steps**:
1. Create `api/templates/` directory
2. Group templates by category (analytics, data quality, etc.)
3. Create registry pattern in `__init__.py` for template discovery
4. Add type hints for template parameters
5. Update imports in dependent files
6. Add unit tests for each template category

**Dependencies**: None
**Breaking Changes**: None (internal only)

##### 1.2 Split `api/core_nlp_templates.py` (1,183 lines)
**Current**: Natural language to SQL templates
**Target Structure**:
```
api/nlp/
├── __init__.py
├── patterns.py                 # Regex patterns
├── intent_classifier.py        # Intent detection
├── entity_extractor.py         # Entity extraction
├── template_matcher.py         # Template matching logic
└── sql_generator.py            # SQL generation
```

**Refactoring Steps**:
1. Create `api/nlp/` directory
2. Separate pattern definitions from logic
3. Extract intent classification
4. Extract entity extraction
5. Extract template matching
6. Update imports in `api/services/nlq_service.py`

**Dependencies**: None
**Breaking Changes**: None

##### 1.3 Split `components/Automation/shared/templates.ts` (652 lines)
**Current**: Automation template data in one file
**Target Structure**:
```
components/Automation/templates/
├── index.ts                    # Registry + exports
├── types.ts                    # Template type definitions
├── data-processing.ts          # Data processing templates
├── api-integrations.ts         # API integration templates
├── file-operations.ts          # File operation templates
├── notifications.ts            # Notification templates
└── scheduling.ts               # Scheduling templates
```

**Refactoring Steps**:
1. Create `components/Automation/templates/` directory
2. Group templates by category
3. Extract type definitions to `types.ts`
4. Create registry in `index.ts`
5. Update imports in `components/Automation/index.tsx`

**Dependencies**: None
**Breaking Changes**: None

---

### PHASE 2: Backend Services (Critical Path)
**Goal**: Refactor largest backend service files
**Duration**: 1 week
**Risk**: MEDIUM-HIGH

**Success Criteria**:
- Team, Vault, and Chat services are decomposed into focused submodules with `core.py` files acting only as orchestration layers.
- All related API endpoints behave identically in integration/E2E tests (permissions, audit trails, and data semantics unchanged).

**Testing Requirements**:
- Unit tests for each new service submodule.
- Integration tests for critical team, vault, and chat workflows, including permission checks and audit logging.

#### 2.1 Refactor `api/services/team/core.py` (2,872 lines)
**Current**: Monolithic team service with everything
**Target Structure**:
```
api/services/team/
├── __init__.py                 # Public API exports
├── core.py                     # Orchestration layer (200 lines)
├── members.py                  # Member management
├── invitations.py              # Invitation handling
├── permissions.py              # Team permissions
├── chat.py                     # Team chat operations
├── workspaces.py               # Workspace management
├── notifications.py            # Team notifications
├── analytics.py                # Team analytics
├── storage.py                  # Team storage operations
└── types.py                    # Type definitions
```

**Refactoring Steps**:
1. Create `types.py` with all data models and type hints
2. Extract database operations to `storage.py`
3. Extract member operations to `members.py` (~400 lines)
4. Extract invitation logic to `invitations.py` (~300 lines)
5. Extract permissions to `permissions.py` (~350 lines)
6. Extract chat operations to `chat.py` (~400 lines)
7. Extract workspace logic to `workspaces.py` (~300 lines)
8. Extract notifications to `notifications.py` (~250 lines)
9. Extract analytics to `analytics.py` (~200 lines)
10. Reduce `core.py` to orchestration only (~200 lines)
11. Update `api/routes/team.py` imports
12. Add unit tests for each module

**Dependencies**:
- `api/routes/team.py` (1,443 lines - also needs refactoring)
- `api/permission_engine.py`

**Breaking Changes**: None (maintain same public API)

**Test Strategy**:
- Unit tests for each new module
- Integration tests for `core.py` orchestration
- Regression tests for existing team endpoints

#### 2.2 Refactor `api/services/vault/core.py` (2,780 lines)
**Current**: Monolithic vault service
**Target Structure**:
```
api/services/vault/
├── __init__.py                 # Public API exports
├── core.py                     # Orchestration layer (200 lines)
├── encryption.py               # Crypto operations
├── files.py                    # File operations
├── folders.py                  # Folder operations
├── documents.py                # Document operations
├── sharing.py                  # Sharing logic
├── automation.py               # Automation rules
├── search.py                   # Vault search
├── storage.py                  # Database operations
├── websocket.py                # WebSocket handlers
└── types.py                    # Type definitions
```

**Refactoring Steps**:
1. Create `types.py` with all models
2. Extract crypto to `encryption.py` (~400 lines)
3. Extract file ops to `files.py` (~500 lines)
4. Extract folder ops to `folders.py` (~300 lines)
5. Extract document ops to `documents.py` (~400 lines)
6. Extract sharing to `sharing.py` (~400 lines)
7. Extract automation to `automation.py` (~300 lines)
8. Extract search to `search.py` (~200 lines)
9. Extract DB ops to `storage.py` (~300 lines)
10. Extract WebSocket to `websocket.py` (~200 lines)
11. Reduce `core.py` to orchestration (~200 lines)
12. Update route imports in `api/routes/vault/`

**Dependencies**:
- `api/routes/vault/files.py` (1,565 lines)
- `api/routes/vault/sharing.py` (624 lines)
- `api/services/crypto_wrap.py`

**Breaking Changes**: None

#### 2.3 Refactor `api/services/chat/core.py` (1,751 lines)
**Current**: Monolithic chat service
**Target Structure**:
```
api/services/chat/
├── __init__.py                 # Public API exports
├── core.py                     # Orchestration layer (200 lines)
├── ollama_client.py            # Ollama API client
├── session_manager.py          # Session management
├── message_handler.py          # Message processing
├── streaming.py                # WebSocket streaming
├── context_manager.py          # Context window management
├── model_selector.py           # Model selection logic
├── file_processor.py           # File attachment processing
├── storage.py                  # Database operations
└── types.py                    # Type definitions
```

**Refactoring Steps**:
1. Create `types.py` with all models
2. Extract Ollama client to `ollama_client.py` (~300 lines)
3. Extract session logic to `session_manager.py` (~250 lines)
4. Extract message handling to `message_handler.py` (~300 lines)
5. Extract streaming to `streaming.py` (~250 lines)
6. Extract context to `context_manager.py` (~200 lines)
7. Extract model selection to `model_selector.py` (~200 lines)
8. Extract file processing to `file_processor.py` (~200 lines)
9. Extract DB ops to `storage.py` (~250 lines)
10. Reduce `core.py` to orchestration (~200 lines)
11. Update route imports

**Dependencies**:
- `api/routes/chat/` (28 endpoints)
- `api/chat_memory.py` (891 lines - may also need refactoring)

**Breaking Changes**: None

---

### PHASE 3: Backend Routes & Main
**Goal**: Clean up route files and main.py
**Duration**: 1 week
**Risk**: MEDIUM

**Success Criteria**:
- `api/main.py` is reduced to a minimal entry point using `app_factory.py`, and route files are split as proposed without changing URL paths.
- FastAPI startup, health checks, and route registration succeed locally and in CI environments.

**Testing Requirements**:
- Integration or smoke tests that cover app startup, core routes, and the most-used vault/team endpoints.

#### 3.1 Refactor `api/main.py` (1,920 lines)
**Current**: Everything in one file (app setup, middleware, routes, startup, shutdown)
**Target Structure**:
```
api/
├── main.py                     # Entry point only (100 lines)
├── app_factory.py              # FastAPI app creation (150 lines)
├── middleware/
│   ├── __init__.py
│   ├── auth.py                 # JWT middleware (from auth_middleware.py)
│   ├── cors.py                 # CORS configuration
│   ├── rate_limit.py           # Rate limiting
│   └── error_handlers.py       # Global error handling
├── startup/
│   ├── __init__.py
│   ├── migrations.py           # Database migrations
│   ├── ollama.py               # Ollama initialization
│   ├── metal4.py               # Metal 4 GPU setup
│   └── health_checks.py        # Startup health checks
└── routes/
    └── __init__.py             # Route registration (200 lines)
```

**Refactoring Steps**:
1. Create `app_factory.py` for FastAPI app creation
2. Move middleware to `middleware/` directory
3. Move startup logic to `startup/` directory
4. Create route registration module
5. Reduce `main.py` to minimal entry point
6. Update imports across the project

**Dependencies**: ALL route files
**Breaking Changes**: None

#### 3.2 Refactor `api/routes/vault/files.py` (1,565 lines)
**Current**: 30+ endpoints in one file
**Target Structure**:
```
api/routes/vault/
├── __init__.py
├── files/
│   ├── __init__.py
│   ├── upload.py               # Upload endpoints
│   ├── download.py             # Download endpoints
│   ├── management.py           # CRUD operations
│   ├── search.py               # Search endpoints
│   └── metadata.py             # Metadata operations
├── folders.py                  # Folder operations
├── sharing.py                  # Already separate (624 lines)
├── automation.py               # Automation rules
└── websocket.py                # WebSocket routes
```

**Refactoring Steps**:
1. Create `files/` subdirectory
2. Group endpoints by operation type
3. Split into 5 focused modules
4. Update route registration
5. Maintain same URL paths

**Dependencies**: `api/services/vault/`
**Breaking Changes**: None (URL paths stay same)

#### 3.3 Refactor `api/routes/team.py` (1,443 lines - 52 endpoints!)
**Current**: 52 endpoints in one file
**Target Structure**:
```
api/routes/team/
├── __init__.py
├── teams.py                    # Team CRUD (10 endpoints)
├── members.py                  # Member management (12 endpoints)
├── invitations.py              # Invitations (8 endpoints)
├── permissions.py              # Permissions (10 endpoints)
├── chat.py                     # Team chat (6 endpoints)
├── workspaces.py               # Workspaces (4 endpoints)
└── analytics.py                # Analytics (2 endpoints)
```

**Refactoring Steps**:
1. Create `team/` subdirectory
2. Group endpoints by resource type
3. Split into 7 focused modules (~200 lines each)
4. Update route registration
5. Maintain URL paths

**Dependencies**: `api/services/team/`
**Breaking Changes**: None

---

### PHASE 4: Frontend Core Components
**Goal**: Refactor largest frontend components
**Duration**: 1 week
**Risk**: MEDIUM-HIGH

**Success Criteria**:
- VaultWorkspace, App shell, TeamChat, and WorkflowDesigner are split into smaller components/hooks that match the proposed structures.
- Frontend builds with no TypeScript errors and E2E flows for vault, chat, workflows, and navigation continue to pass.

**Testing Requirements**:
- Component or unit tests where they already exist.
- E2E or scripted smoke tests for core user journeys (vault, chat, workflows, login/navigation).

#### 4.1 Complete `VaultWorkspace.tsx` Refactoring
**Current**: Partially refactored (4,119 lines + 942 line index)
**Status**: Already has `VaultWorkspace/` directory
**Target Structure**:
```
components/VaultWorkspace/
├── index.tsx                   # Main component (150 lines)
├── hooks.ts                    # Custom hooks (567 lines - DONE)
├── types.ts                    # Type definitions
├── FileList/
│   ├── index.tsx               # File list component
│   ├── FileItem.tsx            # Individual file item
│   ├── FileActions.tsx         # File action buttons
│   └── FilePreview.tsx         # File preview modal
├── FolderTree/
│   ├── index.tsx               # Folder tree component
│   ├── FolderNode.tsx          # Tree node component
│   └── FolderActions.tsx       # Folder actions
├── Upload/
│   ├── UploadButton.tsx        # Upload button
│   ├── UploadProgress.tsx      # Progress indicator
│   └── DragDropZone.tsx        # Drag-drop zone
├── Sharing/
│   ├── SharingModal.tsx        # Share modal
│   ├── PermissionSelector.tsx  # Permission UI
│   └── SharedWithList.tsx      # Shared users list
├── Automation/
│   ├── AutomationPanel.tsx     # Automation UI
│   └── RuleBuilder.tsx         # Rule builder
└── Search/
    ├── SearchBar.tsx           # Search input
    └── SearchResults.tsx       # Results display
```

**Refactoring Steps**:
1. Audit existing `VaultWorkspace/` structure
2. Create missing subdirectories
3. Extract file list components
4. Extract folder tree components
5. Extract upload components
6. Extract sharing components
7. Extract automation components
8. Extract search components
9. Reduce `index.tsx` to composition (~150 lines)
10. Update store imports

**Dependencies**: `stores/vaultStore.ts`
**Breaking Changes**: None

#### 4.2 Refactor `App.tsx` (555 lines)
**Current**: Main app + routing + auth + layout
**Target Structure**:
```
src/
├── App.tsx                     # Entry point (100 lines)
├── AppRouter.tsx               # Routing logic (150 lines)
├── AppLayout.tsx               # Layout component (150 lines)
├── AuthGuard.tsx               # Auth wrapper (100 lines)
└── AppProviders.tsx            # Context providers (50 lines)
```

**Refactoring Steps**:
1. Extract routing to `AppRouter.tsx`
2. Extract layout to `AppLayout.tsx`
3. Extract auth guard to `AuthGuard.tsx`
4. Extract providers to `AppProviders.tsx`
5. Reduce `App.tsx` to composition

**Dependencies**: All pages and stores
**Breaking Changes**: None

#### 4.3 Refactor `components/TeamChatWindow.tsx` (725 lines)
**Current**: Monolithic chat component
**Target Structure**:
```
components/TeamChat/
├── index.tsx                   # Main component (150 lines)
├── MessageList.tsx             # Message list
├── MessageItem.tsx             # Single message
├── MessageInput.tsx            # Input area
├── UserList.tsx                # Online users
├── TypingIndicator.tsx         # Typing indicator
├── FileAttachment.tsx          # File attachments
└── hooks/
    ├── useMessages.ts          # Message hooks
    ├── useTyping.ts            # Typing hooks
    └── useWebSocket.ts         # WebSocket hook
```

**Refactoring Steps**:
1. Create `TeamChat/` directory
2. Extract message list
3. Extract message input
4. Extract user list
5. Extract custom hooks
6. Reduce main component to composition

**Dependencies**: `stores/teamStore.ts`
**Breaking Changes**: None

#### 4.4 Refactor `components/WorkflowDesigner.tsx` (578 lines)
**Current**: Monolithic visual designer
**Target Structure**:
```
components/WorkflowDesigner/
├── index.tsx                   # Main component
├── Canvas.tsx                  # Workflow canvas
├── NodePalette.tsx             # Node palette
├── NodeRenderer.tsx            # Node rendering
├── EdgeRenderer.tsx            # Edge rendering
├── PropertyPanel.tsx           # Node properties
├── Toolbar.tsx                 # Designer toolbar
└── hooks/
    ├── useCanvas.ts            # Canvas logic
    ├── useDragDrop.ts          # Drag-drop
    └── useWorkflowState.ts     # State management
```

**Refactoring Steps**:
1. Create `WorkflowDesigner/` directory
2. Extract canvas component
3. Extract node palette
4. Extract renderers
5. Extract property panel
6. Extract custom hooks
7. Reduce main component

**Dependencies**: `types/workflow.ts`, workflow stores
**Breaking Changes**: None

---

### PHASE 5: Settings & Modals
**Goal**: Modularize settings and modal components
**Duration**: 5 days
**Risk**: LOW-MEDIUM

**Success Criteria**:
- `SettingsTab` and large modal components are decomposed into layout + tab/modal subcomponents without changing settings behavior.
- All settings panels and modals render and function as before in manual/E2E checks.

**Testing Requirements**:
- UI regression tests or scripted/manual checklists for each settings tab and modal.

#### 5.1 Refactor `components/settings/SettingsTab.tsx` (862 lines)
**Current**: Monolithic settings tab coordinator
**Target Structure**:
```
components/settings/
├── SettingsTab.tsx             # Tab coordinator (200 lines)
├── SettingsLayout.tsx          # Layout wrapper
├── tabs/
│   ├── AppSettingsTab.tsx      # App settings (516 lines - keep as is)
│   ├── AdminTab.tsx            # Admin (542 lines - keep as is)
│   ├── DangerZoneTab.tsx       # Danger zone (587 lines - may split)
│   ├── AnalyticsTab.tsx        # Analytics (495 lines)
│   ├── BackupsTab.tsx          # Backups (482 lines)
│   ├── AuditLogsTab.tsx        # Audit logs (467 lines)
│   ├── LegalDisclaimersTab.tsx # Legal (467 lines)
│   └── ChatSettingsContent.tsx # Chat settings (458 lines)
└── shared/
    ├── SettingSection.tsx      # Section component
    ├── SettingRow.tsx          # Row component
    └── SettingToggle.tsx       # Toggle component
```

**Refactoring Steps**:
1. Extract shared UI components
2. Simplify tab coordinator
3. Review individual tabs for further splitting
4. Create reusable setting components

**Dependencies**: All settings tabs
**Breaking Changes**: None

#### 5.2 Refactor Large Modals
**Files**:
- `components/ProjectLibraryModal.tsx` (798 lines)
- `components/ProfileSettingsModal.tsx` (773 lines)
- `components/LibraryModal.tsx` (726 lines)

**Target Structure** (example for ProfileSettingsModal):
```
components/ProfileSettings/
├── Modal.tsx                   # Modal wrapper (100 lines)
├── AccountTab.tsx              # Account settings
├── SecurityTab.tsx             # Security settings
├── PreferencesTab.tsx          # User preferences
├── AppearanceTab.tsx           # Appearance settings
└── NotificationsTab.tsx        # Notification settings
```

**Refactoring Steps**:
1. Split each modal into tab components
2. Extract reusable modal wrapper
3. Create shared form components
4. Reduce main modal to composition

**Dependencies**: User stores
**Breaking Changes**: None

---

### PHASE 6: Backend Utilities & Edge Cases
**Goal**: Clean up remaining large backend files
**Duration**: 5 days
**Risk**: LOW-MEDIUM

**Success Criteria**:
- Permission, code editor, and other large backend utility files are reorganized into dedicated modules with stable public APIs.
- All permission checks, code editor operations, and related endpoints pass integration tests, with no regressions in existing monitoring.

**Testing Requirements**:
- Unit tests for new utility modules.
- Integration tests around permissions, code editing, and workflows that depend on these utilities.

#### 6.1 Refactor Permission Files
**Files**:
- `api/permissions_admin.py` (1,077 lines)
- `api/permission_engine.py` (1,052 lines)
- `api/services/permissions.py` (1,050 lines)
- `api/permission_layer.py` (757 lines)

**Target Structure**:
```
api/permissions/
├── __init__.py                 # Public API
├── engine.py                   # Core RBAC engine (300 lines)
├── admin.py                    # Admin operations (300 lines)
├── decorators.py               # @require_perm decorator
├── hierarchy.py                # Permission hierarchy
├── storage.py                  # Database operations
└── types.py                    # Type definitions
```

**Refactoring Steps**:
1. Consolidate 4 files into single `permissions/` module
2. Remove duplication between files
3. Create clear separation of concerns
4. Maintain same decorator API

**Dependencies**: Nearly all routes
**Breaking Changes**: None (decorator API stays same)

#### 6.2 Refactor Code Editor Files
**Files**:
- `api/code_editor_service.py` (1,064 lines)
- `api/code_operations.py` (1,036 lines)

**Target Structure**:
```
api/services/code_editor/
├── __init__.py
├── service.py                  # Main service (300 lines)
├── file_operations.py          # File ops
├── git_operations.py           # Git integration
├── linting.py                  # Linting operations
├── formatting.py               # Code formatting
└── language_server.py          # LSP integration
```

**Refactoring Steps**:
1. Create `code_editor/` service directory
2. Split by operation type
3. Consolidate duplicate code
4. Add type hints

**Dependencies**: Code workspace routes
**Breaking Changes**: None

#### 6.3 Refactor Other Large Files
**Files**:
- `api/p2p_chat_service.py` (1,151 lines) → Split into `p2p/chat/`
- `api/admin_service.py` (1,049 lines) → Split by admin operation type
- `api/learning_system.py` (979 lines) → Split into `learning/`
- `api/agent/orchestrator.py` (961 lines) → Split into `agent/orchestration/`
- `api/workflow_orchestrator.py` (917 lines) → Merge with workflow_service.py

**Approach**: Apply same patterns as above phases

---

### PHASE 7: Package Refactoring (Lower Priority)
**Goal**: Refactor core packages
**Duration**: 1 week
**Risk**: HIGH (these are "dumb core" - must remain stable)

**Success Criteria**:
- `pulsar_core` and `neutron_core` engines are split into smaller modules with `engine.py` providing the only public API surface.
- All existing consumers of these packages compile and pass regression and performance tests.

**Testing Requirements**:
- High-coverage unit and integration tests around core package behavior.
- Targeted performance benchmarks to ensure no regressions in critical workloads.

#### 7.1 `packages/pulsar_core/engine.py` (980 lines)
**Current**: Monolithic JSON normalization engine
**Target Structure**:
```
packages/pulsar_core/
├── engine.py                   # Public API (100 lines)
├── parser.py                   # JSON parsing
├── normalizer.py               # Normalization logic
├── flattener.py                # Object flattening
├── type_inference.py           # Type detection
└── excel_writer.py             # Excel output (323 lines - keep)
```

**Caution**: This is core infrastructure - extensive testing required

#### 7.2 `packages/neutron_core/engine.py` (875 lines)
**Current**: DuckDB engine wrapper
**Target Structure**:
```
packages/neutron_core/
├── engine.py                   # Public API (100 lines)
├── connection.py               # DuckDB connection
├── query_executor.py           # Query execution
├── type_mapper.py              # Type mapping
├── memory_manager.py           # Memory management
└── streaming.py                # Large file streaming
```

**Caution**: "Dumb core that always works" - must remain ultra-reliable

---

## Implementation Guidelines

### Code Review Process
1. **PR Size**: Max 500 lines changed per PR
2. **Review Team**: At least 2 reviewers (Claude, User, Codex)
3. **Testing**: 80%+ code coverage for new modules
4. **Documentation**: Update docstrings and type hints
5. **Migration**: Ensure zero downtime during refactor

### Testing Strategy
1. **Unit Tests**: Each new module gets isolated tests
2. **Integration Tests**: Test module interactions
3. **Regression Tests**: Ensure existing behavior unchanged
4. **E2E Tests**: Validate full user workflows still work

### Git Strategy
1. **Branch Naming**: `refactor/phase-{N}-{component-name}`
2. **Commits**: Atomic commits with clear messages
3. **PRs**: One PR per major file/component
4. **Merging**: Squash merge to keep history clean
5. **Isolation**: Refactor branches must not include unrelated feature work to keep rollbacks simple.

### Rollback Plan
1. **Feature Branches**: Keep refactors on short-lived `refactor/...` branches so they can be rolled back as a unit.
2. **Feature Flags**: Use flags for new module paths that change runtime behavior so they can be disabled quickly if needed.
3. **Gradual Migration**: Keep old code until new code proven
4. **Monitoring**: Watch error rates after each merge
5. **Quick Revert**: Ability to revert any PR within 5 minutes

---

## Success Metrics

### Code Quality Metrics
- **Average File Size**: <500 lines for frontend, <800 lines for backend
- **Cyclomatic Complexity**: <10 per function
- **Test Coverage**: >80% for all new modules
- **Type Coverage**: 100% (TypeScript strict mode)

### Developer Experience Metrics
- **Build Time**: <30 seconds for full build
- **Hot Reload Time**: <2 seconds for single file change
- **PR Review Time**: <1 hour for refactor PRs
- **Onboarding Time**: New dev productive in <1 day

### Performance Metrics
- **Bundle Size**: Reduce by 15% via better code splitting
- **Initial Load**: <2 seconds for first render
- **Route Transitions**: <200ms for lazy-loaded routes
- **Memory Usage**: No increase after refactor

---

## Timeline & Milestones

### Week 1-2: Phase 1 + Phase 2 Start
- Complete all template/data file splits
- Begin Team service refactor
- **Milestone**: All template files modular

### Week 3-4: Phase 2 Complete
- Complete Team, Vault, Chat service refactors
- **Milestone**: All critical backend services modular

### Week 5-6: Phase 3
- Refactor main.py and route files
- **Milestone**: Backend architecture clean

### Week 7-8: Phase 4
- Refactor VaultWorkspace, App.tsx, TeamChat, WorkflowDesigner
- **Milestone**: All critical frontend components modular

### Week 9: Phase 5
- Refactor settings and modals
- **Milestone**: All frontend components <500 lines

### Week 10: Phase 6
- Clean up remaining backend files
- **Milestone**: All backend files <800 lines

### Week 11-12: Phase 7 (Optional)
- Refactor core packages (if time permits)
- **Milestone**: Entire codebase modular

---

## Risk Mitigation

### High-Risk Areas
1. **api/main.py**: Breaking this could break entire backend
   - **Mitigation**: Comprehensive integration tests, gradual migration
2. **App.tsx**: Core frontend routing
   - **Mitigation**: E2E tests for all routes, feature flags
3. **Vault/Team services**: Complex business logic
   - **Mitigation**: Extensive unit tests, parallel old/new code paths
4. **Core packages**: Foundation of entire system
   - **Mitigation**: 100% test coverage, beta testing period

### Common Pitfalls
1. **Circular Dependencies**: Avoid by clear dependency hierarchy
2. **Breaking Public APIs**: Maintain same interfaces
3. **Test Coverage Gaps**: Write tests BEFORE refactoring
4. **Performance Regressions**: Benchmark before/after
5. **Merge Conflicts**: Coordinate refactors across team

---

## Team Coordination

### Roles & Responsibilities

**Claude** (AI Assistant):
- Code generation for boilerplate
- Refactoring execution
- Test generation
- Documentation updates

**User**:
- Architecture decisions
- Code review
- Testing coordination
- Final approval

**Codex** (AI Pair Programmer):
- Parallel refactoring work
- Code review
- Integration testing
- Performance optimization

### Communication
- **Daily Standups**: Quick sync on progress
- **PR Reviews**: Within 24 hours
- **Blockers**: Immediate notification
- **Demos**: Weekly demo of refactored modules

### Conflict Resolution
- **Code Conflicts**: Git conflict resolution protocol
- **Design Conflicts**: Architecture decision records (ADRs)
- **Priority Conflicts**: User has final say

---

## Appendix: File Size Summary

### Backend Top 20 Files
| Rank | File | Lines | Category |
|------|------|-------|----------|
| 1 | `api/services/team/core.py` | 2,872 | Service |
| 2 | `api/services/vault/core.py` | 2,780 | Service |
| 3 | `api/main.py` | 1,920 | Core |
| 4 | `api/services/chat/core.py` | 1,751 | Service |
| 5 | `api/template_library_full.py` | 1,676 | Data |
| 6 | `api/routes/vault/files.py` | 1,565 | Routes |
| 7 | `api/routes/team.py` | 1,443 | Routes |
| 8 | `api/core_nlp_templates.py` | 1,183 | Data |
| 9 | `api/p2p_chat_service.py` | 1,151 | Service |
| 10 | `api/permissions_admin.py` | 1,077 | Service |
| 11 | `api/code_editor_service.py` | 1,064 | Service |
| 12 | `api/permission_engine.py` | 1,052 | Service |
| 13 | `api/services/permissions.py` | 1,050 | Service |
| 14 | `api/admin_service.py` | 1,049 | Service |
| 15 | `api/code_operations.py` | 1,036 | Service |
| 16 | `api/learning_system.py` | 979 | Service |
| 17 | `api/agent/orchestrator.py` | 961 | Service |
| 18 | `api/routes/sql_json.py` | 948 | Routes |
| 19 | `api/workflow_orchestrator.py` | 917 | Service |
| 20 | `api/agent/engines/codex_engine.py` | 910 | Service |

**Total Lines in Top 20**: 28,363 lines
**Target After Refactor**: ~8,000 lines (70% reduction)

### Frontend Top 20 Files
| Rank | File | Lines | Category |
|------|------|-------|----------|
| 1 | `components/VaultWorkspace.tsx` | 4,119 | Component |
| 2 | `components/VaultWorkspace/index.tsx` | 942 | Component |
| 3 | `components/settings/SettingsTab.tsx` | 862 | Component |
| 4 | `components/ProjectLibraryModal.tsx` | 798 | Component |
| 5 | `components/ProfileSettingsModal.tsx` | 773 | Component |
| 6 | `components/LibraryModal.tsx` | 726 | Component |
| 7 | `components/TeamChatWindow.tsx` | 725 | Component |
| 8 | `components/DocumentEditor.tsx` | 660 | Component |
| 9 | `components/Automation/shared/templates.ts` | 652 | Data |
| 10 | `components/CodeEditorPanel.tsx` | 593 | Component |
| 11 | `components/settings/DangerZoneTab.tsx` | 587 | Component |
| 12 | `components/Automation/index.tsx` | 585 | Component |
| 13 | `components/NetworkSelector.tsx` | 580 | Component |
| 14 | `components/WorkflowDesigner.tsx` | 578 | Component |
| 15 | `types/workflow.ts` | 572 | Types |
| 16 | `components/Header.tsx` | 571 | Component |
| 17 | `components/CodeEditor.tsx` | 568 | Component |
| 18 | `components/VaultWorkspace/hooks.ts` | 567 | Hooks |
| 19 | `components/CodeEditorTab.tsx` | 558 | Component |
| 20 | `App.tsx` | 555 | Core |

**Total Lines in Top 20**: 16,570 lines
**Target After Refactor**: ~5,000 lines (70% reduction)

---

## Next Steps

1. **Review this plan** with User and Codex
2. **Prioritize phases** based on current sprint goals
3. **Set up tracking** (GitHub project board)
4. **Create branch strategy** for refactor work
5. **Begin Phase 1** with template file splits

---

## PHASE 8: Stealth Labels - App-Wide Privacy Feature (Future)
**Goal**: Implement comprehensive stealth label system across entire app
**Duration**: 2 weeks
**Risk**: MEDIUM
**Priority**: DEFERRED - Requires Phase 1-6 completion first

### Current State
**Partially Implemented** (frontend only, Vault workspace only):
- `stealth_labels` setting exists in `docsStore` (per-user preference)
- `VaultWorkspace.tsx:313` has `getDisplayTitle()` that checks for stealth labels
- Documents have optional `stealth_label` field
- **NOT part of RBAC** - it's a user privacy preference
- **NO backend storage** - purely frontend behavior

### Problems with Current Implementation
1. **Inconsistent coverage**: Only works in Vault, not in chat/team/search/files/etc.
2. **No persistence**: Stealth labels not stored in backend database
3. **App title exposure**: Window title always shows "ElohimOS" regardless of stealth mode
4. **Search leakage**: Search results show real titles
5. **Notification leakage**: Toasts/notifications show real titles
6. **Recent files leakage**: File browsers show real titles
7. **Chat history leakage**: Chat shows real document references

### Proposed Solution

#### Backend Changes
**New database fields** (across all relevant tables):
```sql
-- Add to vault documents
ALTER TABLE vault_documents ADD COLUMN stealth_label TEXT;

-- Add to chat sessions
ALTER TABLE chat_sessions ADD COLUMN stealth_label TEXT;

-- Add to team files
ALTER TABLE team_files ADD COLUMN stealth_label TEXT;

-- Add to code files
ALTER TABLE code_files ADD COLUMN stealth_label TEXT;

-- Add to saved queries
ALTER TABLE saved_queries ADD COLUMN stealth_label TEXT;
```

**New API endpoints**:
- `PATCH /api/v1/vault/documents/{id}/stealth-label` - Set stealth label
- `PATCH /api/v1/chat/sessions/{id}/stealth-label` - Set stealth label
- `GET /api/v1/settings/stealth-mode` - Get user's stealth mode preference
- `PUT /api/v1/settings/stealth-mode` - Update stealth mode preference

**Backend services**:
```
api/services/stealth/
├── __init__.py
├── label_manager.py      # CRUD for stealth labels
├── title_masker.py       # Apply stealth labels to responses
└── types.py              # Type definitions
```

#### Frontend Changes

**Global stealth context**:
```typescript
// New hook: useStealthMode
export function useStealthMode() {
  const { securitySettings } = useDocsStore()

  const getDisplayTitle = (item: {
    title: string
    stealth_label?: string
  }) => {
    if (securitySettings.stealth_labels && item.stealth_label) {
      return item.stealth_label
    }
    return item.title
  }

  const getAppTitle = () => {
    if (securitySettings.stealth_labels) {
      return 'Productivity Suite' // or user-configurable
    }
    return 'ElohimOS'
  }

  return { getDisplayTitle, getAppTitle, isStealthMode: securitySettings.stealth_labels }
}
```

**Components to update**:
1. **App.tsx** - Window title via `document.title`
2. **ChatWindow.tsx** - Message content, file references
3. **TeamWorkspace.tsx** - File lists, shared documents
4. **CodeWorkspace.tsx** - File browser, recent files
5. **SearchResults** (all) - Search result titles
6. **Toast notifications** - Success/error messages
7. **Header.tsx** - Breadcrumbs, current file name
8. **FileUpload.tsx** - Uploaded file names
9. **LibraryModal.tsx** - Query names
10. **ProjectLibraryModal.tsx** - Project names

**UI for setting stealth labels**:
- Add "Set Stealth Label" button to all file/document/chat UIs
- Modal to enter innocuous cover name
- Auto-suggest generic labels ("Document 1", "Notes", "Report")

#### App Title Bar Implementation
**High Priority Sub-task**:
```typescript
// In App.tsx or root component
useEffect(() => {
  const { securitySettings } = useDocsStore.getState()
  const appTitle = securitySettings.stealth_labels
    ? (securitySettings.stealth_app_name || 'Productivity Suite')
    : 'ElohimOS'

  document.title = appTitle
}, [securitySettings.stealth_labels, securitySettings.stealth_app_name])
```

**New setting**: `stealth_app_name` (user-configurable)
- Default: "Productivity Suite"
- Options: "Notes App", "Task Manager", "Project Tool", etc.
- Stored in user preferences

### Success Criteria
- [ ] All file/document references use stealth labels when enabled
- [ ] Window title changes based on stealth mode
- [ ] Search results respect stealth labels
- [ ] Notifications use stealth labels
- [ ] Backend persists stealth labels for all entity types
- [ ] Users can easily set/edit stealth labels
- [ ] No performance degradation from stealth checks
- [ ] Works consistently across all workspaces

### Testing Requirements
- [ ] Unit tests for `useStealthMode` hook
- [ ] E2E test: Enable stealth mode, verify all titles masked
- [ ] E2E test: Disable stealth mode, verify real titles shown
- [ ] Backend tests for stealth label CRUD operations
- [ ] Search tests with stealth labels
- [ ] Notification tests with stealth labels

### Migration Strategy
1. Add database columns (backward compatible - nullable)
2. Update backend APIs (backward compatible - optional fields)
3. Roll out frontend hook to one workspace at a time
4. Add UI for setting stealth labels
5. Apply to remaining workspaces
6. Add app title bar integration
7. Final E2E validation

### Dependencies
- **Requires**: Phase 4 (Frontend refactoring) for cleaner component updates
- **Blocks**: None (this is a standalone feature)

### Estimated Effort
- Backend: 3 days (migrations, APIs, services)
- Frontend: 5 days (hook, component updates, UI)
- Testing: 2 days (unit + E2E)
- Documentation: 1 day
- **Total**: 11 days (~2 weeks)

### Priority Justification
**Deferred to Phase 8** because:
- Not critical for modular refactoring goals
- Touches many components (easier after Phase 4 refactoring)
- Standalone feature that doesn't block other work
- User can manually avoid sensitive titles until implemented

---

## PHASE 9: Admin Tab RBAC & Multi-Profile System (Future)
**Goal**: Implement proper role-based access control for Admin tab with multi-profile support
**Duration**: 3-4 weeks
**Risk**: HIGH
**Priority**: DEFERRED - Requires deep architectural planning

### Current State
**Admin tab is currently unrestricted**:
- Admin tab (Shield icon) moved to bottom of nav rail (above Settings)
- **No RBAC enforcement**: All authenticated users can access Admin page
- **No profile isolation**: Solo users can see/modify everything
- **No multi-profile support**: Cannot restrict admin view to specific user profiles
- **Setup wizard exists** but doesn't configure profile/admin boundaries

### Problem Statement

When using ElohimOS solo (single user), the Admin page shows **all system data**:
- All users (even if you're the only one)
- All teams (even non-existent ones)
- All permissions (global view)
- All system settings
- Database health for ALL databases

**The core issue**: In solo mode, you should only see/manage **your own profile's data**, not the entire system.

**In team mode**, admin access should be restricted by:
- User role (founder_rights, super_admin, admin, member, viewer)
- Team membership (can only admin teams you're part of)
- Permission scope (can only see users/data you have permission to manage)

### Proposed Solution

#### Conceptual Model: Solo Mode vs Team Mode

**Solo Mode** (default for new users):
- User is the "owner" of their local instance
- Admin page shows only their profile's data
- No access to other users' data (even if they exist in DB)
- Settings are scoped to "my profile" not "system-wide"
- Equivalent to a personal workspace

**Team Mode** (enabled when joining/creating teams):
- User role determines admin capabilities
- founder_rights: Full system admin (all teams, all users)
- super_admin: Multi-team admin (teams they're assigned to)
- admin: Single team admin (their team only)
- member/viewer: No admin access

#### New RBAC Rules for Admin Tab

**Frontend (NavigationRail.tsx)**:
```typescript
case 'admin':
  // Admin tab visibility based on mode + role
  if (userMode === 'solo') {
    // Solo mode: Always show admin (for self-management)
    return true
  } else {
    // Team mode: Role-based access
    return permissions.canAccessAdmin // founder_rights, super_admin, admin
  }
```

**Backend**:
- New permission: `admin.access_panel`
- New setting: `user_mode` (solo | team)
- New concept: `profile_scope` (defines what data user can admin)

#### Profile Scope System

**Profile Scope Levels**:
1. **Self Only** (solo mode default)
   - Can only see/manage own user record
   - Can only see own teams (if any)
   - Can only see own settings
   - Database health: Only shows databases with user's data

2. **Team Scoped** (admin role in team mode)
   - Can see/manage users in their team(s)
   - Can see/manage their team(s) settings
   - Can see team-level analytics
   - Cannot see other teams

3. **Multi-Team Scoped** (super_admin role)
   - Can see/manage multiple teams
   - Can see cross-team analytics
   - Cannot create new system-level users (founder only)

4. **System Scoped** (founder_rights only)
   - Full system access (current Admin page behavior)
   - Can see all users, teams, settings
   - Can access all databases
   - Can modify system-level settings

#### Setup Wizard Enhancement

**New "Profile Mode" step in setup wizard**:

```
┌─────────────────────────────────────────┐
│  Choose Your ElohimOS Mode              │
├─────────────────────────────────────────┤
│                                         │
│  ○ Solo Mode (Personal Use)            │
│    • Just you, your data               │
│    • Full control over your profile    │
│    • Admin tab shows only your info    │
│                                         │
│  ○ Team Mode (Collaborative)           │
│    • Multiple users/teams              │
│    • Role-based permissions            │
│    • Admin access based on role        │
│                                         │
│  [Continue]                             │
└─────────────────────────────────────────┘
```

**What this controls**:
- Sets `user_mode` in user preferences
- Sets initial `profile_scope`
- Determines Admin tab behavior
- Affects permission checks across app

**Can be changed later** in Settings → Profile → Account Type

#### Settings Integration

**New section in Profile Settings → Identity**:

**Account Type**:
- Current mode: Solo / Team
- Change mode button (with migration warning)
- Scope: Self Only / Team Scoped / System Scoped (read-only, based on role)

**Migration Considerations**:
- Solo → Team: Must create/join a team first
- Team → Solo: Warning about losing team access
- Data is never deleted, just scope of admin view changes

#### Admin Page Changes

**Dynamic Sections Based on Scope**:

**Solo Mode Admin Page**:
```
Admin
├── My Profile
│   ├── User Information (read-only email, role)
│   ├── Storage Usage (my data only)
│   └── Activity Log (my actions only)
├── My Settings
│   ├── Preferences
│   ├── Security
│   └── Privacy
└── System Health
    ├── Ollama Status
    ├── Backend Status
    └── My Databases (only DBs with my data)
```

**Team Admin Page** (admin role):
```
Admin
├── My Team
│   ├── Team Members (can add/remove)
│   ├── Team Settings
│   └── Team Storage
├── Permissions
│   ├── Role Management (within team)
│   └── Access Control (team scope)
└── Analytics
    └── Team Usage Stats
```

**System Admin Page** (founder_rights):
```
Admin
├── All Users (current behavior)
├── All Teams
├── System Permissions
├── Database Health (all DBs)
├── Performance Metrics
└── Audit Logs (all)
```

### Database Schema Changes

**New columns in `users` table**:
```sql
ALTER TABLE users ADD COLUMN user_mode TEXT DEFAULT 'solo'; -- 'solo' | 'team'
ALTER TABLE users ADD COLUMN profile_scope TEXT DEFAULT 'self'; -- 'self' | 'team' | 'multi_team' | 'system'
```

**New table: `user_profile_settings`**:
```sql
CREATE TABLE user_profile_settings (
  id INTEGER PRIMARY KEY,
  user_id TEXT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'solo', -- 'solo' | 'team'
  scope TEXT NOT NULL DEFAULT 'self', -- computed from role + mode
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

### API Changes

**New endpoints**:
- `GET /api/v1/users/me/mode` - Get current user mode
- `PUT /api/v1/users/me/mode` - Change user mode (solo ↔ team)
- `GET /api/v1/users/me/scope` - Get current profile scope
- `GET /api/v1/admin/scoped` - Get admin data filtered by scope

**Modified endpoints**:
- All Admin endpoints must check `profile_scope` before returning data
- Filter results based on scope (self, team, multi-team, system)

### Frontend Components to Update

1. **NavigationRail.tsx** - Admin tab visibility logic ✅ (partially done)
2. **AdminPage.tsx** - Dynamic sections based on scope
3. **ProfileSettings/IdentitySection.tsx** - Add Account Type section
4. **SetupWizard** - Add Profile Mode selection step
5. **PermissionsUI** - Scope-aware permission displays

### Permissions to Add

New permissions for granular admin control:
- `admin.access_panel` - Can see Admin tab
- `admin.view_self` - Can view own profile (always true)
- `admin.view_team` - Can view team admin data
- `admin.view_multi_team` - Can view multiple teams
- `admin.view_system` - Can view all system data (founder only)
- `admin.manage_team_users` - Can add/remove team users
- `admin.manage_team_settings` - Can modify team settings
- `admin.manage_system` - Can modify system settings (founder only)

### Edge Cases & Considerations

**Solo user who creates a team**:
- Mode stays "solo" until they explicitly switch to "team"
- If they invite others, they get prompted to switch modes
- Switching to team mode gives them "admin" role in their team

**Team member who leaves all teams**:
- Suggested to switch back to solo mode
- If they stay in team mode with no teams, Admin tab shows nothing
- Can switch to solo mode to see self-admin view

**Founder rights user in solo mode**:
- Still sees full system (scope = system regardless of mode)
- Mode is more of a UI preference for founders

**Database health visibility**:
- Solo mode: Only show DBs with user's data (vault.db if they have vault items, chat_memory.db if they have chats, etc.)
- Team mode: Show team-relevant DBs
- System mode: Show all DBs

### Testing Requirements

- [ ] Unit tests for scope calculation logic
- [ ] API tests for scoped data filtering
- [ ] E2E test: Solo user sees only their data in Admin
- [ ] E2E test: Team admin sees only team data
- [ ] E2E test: Founder sees everything
- [ ] Migration test: Solo → Team mode transition
- [ ] Migration test: Team → Solo mode transition
- [ ] Permission tests for new admin.* permissions
- [ ] Setup wizard flow test with mode selection

### Success Criteria

- [ ] Solo users cannot see other users' data in Admin page
- [ ] Team admins can only see their team's data
- [ ] Founder rights can see everything (current behavior preserved)
- [ ] Setup wizard asks for mode preference
- [ ] Users can switch modes in Settings
- [ ] Admin tab visibility based on role + mode
- [ ] No performance degradation from scope filtering
- [ ] Clear UI indicators showing current scope
- [ ] Migration path from current "everyone sees everything" state

### Migration Strategy

**Phase 1: Database Schema** (backward compatible)
1. Add new columns (nullable, with defaults)
2. Backfill existing users:
   - If role = founder_rights → mode: team, scope: system
   - If role = admin → mode: team, scope: team
   - All others → mode: solo, scope: self

**Phase 2: Backend Scope Logic**
1. Implement scope calculation
2. Add scoped filtering to Admin endpoints
3. Add new mode/scope management endpoints
4. Update permission checks

**Phase 3: Frontend Updates**
1. Update NavigationRail admin visibility
2. Add Account Type to Profile Settings
3. Update AdminPage to show scoped sections
4. Add Setup Wizard mode selection

**Phase 4: Gradual Rollout**
1. Deploy backend changes (no UI changes yet)
2. Deploy frontend with feature flag
3. Prompt existing users to choose mode
4. Enable feature flag for all users

### Dependencies

- **Requires**:
  - Phase 2 (Backend Services refactor) for cleaner permission logic
  - Phase 4 (Frontend refactor) for AdminPage modularization
  - Existing RBAC system (phase2_permissions_rbac.py migration)
  - Existing setup wizard framework

- **Blocks**: None (standalone feature)

### Estimated Effort

- **Planning & Design**: 3 days (define all scope rules)
- **Database migrations**: 2 days (schema + backfill)
- **Backend scope logic**: 5 days (filtering, APIs, permissions)
- **Frontend AdminPage refactor**: 5 days (dynamic sections by scope)
- **Setup Wizard update**: 2 days (mode selection flow)
- **Profile Settings update**: 2 days (Account Type section)
- **Testing**: 5 days (unit, integration, E2E, migration)
- **Documentation**: 2 days (user guide, admin guide)
- **Buffer for edge cases**: 3 days
- **Total**: ~29 days (4 weeks)

### Priority Justification

**Deferred to Phase 9** because:
- Requires deep architectural thinking about scope model
- Needs careful design of solo vs team mode UX
- High complexity due to data filtering across all admin endpoints
- Risk of breaking existing admin functionality
- Should be done after core refactoring complete (Phases 1-6)
- Not blocking other features
- Current workaround: Solo users can manually ignore irrelevant admin data

### Future Enhancements (Post-Phase 9)

- **Multi-profile support**: One user, multiple personas (work, personal)
- **Profile switching**: Quick switch between profiles without logout
- **Profile-specific themes**: Different visual themes per profile
- **Profile data isolation**: Separate vaults/chats/files per profile
- **Cross-profile sharing**: Share data between your own profiles

---

**Document Version**: 1.2
**Last Updated**: 2025-11-16
**Status**: DRAFT - Awaiting team review
**Recent Changes**:
- Added Phase 8 - Stealth Labels app-wide implementation plan
- Added Phase 9 - Admin Tab RBAC & Multi-Profile System
