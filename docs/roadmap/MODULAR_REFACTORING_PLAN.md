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

---

## Detailed Refactoring Plans

### PHASE 1: Quick Wins (Data/Template Files)
**Goal**: Build momentum with low-complexity refactors
**Duration**: 2-3 days
**Risk**: LOW

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

### Rollback Plan
1. **Feature Flags**: Use flags for new module paths
2. **Gradual Migration**: Keep old code until new code proven
3. **Monitoring**: Watch error rates after each merge
4. **Quick Revert**: Ability to revert any PR within 5 minutes

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

**Document Version**: 1.0
**Last Updated**: 2025-11-16
**Status**: DRAFT - Awaiting team review
