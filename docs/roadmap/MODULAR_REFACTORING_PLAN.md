# ElohimOS Modular Refactoring Plan

**Created:** 2025-11-16
**Last Updated:** 2025-11-19
**Status:** ✅ Phase 5 COMPLETE – All settings architecture aligned and large modals refactored. Ready for Phase 6 (backend utilities).
**Version:** 4.0 (Backend + routes + core frontend + settings/modals modularized)
**Team:** Claude, User, Codex
**Priority:** HIGH - Foundation for future scalability

---

## Executive Summary

This is the **single source of truth** for refactoring ElohimOS over the next 12 weeks. All large files will be split into smaller, modular components to improve:

- **Maintainability**: Easier to understand and modify individual modules
- **Testability**: Smaller units are easier to test in isolation
- **Collaboration**: Multiple developers can work on different modules without conflicts
- **Performance**: Better code splitting and lazy loading opportunities
- **Onboarding**: New developers can understand individual modules faster

**Constraints (NON-NEGOTIABLE)**:
- ✅ No breaking changes to public HTTP APIs (routes, request/response schemas, auth flows)
- ✅ No RBAC regressions - all permission checks must remain intact
- ✅ No vault data corruption - encryption/decryption logic stays unchanged
- ✅ All existing tests must continue to pass
- ✅ Phase work is isolated - each phase can be completed and merged independently

**Current Repo State** (as of 2025-11-19):
- **Backend**: 144 Python files in `apps/backend/api/`, Phase 2–3 complete:
  - Team service fully modular (6 modules)
  - Vault service modular (`core.py` + `storage,encryption,sharing,permissions,schemas,documents,files,folders,search,automation`)
  - Chat service modular (`core.py` + `types,storage,sessions,models,hot_slots,analytics,system,ollama_ops,routing,ai_features,streaming`)
  - `main.py` now uses `app_factory.py` + `middleware/` + `startup/` + centralized `router_registry`
- **Frontend**: 220 TS/TSX components, 14 Zustand stores
  - Major workspaces modularized: `VaultWorkspace/`, `AppShell` + `useAppBootstrap`, `TeamChat/`, `WorkflowDesigner/`
  - Settings & profile: `SettingsModal` uses modular tabs; `ProfileSettings` package is source of truth for profile; `ProfileSettingsModal` is thin wrapper (62 lines); legacy `SettingsTab` (862 → 28 lines) is now a thin wrapper around `AppSettingsTab`
  - Library modals: `LibraryModal` (726 → 11 lines) and `ProjectLibraryModal` (798 → 13 lines) are fully modularized with backwards compatibility shims
- **Docs**: Consolidated to 6 core docs (most deleted in recent cleanup)
- **Architecture**: FastAPI + 8 SQLite DBs + DuckDB + Ollama + Metal 4 + React/Zustand

**References**:
- Architecture: `docs/architecture/SYSTEM_ARCHITECTURE.md`
- Permissions: `docs/architecture/PERMISSION_MODEL.md`
- Philosophy: `docs/architecture/ARCHITECTURE_PHILOSOPHY.md`

---

## Large Files Analysis

### Backend Files (Threshold: >1000 lines)

#### Critical Priority (>2000 lines)

| File | Lines | Current Responsibility | Refactoring Status |
|------|-------|------------------------|------------------------|
| ~~`api/services/team/core.py`~~ | ~~2,872~~ → **1,784** | ✅ **REFACTORED** → `services/team/{types,storage,members,invitations,roles,founder_rights}.py` (Phase 2.1 + 2.1b) | ~~HIGH~~ → **COMPLETED** |
| ~~`api/services/vault/core.py`~~ | ~~2,780~~ → **1,538** | ✅ **REFACTORED** → `services/vault/{storage,encryption,sharing,permissions,schemas,documents,files,folders,search,automation}.py` (Phase 2.2b + 2.2c, core now orchestration) | ~~HIGH~~ → **COMPLETED** |

#### High Priority (1500-2000 lines)

| File | Lines | Current Responsibility | Refactoring Status |
|------|-------|------------------------|------------------------|
| ~~`api/main.py`~~ | ~~1,920~~ → **1,017** | FastAPI app entrypoint + legacy inline endpoints (now uses `app_factory.py`, `middleware/`, `startup/`, `router_registry`) | MEDIUM → **PARTIAL (arch refactor complete)** |
| ~~`api/services/chat/core.py`~~ | ~~1,751~~ → **1,248** | ✅ **REFACTORED** → `services/chat/{types,storage,sessions,models,hot_slots,analytics,system,ollama_ops,routing,ai_features,streaming}.py` (Phase 2.3a–c) | ~~HIGH~~ → **COMPLETED** |
| ~~`api/template_library_full.py`~~ | ~~1,676~~ | ✅ **REFACTORED** → `templates/` (Phase 1.1, 13 files) | ~~LOW~~ → **COMPLETED** |
| ~~`api/routes/vault/files.py`~~ | ~~1,565~~ | ✅ **REFACTORED** → `routes/vault/files/{upload,download,management,search,metadata}.py` (Phase 3.2) | MEDIUM → **COMPLETED** |
| ~~`api/routes/team.py`~~ | ~~1,443~~ | ✅ **REFACTORED** → `routes/team/{teams,members,invitations,permissions,chat,workspaces,analytics}.py` (Phase 3.3) | MEDIUM → **COMPLETED** |

#### Medium Priority (1000-1500 lines)

| File | Lines | Current Responsibility | Refactoring Complexity |
|------|-------|------------------------|------------------------|
| ~~`api/core_nlp_templates.py`~~ | ~~1,183~~ | ✅ **REFACTORED** → `nlp/` (Phase 1.2, 13 files) | ~~LOW~~ |
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
| ~~`components/VaultWorkspace.tsx`~~ | ~~4,119~~ | ✅ **REFACTORED** → `components/VaultWorkspace/` (Toolbar, grids, modals, hooks, helpers) – original kept as backup only | MEDIUM → **COMPLETED** |
| ~~`components/VaultWorkspace/index.tsx`~~ | ~~942~~ | ✅ **REFACTORED** → `VaultWorkspace/index.tsx` + subcomponents (Phase 4.1) | LOW → **COMPLETED** |
| `components/settings/SettingsTab.tsx` | 862 | Settings tab coordination | MEDIUM |
| ~~`components/ProjectLibraryModal.tsx`~~ | ~~798~~ → **13** | ✅ **REFACTORED** → `ProjectLibraryModal/{ProjectLibraryModal,DocumentRow,TagInput,NewDocumentEditor,EditDocumentEditor,DeleteConfirmDialog,types}.tsx` (Phase 5.2) | ~~MEDIUM~~ → **COMPLETED** |
| ~~`components/ProfileSettingsModal.tsx`~~ | ~~773~~ → **62** | ✅ **REFACTORED** → Thin wrapper around `ProfileSettings/` module (Phase 5.2) | ~~MEDIUM~~ → **COMPLETED** |
| ~~`components/LibraryModal.tsx`~~ | ~~726~~ → **11** | ✅ **REFACTORED** → `LibraryModal/{LibraryModal,QueryRow,NewQueryEditor,EditQueryEditor,DeleteConfirmDialog}.tsx` (Phase 5.2) | ~~MEDIUM~~ → **COMPLETED** |
| ~~`components/TeamChatWindow.tsx`~~ | ~~725~~ | ✅ **REFACTORED** → `components/TeamChat/{TeamChatWindow,MessageList,MessageInput,EmojiPicker,types}.tsx` (Phase 4.3) | HIGH → **COMPLETED** |

#### High Priority (600-900 lines)

| File | Lines | Current Responsibility | Refactoring Complexity |
|------|-------|------------------------|------------------------|
| `components/DocumentEditor.tsx` | 660 | Document editing | MEDIUM |
| ~~`components/Automation/shared/templates.ts`~~ | ~~652~~ | ✅ **REFACTORED** → `Automation/templates/` (Phase 1.3, 5 files) | ~~LOW~~ |
| `components/CodeEditorPanel.tsx` | 593 | Code editor panel | MEDIUM |
| `components/settings/DangerZoneTab.tsx` | 587 | Danger zone settings | LOW |
| `components/Automation/index.tsx` | 585 | Automation workspace | MEDIUM |
| `components/NetworkSelector.tsx` | 580 | Network selection UI | MEDIUM |
| ~~`components/WorkflowDesigner.tsx`~~ | ~~578~~ | ✅ **REFACTORED** → `components/WorkflowDesigner/{WorkflowDesigner,StageList,StageEditor}.tsx` (Phase 4.4) | HIGH → **COMPLETED** |
| `components/Header.tsx` | 571 | Main app header | MEDIUM |
| `components/CodeEditor.tsx` | 568 | Monaco editor wrapper | MEDIUM |
| `components/VaultWorkspace/hooks.ts` | 567 | Vault custom hooks | LOW |
| `components/CodeEditorTab.tsx` | 558 | Code editor tab | MEDIUM |

#### Medium Priority (500-600 lines)

| File | Lines | Current Responsibility | Refactoring Complexity |
|------|-------|------------------------|------------------------|
| ~~`App.tsx`~~ | ~~547~~ → **186** | ✅ **REFACTORED** → `App.tsx` (flow control only) + `hooks/useAppBootstrap.ts`, `hooks/useModelPreload.ts`, `components/layout/AppShell.tsx` (Phase 4.2) | HIGH → **COMPLETED** |
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

We'll tackle this in **10 phases** (Phases 0–9), prioritizing by:
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

### PHASE 0: Docs & Roadmap Alignment
**Goal**: Align docs with current minimal structure and establish this roadmap as single source of truth
**Duration**: 1 day
**Risk**: MINIMAL

**Current State**:
- 39 docs deleted in working tree (not committed yet)
- `docs/README.md` still references deleted files (database/, development/, deployment/, monitoring/, multiple roadmaps)
- Only 6 core docs remain: README, 4 architecture docs, this roadmap

**Non-negotiable Constraints**:
- Do not recreate deleted docs
- Do not change architecture or codebase
- Keep this roadmap as the master plan

**Tasks**:

#### Task 0.1: Commit Doc Cleanup
**File**: Working tree (39 deleted files)
**Acceptance Criteria**:
- Run `git add -u docs/` to stage all deletions
- Run `git commit -m "docs: Remove deprecated/duplicate documentation (39 files)"`
- Verify: `git status docs/` shows clean
**Estimated Time**: 15 minutes
**Done When**: All doc deletions are committed to git history

#### Task 0.2: Update docs/README.md
**File**: `docs/README.md`
**Acceptance Criteria**:
- Remove all references to deleted docs (database/, development/, deployment/, monitoring/, roadmap/*)
- Update structure to reflect current 6 docs:
  - `README.md`
  - `architecture/SYSTEM_ARCHITECTURE.md`
  - `architecture/PERMISSION_MODEL.md`
  - `architecture/ARCHITECTURE_PHILOSOPHY.md`
  - `architecture/refactoring-guide.md`
  - `roadmap/MODULAR_REFACTORING_PLAN.md` (THIS FILE)
- Add prominent note: "MODULAR_REFACTORING_PLAN.md is the single source of truth for all refactoring work"
- Link to SYSTEM_ARCHITECTURE.md for invariants
- Link to PERMISSION_MODEL.md for RBAC constraints
**Estimated Time**: 30 minutes
**Done When**: `docs/README.md` accurately reflects current docs tree and has no broken links

#### Task 0.3: Verify Core Architecture Docs
**Files**:
- `docs/architecture/SYSTEM_ARCHITECTURE.md`
- `docs/architecture/PERMISSION_MODEL.md`
**Acceptance Criteria**:
- Read both files, verify they're up to date
- Note any discrepancies with current codebase
- If major discrepancies found, add TODO tasks to Phase 1 or 2 to update them
**Estimated Time**: 20 minutes
**Done When**: Both files reviewed and any TODOs documented

**Phase 0 Complete When**:
- ✅ All doc deletions committed
- ✅ docs/README.md updated and committed
- ✅ Core architecture docs verified
- ✅ This roadmap established as master plan

---

### PHASE 1: Quick Wins (Data/Template Files) ✅ COMPLETED (2025-11-17)
**Goal**: Build momentum with low-complexity refactors - split static template/data files
**Duration**: 2-3 days
**Risk**: LOW
**Status**: ✅ COMPLETED - All three tasks successfully implemented

**Outcomes**:
- Backend SQL templates: `template_library_full.py` (1,676 lines) → `templates/` package (13 files, 256 templates)
- Backend NLP templates: `core_nlp_templates.py` (1,183 lines) → `nlp/` package (13 files, 49 templates)
- Frontend Automation workflows: `shared/templates.ts` (652 lines) → `Automation/templates/` (5 files)
- Established "types + data + registry" pattern across backend and frontend
- All builds passing, behavior preserved

**Non-negotiable Constraints**:
- No changes to template functionality or SQL logic
- All imports must be updated atomically (no broken imports)
- Backend/frontend builds must pass after each task

**Success Criteria**:
- ✅ Template, NLP, and Automation template files are split into the new module structures with all imports updated
- ✅ Backend and frontend builds/tests pass with no public API or route changes
- ✅ Each new module has basic unit tests

**Phase 1 Tasks**:

#### Task 1.1: Split `api/template_library_full.py` → `api/templates/` (1,676 lines) ✅ COMPLETED
**Status**: ✅ COMPLETED (2025-11-17)
**Old**: 256 SQL templates in one massive file (`template_library_full.py`)
**New**: `templates/` package with 13 files

**Implemented Structure**:
```
api/templates/
├── __init__.py                      # Public exports (get_full_template_library, TemplateCategory, SQLTemplate)
├── types.py                         # SQLTemplate, TemplateCategory dataclasses
├── registry.py                      # FullTemplateLibrary, get_full_template_library()
├── product_enrichment.py            # Product data enrichment templates
├── attribute_extraction.py          # Attribute extraction templates
├── category_mapping.py              # Category mapping templates
├── brand_standardization.py         # Brand standardization templates
├── pricing_analysis.py              # Pricing analysis templates
├── inventory_optimization.py        # Inventory optimization templates
├── quality_validation.py            # Quality validation templates
├── competitor_analysis.py           # Competitor analysis templates
├── trend_detection.py               # Trend detection templates
└── customer_segmentation.py         # Customer segmentation templates
```

**Implementation Details**:
- 256 templates split by business domain (product enrichment, pricing, inventory, etc.)
- Registry pattern: `get_full_template_library()` builds complete library from category modules
- Consumer (`template_orchestrator.py`) now imports: `from templates import get_full_template_library, TemplateCategory, SQLTemplate`
- All template IDs and categories preserved (no behavior changes)

**Acceptance Criteria**:
- ✅ Created `apps/backend/api/templates/` directory with 13 modules
- ✅ Moved all 256 templates to appropriate category files
- ✅ Created registry pattern with `get_full_template_library()` function
- ✅ Updated imports in `template_orchestrator.py` and other consumers
- ✅ Backend runs without import errors
- ✅ No changes to SQL template logic or function signatures

**Files Touched**:
- NEW: `apps/backend/api/templates/*.py` (13 files)
- DELETE: `apps/backend/api/template_library_full.py`
- UPDATE: `apps/backend/api/template_orchestrator.py` and other consumers

**Actual Time**: ~1 day
**Completed**: 2025-11-17

---

#### Task 1.2: Split `api/core_nlp_templates.py` → `api/nlp/` (1,183 lines) ✅ COMPLETED
**Status**: ✅ COMPLETED (2025-11-17)
**Old**: Natural language intent classification and entity extraction in one monolithic file
**New**: `nlp/` package with 13 files (intent-category architecture)

**Implemented Structure** (Option A: Intent-Category Modules):
```
api/nlp/
├── __init__.py                      # Public exports (NLPTemplate, IntentCategory, CoreNLPLibrary)
├── types.py                         # NLPTemplate dataclass, IntentCategory enum
├── core.py                          # CoreNLPLibrary (classify_intent, extract_entities, get_response)
├── code_generation.py               # CODE_GENERATION intent templates
├── code_modification.py             # CODE_MODIFICATION intent templates
├── debugging.py                     # DEBUGGING intent templates
├── research.py                      # RESEARCH intent templates
├── system_operation.py              # SYSTEM_OPERATION intent templates
├── data_analysis.py                 # DATA_ANALYSIS intent templates
├── documentation.py                 # DOCUMENTATION intent templates
├── deployment.py                    # DEPLOYMENT intent templates
├── testing.py                       # TESTING intent templates
└── learning.py                      # LEARNING intent templates
```

**Implementation Details**:
- 49 NLP templates distributed across 10 `IntentCategory` modules
- Split by intent (code generation, debugging, research, etc.) rather than generic NLP tasks
- `CoreNLPLibrary` class in `core.py` provides: `classify_intent()`, `extract_entities()`, `get_response()`, `suggest_workflow()`
- Each category module exports `get_templates()` function returning list of templates for that intent
- Rationale: Intent-based split aligns with Jarvis's actual use case (understanding developer commands)

**Design Decision - Why Intent-Category Architecture?**
- Original roadmap proposed 5 generic NLP modules (entity_extraction, sentiment_analysis, text_classification, summarization, question_answering)
- Actual codebase uses intent-based architecture with `IntentCategory` enum (10 categories)
- Intent-category split is more domain-specific and matches real usage patterns
- Each module contains templates for a specific developer intent (e.g., "create a function", "fix this bug", "explain this code")

**Acceptance Criteria**:
- ✅ Created `apps/backend/api/nlp/` directory with 13 modules (types + core + 10 intent categories)
- ✅ Moved all 49 NLP templates to appropriate intent-category files
- ✅ Created `CoreNLPLibrary` class with intent classification and entity extraction
- ✅ Created public API exports via `__init__.py`
- ✅ Updated imports in consumer files
- ✅ No changes to NLP logic or template matching behavior

**Files Touched**:
- NEW: `apps/backend/api/nlp/*.py` (13 files)
- DELETE: `apps/backend/api/core_nlp_templates.py` (replaced by package)
- UPDATE: All files importing from `core_nlp_templates`

**Actual Time**: ~0.5 day
**Completed**: 2025-11-17

---

#### Task 1.3: Split `components/Automation/shared/templates.ts` → `Automation/templates/` (652 lines) ✅ COMPLETED
**Status**: ✅ COMPLETED (2025-11-17)
**Old**: Workflow template types, styles, definitions, and metadata in one 652-line file
**New**: `Automation/templates/` package with 5 files

**Implemented Structure**:
```
components/Automation/templates/
├── index.ts                    # Public entrypoint (re-exports all types and data)
├── types.ts                    # WorkflowTemplateMetadata, WorkflowTemplateDefinition interfaces
├── styles.ts                   # nodeStyles constant (5 node types: trigger, action, ai, output, condition)
├── definitions.ts              # WORKFLOW_DEFINITIONS (11 ReactFlow workflows with nodes & edges)
└── metadata.ts                 # WORKFLOW_METADATA array (display info for library)
```

**Implementation Details**:
- Split by content type: types, styles, workflow data (definitions + metadata)
- 11 workflows across 5 categories: clinic, ministry, admin, education, travel
- Workflows: clinic-intake, worship-planning, visitor-followup, small-group-coordinator, prayer-request-router, event-manager, donation-tracker, volunteer-scheduler, curriculum-builder, sunday-school-coordinator, trip-planner
- `definitions.ts` contains full ReactFlow node graphs with JSX labels and positioning
- `styles.ts` contains CSS-in-JS gradient styles for 5 node types
- Consumers now import from `./Automation/templates` instead of `./Automation/shared/templates`

**Acceptance Criteria**:
- ✅ Created `apps/frontend/src/components/Automation/templates/` directory with 5 modules
- ✅ Moved all workflow types, styles, definitions, and metadata to appropriate files
- ✅ Created `types.ts` with `WorkflowTemplateMetadata` and `WorkflowTemplateDefinition`
- ✅ Created `index.ts` with public exports
- ✅ Updated imports in `WorkflowBuilder.tsx`, `hooks.ts`, `types.ts`
- ✅ Frontend builds without errors: `npm run build` passed (1.98s)
- ✅ No changes to template structure or behavior

**Files Touched**:
- NEW: `apps/frontend/src/components/Automation/templates/*.ts` (5 files)
- DELETE: `apps/frontend/src/components/Automation/shared/templates.ts`
- UPDATE: `components/WorkflowBuilder.tsx`, `Automation/hooks.ts`, `Automation/types.ts`

**Actual Time**: ~0.5 day
**Completed**: 2025-11-17

---

**Phase 1 Complete When**:
- ✅ All 3 tasks (1.1, 1.2, 1.3) completed (DONE 2025-11-17)
- ✅ Backend tests pass: `pytest apps/backend/api/` (VERIFIED)
- ✅ Frontend builds: `npm run build` (PASSED - 1.98s)
- ✅ No import errors or broken templates (VERIFIED)

**Phase 1 Summary**:
Phase 1 successfully established the "types + data + registry" pattern across backend and frontend:
- Backend SQL templates: Reduced `template_library_full.py` from 1,676 lines to 13 focused modules
- Backend NLP templates: Reduced `core_nlp_templates.py` from 1,183 lines to 13 intent-category modules
- Frontend Automation workflows: Reduced `shared/templates.ts` from 652 lines to 5 content-type modules
- Total reduction: 3,511 lines → 31 modular files
- Zero behavior changes, all builds passing

---

### PHASE 2: Backend Services (Critical Path)
**Goal**: Refactor largest backend service files
**Duration**: 1 week
**Risk**: MEDIUM-HIGH
**Status**: 🔄 IN PROGRESS - Phase 2.1 (Team members + invites) COMPLETED (2025-11-17)

**Success Criteria**:
- Team, Vault, and Chat services are decomposed into focused submodules with `core.py` files acting only as orchestration layers.
- All related API endpoints behave identically in integration/E2E tests (permissions, audit trails, and data semantics unchanged).

**Testing Requirements**:
- Unit tests for each new service submodule.
- Integration tests for critical team, vault, and chat workflows, including permission checks and audit logging.

#### 2.1 Refactor `api/services/team/core.py` (2,872 lines) - ✅ COMPLETED (Phase 2.1 + 2.1b)
**Status**: ✅ COMPLETE - Members, Invitations, Roles/Promotions, Founder Rights all extracted
**Current**: Fully modular team service with clean separation of concerns
**Target Structure**:
```
api/services/team/
├── __init__.py                 # Public API exports
├── core.py                     # Orchestration layer (1,784 lines, orchestrates all modules)
├── members.py                  # Member management ✅ COMPLETED
├── invitations.py              # Invitation handling ✅ COMPLETED
├── roles.py                    # Roles & promotions ✅ COMPLETED (Phase 2.1b)
├── founder_rights.py           # Founder Rights (God Rights) ✅ COMPLETED (Phase 2.1b)
├── storage.py                  # Database operations ✅ COMPLETED (1,005 lines)
└── types.py                    # Type definitions ✅ COMPLETED
```

**Deferred** (not in critical path):
- `permissions.py` - Workflow/queue permissions (Phase 5.2/5.3 features)
- `chat.py` - Team chat operations (low priority)
- `workspaces.py`, `notifications.py`, `analytics.py` - Future features
```

**Phase 2.1 Completion Summary (2025-11-17)**:

✅ **Completed Modules**:
- `types.py` (45 lines) - Constants, type aliases (SuccessResult, SuccessResultWithId), team roles, permission types
- `storage.py` (474 lines) - Database access layer with 23 functions for team/member/invite CRUD
- `members.py` (296 lines) - Member operations: get/join/update role/job roles/last seen tracking
- `invitations.py` (182 lines) - Invite lifecycle: generation (XXXXX-XXXXX-XXXXX format), validation, brute-force protection
- `core.py` reduced from 2,872 → 2,461 lines (-411 lines, -14%)

✅ **Methods Delegated** (17 total):
- Member methods (11): `get_team_members`, `get_user_teams`, `join_team`, `update_member_role`, `get_days_since_joined`, `update_last_seen`, `update_job_role`, `get_member_job_role`, `count_role`, `count_super_admins`, `get_team_size`
- Invitation methods (6): `generate_invite_code`, `get_active_invite_code`, `regenerate_invite_code`, `validate_invite_code`, `record_invite_attempt`, `check_brute_force_lockout`

✅ **Runtime Validation** (smoke tests passed):
- Team creation with invite code generation
- Invite code validation and member joining
- Member role updates (member → admin)
- Team member/user teams retrieval
- Brute-force protection (10 failed attempts → lockout)

---

**Phase 2.1b Completion Summary (2025-11-17)**:

✅ **Completed Modules**:
- `roles.py` (490 lines) - Role/promotion orchestration: auto-promotion (7-day guest→member), instant promotion (real password), delayed promotion (21-day decoy password delay), temporary promotions (offline super admin failsafe)
- `founder_rights.py` (204 lines) - Founder Rights (God Rights) management: grant/revoke/check operations, auth key hashing (SHA256), delegation tracking, audit trail
- `storage.py` updated (+531 lines) - Added 17 DB functions for 3 tables:
  * `delayed_promotions` (4 functions) - Schedule/execute delayed guest→member promotions
  * `temp_promotions` (6 functions) - Offline super admin failsafe tracking
  * `god_rights_auth` (7 functions) - Founder Rights authorization & audit
- `core.py` updated (-1,236 lines refactored) - 19 methods now delegate to roles.py and founder_rights.py

✅ **Methods Delegated** (19 total):
- Role methods (11): `get_max_super_admins`, `can_promote_to_super_admin`, `check_auto_promotion_eligibility`, `auto_promote_guests`, `instant_promote_guest`, `schedule_delayed_promotion`, `execute_delayed_promotions`, `promote_admin_temporarily`, `get_pending_temp_promotions`, `approve_temp_promotion`, `revert_temp_promotion`
- Founder Rights methods (5): `grant_god_rights`, `revoke_god_rights`, `check_god_rights`, `get_god_rights_users`, `get_revoked_god_rights`
- Helper methods (3): `count_role`, `count_super_admins`, `get_team_size` (used by roles.py logic)

✅ **Runtime Validation** (smoke tests passed):
- Super admin limit calculation (tiered: 1-5 based on team size)
- Guest auto-promotion eligibility (7-day tracking)
- Delayed promotion scheduling (21-day decoy password safety delay)
- Founder Rights grant/revoke with delegator verification
- Zero `self.conn` usage in refactored code paths

🔄 **Remaining Deferred Items** (not critical path):
- Workflow permissions (Phase 5.2) - stays in core.py for now
- Queue operations (Phase 5.3) - stays in core.py for now
- Team Vault operations (Phase 6.2) - handled by vault service

**Pattern Established**:
- "Manager parameter" pattern for methods needing access to other TeamManager methods (e.g., `update_member_role_impl(manager, ...)`)
- Per-function database connections via `_get_app_conn()` (no persistent connection state)
- Backward-compatible public API - no changes to `__init__.py` exports or route imports

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

#### 2.2 Refactor `api/services/vault/core.py` (2,780 lines) - ✅ COMPLETED (Phase 2.2b + 2.2c)
**Status**: ✅ COMPLETE – Storage, crypto, sharing, permissions, schemas, documents, files, folders, search, and automation all extracted; `core.py` is now orchestration-only.
**Current**: Vault service is fully modular; all DB/file logic lives in dedicated modules and is reused by routes.
**Achieved Structure**:
```
api/services/vault/
├── __init__.py                 # Public API exports (74 lines)
├── core.py                     # Orchestration only (~1,538 lines → shrinking)
├── storage.py                  # Database operations ✅ COMPLETED (666 lines)
├── encryption.py               # Crypto helpers ✅ COMPLETED (61 lines)
├── sharing.py                  # Sharing utilities ✅ COMPLETED (46 lines)
├── permissions.py              # Permission helpers ✅ COMPLETED (65 lines)
├── schemas.py                  # Schema definitions ✅ COMPLETED (67 lines)
├── documents.py                # Document CRUD ✅ COMPLETED
├── files.py                    # File upload/list/delete/versioning/trash ✅ COMPLETED
├── folders.py                  # Folder CRUD/move/delete ✅ COMPLETED
├── search.py                   # Advanced file search ✅ COMPLETED
└── automation.py               # Pinned files, folder colors, export ✅ COMPLETED
```

**Phase 2.2 Completion Summary**:

✅ **Completed Modules**:
- `storage.py` (666 lines) - Database access layer for vault documents, files, folders with `_get_app_conn()` pattern
- `encryption.py` (61 lines) - Encryption/decryption helpers using Fernet (symmetric encryption)
- `sharing.py` (46 lines) - Vault sharing utilities
- `permissions.py` (65 lines) - Vault permission helpers
- `schemas.py` (67 lines) - Vault schema/validation definitions
 - `documents.py` – Document-level CRUD operations (user/team scoped)
 - `files.py` – File upload/download/list/delete, versioning, trash, secure delete
 - `folders.py` – Folder creation/list/rename/delete with cascading path updates
 - `search.py` – Advanced search across files (tags, date/size/mime filters)
 - `automation.py` – Pinned files, folder colors, export helpers

✅ **Pattern Applied**:
- Per-function database connections via `_get_app_conn()` (same as Team service)
- Encryption layer separated from business logic
- All DB operations go through storage.py
Routes now depend only on the service API; all heavy logic is encapsulated in the `api.services.vault` package.

#### 2.3 Refactor `api/services/chat/core.py` (1,751 lines) - ✅ COMPLETED (Phase 2.3a–c)
**Status**: ✅ COMPLETE – Sessions, storage, model management, Ollama ops, routing, AI features, analytics, and system monitoring have all been extracted; `core.py` is primarily orchestration and glue.
**Current**: Chat service is fully modular; session/message persistence, streaming, routing, analytics, and system/status concerns live in dedicated modules.
**Achieved Structure**:
```
api/services/chat/
├── __init__.py                 # Public API exports (232 lines)
├── core.py                     # Orchestration + high-level chat logic (~1,248 lines and shrinking)
├── types.py                    # Type definitions ✅ COMPLETED (123 lines)
├── storage.py                  # Database operations ✅ COMPLETED (410 lines)
├── sessions.py                 # Session orchestration ✅ COMPLETED (360 lines)
├── streaming.py                # Ollama streaming client ✅ COMPLETED (154 lines)
├── models.py                   # Model listing/status/preload/unload ✅ COMPLETED
├── hot_slots.py                # Hot slot management ✅ COMPLETED
├── analytics.py                # Semantic search + analytics helpers ✅ COMPLETED
├── system.py                   # Health, ANE stats, token counts, router stats ✅ COMPLETED
├── ollama_ops.py               # Ollama server lifecycle + config ✅ COMPLETED
├── routing.py                  # ANE/adaptive routing decisions ✅ COMPLETED
└── ai_features.py              # Tool execution (chat, data, system) based on routing ✅ COMPLETED
```

**Phase 2.3 Completion Summary** (2025-11-17–18):

✅ **Completed Modules**:
- `types.py` (123 lines) - Enums (RouterMode, MessageRole), type aliases (SessionDict, MessageDict), constants (DEFAULT_MODEL, MAX_CONTEXT_MESSAGES, HOT_SLOT_COUNT)
- `storage.py` (410 lines) - Database access layer wrapping NeutronChatMemory:
  * Session ops (7 functions): create/get/list/delete/update_model/update_title/set_archived
  * Message ops (4 functions): add_message, update_summary, get_messages, get_summary
  * Document ops (3 functions): has_documents, store_document_chunks, search_document_chunks
  * Search/Analytics (2 functions): search_messages_semantic, get_analytics
- `sessions.py` (360 lines) - Session lifecycle and context orchestration:
  * Session lifecycle (5 functions): create_new_session, get_session_by_id, list_user_sessions, delete_session_by_id, update_session_metadata
  * Context assembly (1 function): get_conversation_context (handles history truncation, summary inclusion)
  * Message handling (2 functions): save_message_to_session, auto_title_session_if_needed
  * Document ops (3 functions): check_session_has_documents, search_session_documents, store_uploaded_documents
- `core.py` updated to delegate:
  * Session CRUD and message persistence to `sessions.py`
  * Model listing/status/preload/unload to `models.py`
  * Hot slot management to `hot_slots.py`
  * Ollama server lifecycle/config to `ollama_ops.py`
  * Analytics and semantic search to `analytics.py`
  * Health/ANE/token counts/router stats to `system.py`
  * Routing decisions to `routing.py`
  * Tool execution (chat/data/system) to `ai_features.py`

✅ **Pattern Applied**:
- Thread-local SQLite connections via NeutronChatMemory (WAL mode, per-thread connections)
- Storage layer wraps existing `chat_memory.py` (16 DB functions)
- Sessions layer orchestrates lifecycle + context assembly
- Core.py delegates session CRUD, streaming, AI routing, analytics, and system concerns to dedicated modules

**Dependencies**:
- `api/routes/chat/` (28 endpoints)
- `api/chat_memory.py` (891 lines - NeutronChatMemory, stays as DB layer)

**Breaking Changes**: None – all public APIs and routes are unchanged; implementation is modularized behind the same surface.

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
**Status**: ✅ COMPLETED – `main.py` is now a thin entrypoint that delegates app creation and setup to `app_factory.py`, `middleware/`, `startup/`, and `router_registry`.
**Current (pre-refactor baseline)**: Everything in one file (app setup, middleware, routes, startup, shutdown)
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
**Status**: ✅ COMPLETED – Vault file routes are split into `files/{upload,download,management,search,metadata}.py` and aggregated via `routes/vault/__init__.py`.
**Current (pre-refactor baseline)**: 30+ endpoints in one file
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
**Status**: ✅ COMPLETED – Team routes now live in `routes/team/{teams,members,invitations,permissions,chat,workspaces,analytics}.py` and are aggregated via `routes/team/__init__.py`.
**Current (pre-refactor baseline)**: 52 endpoints in one file
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
**Status**: ✅ COMPLETED – `VaultWorkspace`, `App` shell, `TeamChat`, and `WorkflowDesigner` have been modularized into focused subcomponents/hooks while preserving behavior.

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
**Goal**: Modularize settings and modal components, with a focus on reusing the new `ProfileSettings` package and untangling large library/profile modals.
**Duration**: 5 days
**Risk**: LOW-MEDIUM

**Success Criteria**:
- Legacy settings entrypoints (`SettingsTab`, `ProfileSettingsModal`) become thin coordinators/wrappers around the new modular settings components.
- Large modal components (library/profile modals) are decomposed into layout + tab/modal subcomponents without changing behavior.
- All settings panels and modals render and function as before in manual/E2E checks.

**Testing Requirements**:
- UI regression tests or scripted/manual checklists for each settings tab and modal.

#### 5.1 Align `SettingsTab` with new Settings architecture ✅ **COMPLETED**
**Status**: ✅ COMPLETED (2025-11-19)
**Old**: Monolithic settings tab coordinator (~~862 lines~~) duplicating app settings logic.
**New**: ~~`components/settings/SettingsTab.tsx`~~ (862 → **28 lines**) - Thin, deprecated wrapper around `AppSettingsTab`.

**Implementation**:
- `SettingsTab.tsx` is now a minimal wrapper component:
  - Clear `@deprecated` JSDoc comment explaining the new architecture
  - Exposes the same `SettingsTabProps { activeNavTab: NavTab }` interface
  - Delegates entirely to `AppSettingsTab`, which is the single source of truth for app settings
  - No business logic remains - all logic lives in modular tabs

- New modular settings architecture:
  - `components/SettingsModal.tsx` - Main settings modal with sidebar navigation
  - `components/settings/AppSettingsTab.tsx` - App settings (single source of truth)
  - `components/settings/AdvancedTab.tsx` - Advanced settings
  - `components/settings/ChatTab.tsx` / `ChatSettingsContent.tsx` - Chat/AI settings
  - `components/settings/ModelsTab.tsx` - Model management
  - `components/settings/AutomationTab.tsx` - Automation settings
  - `components/ProfileSettings/` - Profile settings module

**Impact**:
- Legacy imports of `SettingsTab` (if any existed) would continue to work via the wrapper
- New code should import `SettingsModal` or individual tab components directly
- No usages of `SettingsTab` found in the codebase - component is purely legacy
- Build succeeds with no errors

**Dependencies**: `AppSettingsTab`, `SettingsModal`, `AdvancedTab`, `ChatTab`, `ProfileSettings`
**Breaking Changes**: None - thin wrapper maintains backwards compatibility

#### 5.2 Refactor Large Modals (Profile & Library)
**Files**:
- `components/ProjectLibraryModal.tsx` (798 lines)
- ~~`components/ProfileSettingsModal.tsx`~~ (~~773~~ → **62 lines**) ✅ **COMPLETED**
- ~~`components/LibraryModal.tsx`~~ (~~726~~ → **11 lines**) ✅ **COMPLETED**

**ProfileSettingsModal** ✅ **COMPLETED**:
- `ProfileSettings` is now a modular package under `components/ProfileSettings/` with:
  - `index.tsx` entrypoint
  - Sections: `IdentitySection`, `SecuritySection`, `CloudSection`, `UpdatesSection`, `PrivacySection`, `DangerZoneSection`
  - Hooks: `useProfileData`, `useProfileForm`, `useBiometricSetup`
- `ProfileSettingsModal.tsx` has been refactored to a **thin modal wrapper** (62 lines):
  - Renders standard modal chrome (title bar, close button, ESC-to-close behavior).
  - Hosts `<ProfileSettings />` as its body content.
  - Preserves all existing props and external behavior (open/close callbacks, size, keyboard handling).
  - Added `CloudSection` to support the Cloud & SaaS tab from the legacy modal.

**LibraryModal** ✅ **COMPLETED**:
- Original `components/LibraryModal.tsx` (726 lines) has been split into a focused module structure:
  - `components/LibraryModal/LibraryModal.tsx` (~291 lines) – orchestrator component:
    - Manages query list, selection, create/edit/delete flows, and interactions with the editor.
  - `components/LibraryModal/QueryRow.tsx` (~123 lines) – single query row with actions.
  - `components/LibraryModal/NewQueryEditor.tsx` (~121 lines) – “new query” form/editor.
  - `components/LibraryModal/EditQueryEditor.tsx` (~136 lines) – “edit existing query” form/editor.
  - `components/LibraryModal/DeleteConfirmDialog.tsx` (~49 lines) – delete confirmation dialog.
  - `components/LibraryModal/index.tsx` (~12 lines) – public barrel export.
  - `components/LibraryModal.tsx` (~11 lines) – backwards compatibility shim that re-exports from `LibraryModal/`.
- Behavior is unchanged:
  - All query CRUD flows, search/filter, and interactions with the SQL editor work as before.
  - Public imports like `import LibraryModal from '@/components/LibraryModal'` still function.

**ProjectLibraryModal – Target Structure** (NEXT):
```
components/ProjectLibraryModal/
├── index.tsx                   # Modal entrypoint (composition only)
├── ProjectLibraryModal.tsx     # Orchestrator (selection + routing)
├── QueryRow.tsx                # Project query row with actions
├── NewQueryEditor.tsx          # Create project-scoped query
├── EditQueryEditor.tsx         # Edit project-scoped query
├── DeleteConfirmDialog.tsx     # Confirm deletion
└── hooks/
    ├── useProjectLibrary.ts    # Project-scoped fetching + filters
    └── useProjectSelection.ts  # Selection state + keyboard nav
```

**Refactoring Steps**:
1. **ProjectLibraryModal** ✅ **COMPLETED**:
   - ✅ Created `components/ProjectLibraryModal/` directory.
   - ✅ Extracted DocumentRow component (document list item with tags and actions).
   - ✅ Extracted TagInput component (tag management with hash pills, ENTER-to-add, hover-to-remove).
   - ✅ Extracted NewDocumentEditor component (create new document with Monaco editor, tags, file type).
   - ✅ Extracted EditDocumentEditor component (edit existing document).
   - ✅ Extracted DeleteConfirmDialog component (type DELETE to confirm).
   - ✅ Extracted types.ts for shared ProjectDocument interface.
   - ✅ Refactored ProjectLibraryModal.tsx into ProjectLibraryModal/ProjectLibraryModal.tsx (orchestrator).
   - ✅ Created backwards compatibility shim at original location.
   - ✅ Preserved all behaviors: tag search, .md/.txt upload, bulk ZIP export, onLoadDocument callback.

**Dependencies**: User/profile stores, library/project library stores
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
**Status**: ✅ COMPLETED (2025-11-19)

**Old Structure**:
- permission_engine.py (~1052 lines) - Core RBAC engine
- services/permissions.py (~1050 lines) - Service layer with inline logic
- permissions_admin.py (~1077 lines) - Legacy admin router
- permission_layer.py (~757 lines) - CLI permission layer (unchanged)

**New Structure**:
api/permissions/ package (modular):
- types.py - PermissionLevel, UserPermissionContext
- hierarchy.py - LEVEL_HIERARCHY
- storage.py - DB connection helpers
- engine.py (836 lines) - PermissionEngine class
- decorators.py (172 lines) - require_perm, require_perm_team
- admin.py (1040 lines) - Admin/service functions
- __init__.py - Public API exports

Compatibility layers:
- permission_engine.py (1052 → 73 lines) - Shim re-exporting from api.permissions
- services/permissions.py (1050 → 292 lines) - Thin façade delegating to api.permissions.admin
- permissions_admin.py - Deprecated with clear notice (router not registered)

**Key Achievements**:
- Eliminated ~1700 lines of duplicate code
- Single source of truth: api.permissions package
- Backwards compatible - all existing imports work
- Import validation passes ✓
- No RBAC behavior changes

**Dependencies**: Nearly all routes
**Breaking Changes**: None (decorator API stays same)

#### 6.2 Refactor Code Editor Files ✅ COMPLETED
**Files**:
- `api/code_editor_service.py` (1,064 → 564 lines) - 47% reduction
- `api/code_operations.py` (1,036 → 891 lines) - 14% reduction
- Total: **644 lines removed from routers**

**Final Structure**:
```
api/services/code_editor/
├── __init__.py              (192 lines) - Public API exports
├── models.py                (106 lines) - All Pydantic models
├── security.py              (88 lines)  - Path security & traversal prevention
├── db_workspaces.py         (251 lines) - Database CRUD operations
├── file_tree.py             (68 lines)  - Tree builder
├── disk_scan.py             (69 lines)  - Directory scanner with language detection
├── diff_service.py          (119 lines) - Diff generation with truncation
├── fs_workspace.py          (112 lines) - Workspace filesystem helpers
├── fs_diff.py               (24 lines)  - FS diff helper
└── fs_write.py              (161 lines) - Write/delete with risk assessment & rate limiting
```
**Total service package**: 1,190 lines

**Key Achievements**:
- Separated business logic from HTTP layer
- Routers now handle: HTTP, auth, audit logging only
- Services handle: workspace management, file operations, diffs, security, risk assessment
- Preserved all security checks: path validation, risk assessment, rate limiting
- Maintained backwards compatibility with existing routes
- Import validation passed ✓

**Dependencies**: Code workspace routes
**Breaking Changes**: None

#### 6.3 Refactor Other Large Files

**6.3a: P2P Chat Service ✅ COMPLETED**

**File**:
- `api/p2p_chat_service.py` (1,151 → 41 lines) - 96% reduction

**Final Structure**:
```
api/services/p2p_chat/
├── __init__.py          (38 lines)   - Public API exports
├── types.py             (16 lines)   - Protocol constants & config
├── storage.py           (429 lines)  - SQLite DB operations (peers, channels, messages, file transfers, keys)
├── encryption.py        (241 lines)  - E2E encryption integration & safety numbers
├── network.py           (509 lines)  - libp2p host, mDNS discovery, stream handlers, auto-reconnect
├── channels.py          (134 lines)  - Channel operations (create/list/get)
├── messages.py          (192 lines)  - Message send/retrieve with E2E encryption
├── files.py             (110 lines)  - File transfer operations (metadata, progress)
└── service.py           (333 lines)  - Main orchestrator
```
**Total service package**: 2,002 lines

**Key Achievements**:
- Separated networking, encryption, storage, and business logic
- Preserved all E2E encryption behavior: device keys, peer keys, safety number tracking
- Preserved libp2p networking: mDNS discovery, auto-reconnect, heartbeat
- Maintained behavior when libp2p not installed (LIBP2P_AVAILABLE gating)
- Router (p2p_chat_router.py) continues using same public API
- Import validation passed ✓
- No breaking changes

**6.3b: Admin Service ✅ COMPLETED**

**File**:
- `api/admin_service.py` (1,049 → 494 lines) - 53% reduction

**New Service Module**:
- `api/services/admin_support.py` (783 lines) - Founder Rights support capabilities

**Responsibilities Moved to admin_support.py**:
- User metadata operations: `list_all_users()`, `get_user_details()`
- Chat metadata operations: `get_user_chats()`, `list_all_chats()`
- Account remediation: `reset_user_password()`, `unlock_user_account()`
- Vault status metadata: `get_vault_status()` (document counts only, no decrypted content)
- Device overview metrics: `get_device_overview_metrics()`
- Workflow metadata: `get_user_workflows()` (workflows and work_items)
- Audit log operations: `get_audit_logs()`, `export_audit_logs()`
- DB helpers: `get_admin_db_connection()`, `_get_memory()`, `_get_auth_service()`

**admin_service.py Now Handles**:
- HTTP routing and FastAPI integration
- Security enforcement: `require_founder_rights`, `@require_perm` decorators
- Audit logging via `audit_logger`
- Rate limiting (device/overview endpoint: 20/min production, 300/min dev)
- Request/response handling and HTTPException raising

**Key Achievements**:
- Clear separation: routers handle HTTP/auth/audit, services handle business logic
- Preserved all Founder Rights security checks
- Preserved Salesforce model: admins can manage accounts but NOT see encrypted user data
- No vault content exposure: only metadata (document counts, last access time)
- Import validation passed ✓
- No breaking changes to /api/v1/admin/* endpoints

**Existing Admin Files** (unchanged):
- `api/services/admin.py` (272 lines) - "Danger Zone" operations (reset/uninstall/clear/export)
- `api/routes/admin.py` (149 lines) - Router for "Danger Zone" endpoints

**Remaining Files**:
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

## 🚀 IMMEDIATE EXECUTION PLAN - Next 3 Weeks

This section breaks down the highest-priority work into weekly sprints with concrete, bite-sized tasks.

### **WEEK 1: Phase 0 + Phase 1 Start**
**Goal**: Clean docs, align roadmap, begin template splits

#### Day 1 (Monday) - Phase 0 Complete
- [ ] **Morning**: Task 0.1 - Commit doc cleanup (39 files)
  - `git add -u docs/`
  - `git commit -m "docs: Remove deprecated/duplicate documentation (39 files)"`
  - `git push`
- [ ] **Afternoon**: Task 0.2 - Update docs/README.md
  - Rewrite docs/README.md to reflect 6-doc structure
  - Remove all broken links
  - Add "MODULAR_REFACTORING_PLAN.md is source of truth" note
  - Commit: `git commit -m "docs: Update README to reflect current minimal docs structure"`
- [ ] **End of Day**: Task 0.3 - Verify architecture docs
  - Read SYSTEM_ARCHITECTURE.md, PERMISSION_MODEL.md
  - Note any TODOs
  - **Phase 0 DONE ✅**

#### Day 2-3 (Tuesday-Wednesday) - Task 1.1: Template Library Split
- [ ] **Day 2 Morning**: Create `apps/backend/api/templates/` structure
  - Create directory + 10 category files
  - Copy all 256 templates to appropriate modules
- [ ] **Day 2 Afternoon**: Create template registry in `__init__.py`
  - Build dict: `{'template_name': func, ...}`
  - Test import: `from api.templates import get_template`
- [ ] **Day 3 Morning**: Update all imports
  - Find: `grep -r "template_library_full" apps/backend/api/`
  - Replace imports in all consumers
- [ ] **Day 3 Afternoon**: Test + commit
  - Run: `pytest apps/backend/api/ -v`
  - Commit: `git commit -m "refactor(backend): Split template_library_full.py into modular templates/ (Phase 1.1)"`
  - **Task 1.1 DONE ✅**

#### Day 4 (Thursday) - Task 1.2: NLP Templates Split
- [ ] **Morning**: Create `apps/backend/api/nlp/` structure
  - 5 modules: patterns, intent_classifier, entity_extractor, template_matcher, sql_generator
  - Move all NLP code
- [ ] **Afternoon**: Update imports + test
  - Find: `grep -r "core_nlp_templates" apps/backend/api/`
  - Replace imports
  - Test: `pytest apps/backend/api/ -k nlp -v`
  - Commit: `git commit -m "refactor(backend): Split core_nlp_templates.py into nlp/ module (Phase 1.2)"`
  - **Task 1.2 DONE ✅**

#### Day 5 (Friday) - Task 1.3: Automation Templates Split
- [ ] **Morning**: Create `apps/frontend/src/components/Automation/templates/`
  - 6 modules: index, types, data-processing, api-integrations, file-operations, notifications, scheduling
  - Move all automation template data
- [ ] **Afternoon**: Update imports + build
  - Update `components/Automation/index.tsx`
  - Run: `npm run build`
  - Commit: `git commit -m "refactor(frontend): Split Automation templates into modular structure (Phase 1.3)"`
  - **Task 1.3 DONE ✅**
  - **PHASE 1 COMPLETE ✅**

**Week 1 End State**:
- ✅ Docs cleaned and aligned
- ✅ 3 large template files split into 21 modular files
- ✅ All tests passing
- ✅ Ready for Phase 2

---

### **WEEK 2: Phase 2 Start - Backend Services (Team)**
**Goal**: Refactor `api/services/team/core.py` (2,872 lines → 9 modules)

#### Day 6-7 (Monday-Tuesday) - Task 2.1.1-2.1.3: Team Service Foundation
- [ ] **Day 6**: Create types.py + storage.py
  - Extract all data models, type hints, Pydantic schemas → `types.py`
  - Extract all DB operations (CRUD for teams table) → `storage.py`
  - Test: Imports work, no circular dependencies
- [ ] **Day 7**: Extract members.py + invitations.py
  - Move member management logic (~400 lines) → `members.py`
  - Move invitation logic (~300 lines) → `invitations.py`
  - Update imports in `core.py`
  - Test: `pytest apps/backend/api/routes/team.py -k member -v`

#### Day 8-9 (Wednesday-Thursday) - Task 2.1.4-2.1.6: Team Permissions + Chat
- [ ] **Day 8**: Extract permissions.py + workspaces.py
  - Move team permissions logic (~350 lines) → `permissions.py`
  - Move workspace management (~300 lines) → `workspaces.py`
  - Cross-check with `docs/architecture/PERMISSION_MODEL.md`
- [ ] **Day 9**: Extract chat.py + notifications.py
  - Move team chat operations (~400 lines) → `chat.py`
  - Move notification logic (~250 lines) → `notifications.py`
  - Test: `pytest apps/backend/api/routes/team.py -k chat -v`

#### Day 10 (Friday) - Task 2.1.7-2.1.8: Team Analytics + Core Reduction
- [ ] **Morning**: Extract analytics.py
  - Move team analytics (~200 lines) → `analytics.py`
- [ ] **Afternoon**: Reduce core.py to orchestration
  - `core.py` should now be ~200 lines (orchestration only)
  - Update all imports in `api/routes/team.py`
  - Run full test suite: `pytest apps/backend/api/services/team/ -v`
  - Commit: `git commit -m "refactor(backend): Split team/core.py into 9 modular services (Phase 2.1)"`
  - **Task 2.1 (Team Service) DONE ✅**

**Week 2 End State**:
- ✅ Team service refactored (2,872 lines → 9 files, ~300 lines each)
- ✅ All team endpoints tested and working
- ✅ Ready to tackle Vault service

---

### **WEEK 3: Phase 2 Continue - Backend Services (Vault)**
**Goal**: Refactor `api/services/vault/core.py` (2,780 lines → 11 modules)

#### Day 11-12 (Monday-Tuesday) - Task 2.2.1-2.2.4: Vault Foundation + Files
- [ ] **Day 11**: Create types.py + storage.py + encryption.py
  - Extract vault data models → `types.py`
  - Extract DB operations → `storage.py`
  - Extract crypto operations (~400 lines) → `encryption.py`
  - **CRITICAL**: No changes to encryption logic (vault data corruption risk!)
- [ ] **Day 12**: Extract files.py + folders.py
  - Move file operations (~500 lines) → `files.py`
  - Move folder operations (~300 lines) → `folders.py`
  - Test: `pytest apps/backend/api/routes/vault/ -k file -v`

#### Day 13-14 (Wednesday-Thursday) - Task 2.2.5-2.2.8: Vault Documents + Sharing
- [ ] **Day 13**: Extract documents.py + sharing.py
  - Move document operations (~400 lines) → `documents.py`
  - Move sharing logic (~400 lines) → `sharing.py`
  - Cross-check with RBAC permission checks
- [ ] **Day 14**: Extract automation.py + search.py
  - Move automation rules (~300 lines) → `automation.py`
  - Move vault search (~200 lines) → `search.py`
  - Test: `pytest apps/backend/api/routes/vault/ -k search -v`

#### Day 15 (Friday) - Task 2.2.9-2.2.10: Vault WebSocket + Core Reduction
- [ ] **Morning**: Extract websocket.py
  - Move WebSocket handlers (~200 lines) → `websocket.py`
- [ ] **Afternoon**: Reduce core.py to orchestration
  - `core.py` should now be ~200 lines
  - Update all imports in `api/routes/vault/`
  - Run full vault test suite: `pytest apps/backend/api/services/vault/ -v`
  - Test vault encryption/decryption still works (critical!)
  - Commit: `git commit -m "refactor(backend): Split vault/core.py into 11 modular services (Phase 2.2)"`
  - **Task 2.2 (Vault Service) DONE ✅**

**Week 3 End State**:
- ✅ Vault service refactored (2,780 lines → 11 files, ~250 lines each)
- ✅ All vault endpoints tested and working
- ✅ Encryption/decryption verified (no data corruption)
- ✅ 2/3 of Phase 2 complete
- ✅ Ready for Chat service refactor in Week 4

---

## NEXT PRIORITIES (Week 4+)

**Week 4**: Complete Phase 2 (Chat service refactor)
**Week 5**: Phase 3 (main.py + route files)
**Week 6-7**: Phase 4 (Frontend core components)
**Week 8**: Phase 5 (Settings & modals)
**Week 9**: Phase 6 (Backend utilities)
**Week 10-12**: Phase 7 (Packages - optional), Phases 8-9 (deferred features)

**Key Metrics to Track**:
- Lines of code per file (target: <800 backend, <500 frontend)
- Test coverage (target: >80% for new modules)
- Build time (target: <30s)
- PR review time (target: <1 hour for refactor PRs)

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

## Phase 10 (Optional): Admin Dashboard Modernization - Real-Time Monitoring & Analytics
**Status**: Post-Phase 9 Enhancement (Optional)
**Priority**: DEFERRED - Can be implemented after Phase 9 RBAC system is complete
**Note**: This phase extends the Admin RBAC work from Phase 9 with real-time monitoring and analytics features.

### Overview

Transform the Admin tab from a basic system overview into a **production-grade administrative dashboard** with real-time monitoring, comprehensive analytics, predictive insights, and proactive alerting. This phase addresses the current limitations where admin capabilities are scattered across multiple tabs with limited visibility, no real-time updates, and minimal actionable insights.

**Relationship to Phase 9**: Phase 9 establishes the RBAC foundation and multi-profile system for the Admin tab. Phase 10 builds on that foundation to add real-time monitoring, metrics dashboards, and alerting capabilities.

### Current State Analysis

**Existing Admin Components** (`apps/frontend/src/pages/AdminPage.tsx` + nested tabs):

1. **System Tab** (`AdminTab.tsx`, 543 lines):
   - Device overview stats (total users, active users, chat sessions, workflows)
   - User management (list, view details, view user chats)
   - Database health widget (path, size, table counts)
   - System health dashboard integration
   - Audit log viewer integration
   - Founder setup wizard integration
   - **Limitations**: Static data, manual refresh, no trends, no alerts

2. **Security & Vault Tab** (`SecurityTab.tsx`):
   - Vault status monitoring
   - Access control configuration
   - **Limitations**: Unknown current capabilities (needs investigation)

3. **Teams & Permissions Tab** (`PermissionsTab.tsx`):
   - RBAC configuration
   - Team access management
   - **Limitations**: Unknown current capabilities (needs investigation)

4. **Backups & Logs Tab** (`BackupsTab.tsx` + `DangerZoneTab.tsx`):
   - Backup creation/restoration
   - System logs viewing
   - Danger zone operations
   - **Limitations**: Unknown current capabilities (needs investigation)

5. **Analytics Tab** (`AnalyticsTab.tsx`):
   - Basic usage analytics
   - **Limitations**: Founder/Admin only, static charts, no drill-down

**Backend Admin Endpoints**:

- **User Management**: `/api/v1/admin/device/overview`, `/api/v1/admin/users`, `/api/v1/admin/users/{user_id}/chats`
- **Danger Zone**: `/api/v1/admin/reset-all`, `/api/v1/admin/uninstall`, `/api/v1/admin/clear-{chats,team-messages,query-library,etc}`
- **Exports**: `/api/v1/admin/export-{all,chats,queries}`
- **Permissions**: `/api/v1/permissions/*` (18+ endpoints for RBAC management)
- **System Health**: `/api/v1/system/db-health`, `/api/v1/diagnostics`

**Gaps Identified**:

- ❌ **No Real-Time Updates**: All data requires manual refresh
- ❌ **No Trending/Forecasting**: Static snapshots, no historical analysis
- ❌ **No Alerting System**: Passive monitoring, no proactive notifications
- ❌ **No Performance Metrics**: CPU, memory, GPU, Metal 4 utilization missing
- ❌ **No Activity Heatmaps**: When/where users are active unclear
- ❌ **Limited Database Insights**: Only table counts, no query performance, WAL status, or fragmentation metrics
- ❌ **No Ollama Monitoring**: Model download progress, inference metrics, token usage invisible
- ❌ **No P2P Mesh Status**: libp2p peer count, sync status, bandwidth usage unknown
- ❌ **Fragmented UX**: Critical info scattered across 5+ tabs
- ❌ **No Export/Report Generation**: Can't generate summary reports for stakeholders
- ❌ **No Comparison Views**: Can't compare current vs. historical metrics

### Proposed Solution

**Redesign Admin Dashboard** with 3 primary views:

#### 1. **Mission Control** (New Overview Dashboard)

**Layout**: Apple-style card grid with live widgets

**Widgets** (all with real-time WebSocket updates):

- **System Vitals** (Hero Card, top-left):
  - CPU usage (per core + overall) with sparkline graph
  - RAM usage (active, wired, compressed) with visual bar
  - GPU/Metal 4 utilization + active model inference count
  - Disk usage + I/O rate (read/write MB/s)
  - Network I/O (P2P mesh bandwidth)
  - Temperature sensors (Apple Silicon thermal state)
  - **Action Buttons**: View detailed metrics, Export diagnostics JSON

- **User Activity** (Medium Card):
  - Active users (last 5m, 1h, 24h, 7d) with trend arrows
  - Concurrent sessions (current WebSocket connections)
  - User activity heatmap (24-hour view, color-coded by intensity)
  - Top active users today (ranked list with session count)
  - **Action Buttons**: View user details, Export user activity CSV

- **Database Health** (Medium Card - Enhanced):
  - All 8 databases (app, vault, teams, workflows, chat, learning, datasets, audit)
  - Per-DB metrics: Size, row count, WAL mode status, fragmentation %
  - Query performance: Avg query time (last 1000 queries), slow query count (>100ms)
  - Connection pool: Active/idle connections
  - Checkpoint history: Last WAL checkpoint timestamp + size
  - **Action Buttons**: Vacuum DB, Run integrity check, View slow queries, Export DB report

- **AI/Ollama Status** (Medium Card):
  - Ollama server status (running/offline) with uptime
  - Active models: List of loaded models in VRAM with size
  - Model downloads: Progress bars for in-flight downloads
  - Inference metrics: Total requests today, avg tokens/sec, cache hit rate
  - Token usage: Total tokens processed (7d trend graph)
  - Model storage: Total disk usage by model
  - **Action Buttons**: View model details, Restart Ollama, Clear model cache

- **P2P Mesh Network** (Medium Card):
  - Peer count: Connected peers (current + max seen today)
  - Sync status: Last sync timestamp, pending messages
  - Bandwidth: Upload/download rates (last 15min graph)
  - Mesh health: Connection quality score (latency, packet loss)
  - Discovered peers: List of available but unconnected peers
  - **Action Buttons**: Force sync, View peer details, Export mesh topology

- **Alerts & Notifications** (Sidebar Widget):
  - Critical alerts (red badge count)
  - Warnings (yellow badge count)
  - Recent events timeline (last 10 events with timestamps)
  - Alert categories: Security, Performance, Storage, Network
  - **Action Buttons**: View all alerts, Configure alert rules, Acknowledge all

- **Quick Actions Panel** (Bottom Toolbar):
  - Buttons: User Management, Analytics, Audit Logs, System Health, Settings
  - Search bar: Global search across users, logs, queries

**Technical Implementation**:
- WebSocket endpoint `/ws/admin/metrics` for real-time updates (1s interval)
- Backend service: `api/services/admin_metrics.py` to aggregate data
- Frontend store: `adminMetricsStore.ts` with Zustand + WebSocket sync
- Chart library: Recharts or Chart.js for sparklines/graphs
- Responsive grid: Tailwind + CSS Grid, collapses to single column on mobile

#### 2. **Deep Analytics** (Enhanced Analytics Tab)

**New Features**:

- **Time-Series Analysis**:
  - User growth chart (daily new users, last 90 days)
  - Session duration trends (avg session length by user role)
  - Feature adoption funnel (% users who used Chat → Kanban → Code → DB)
  - Retention cohorts (users still active after 7/30/90 days)

- **Usage Heatmaps**:
  - Hour-of-day activity matrix (24x7 grid showing busiest times)
  - Feature usage by role (RBAC role vs. feature matrix)
  - Geographic distribution (if multi-device support added later)

- **Performance Benchmarks**:
  - API response time percentiles (p50, p90, p99)
  - Database query performance (slowest queries with EXPLAIN plans)
  - Ollama inference speed (tokens/sec by model)
  - Frontend render metrics (Time to Interactive, Largest Contentful Paint)

- **Predictive Insights** (ML-powered, future enhancement):
  - Forecast user growth (next 30 days)
  - Predict storage exhaustion date
  - Anomaly detection (unusual activity patterns)

- **Export Capabilities**:
  - Generate PDF reports (summary dashboard for stakeholders)
  - Export raw data (CSV/JSON for external BI tools)
  - Schedule automated reports (daily/weekly email summaries)

**Backend APIs**:
- `/api/v1/admin/analytics/timeseries?metric=users&range=90d`
- `/api/v1/admin/analytics/heatmap?type=activity&granularity=hourly`
- `/api/v1/admin/analytics/performance?category=api&limit=50`
- `/api/v1/admin/analytics/export?format=pdf&template=executive_summary`

#### 3. **System Health Deep Dive** (Enhanced Health Tab)

**New Sections**:

- **Process Monitor**:
  - Backend API server (PID, uptime, memory, CPU %)
  - Ollama server (PID, uptime, GPU memory)
  - WebSocket server (connection count, message rate)
  - Nginx (if used, request rate, cache hit ratio)

- **Log Aggregator**:
  - Live log streaming (tail -f style) with filtering
  - Log levels: DEBUG/INFO/WARN/ERROR with color coding
  - Full-text search across logs
  - Export logs (filtered subset or full archive)

- **Diagnostic Tools**:
  - Run health checks (one-click endpoint testing)
  - Network diagnostics (ping libp2p peers, check NAT traversal)
  - Database vacuum/analyze (optimize DB performance)
  - Clear stale cache (Redis, if added)

- **Incident Timeline**:
  - Historical view of errors/alerts (last 7 days)
  - Incident details: Error message, stack trace, affected users
  - Resolution status: Open, Acknowledged, Resolved

**Backend APIs**:
- `/api/v1/admin/health/processes` (list all running processes)
- `/api/v1/admin/health/logs?level=error&tail=100` (stream logs)
- `/api/v1/admin/health/diagnostics/run` (trigger health checks)
- `/api/v1/admin/health/incidents?range=7d` (historical incidents)

#### 4. **Alerting & Notification System** (New Feature)

**Alert Rules** (configurable in Settings):

- **System Alerts**:
  - CPU usage > 80% for 5 minutes → Warning
  - Disk usage > 90% → Critical
  - Database size growth > 1GB/day → Info
  - Ollama server offline → Critical

- **User Alerts**:
  - Concurrent users > 10 → Info (scale planning)
  - Failed login attempts > 5 in 10min → Security alert
  - New user signup → Info

- **Performance Alerts**:
  - API response time > 2s (p95) → Warning
  - Database query > 5s → Warning
  - Ollama inference < 10 tokens/sec → Performance degradation

**Notification Channels** (future):
- In-app toast notifications (immediate)
- Email digests (daily summary)
- Slack/Discord webhooks (team notifications)
- SMS (critical alerts only)

**Backend**:
- Alert engine: `api/services/alert_engine.py` (rule evaluation loop, runs every 30s)
- Alert store: New `alerts` table in `audit.db`
- WebSocket broadcast: Push alerts to connected admin clients
- Alert history: Queryable via `/api/v1/admin/alerts?status=open&severity=critical`

### Implementation Plan

**Phase 10.1: Mission Control Dashboard** (2 weeks)

1. **Backend**:
   - Create `api/services/admin_metrics.py` service (aggregate system metrics)
   - Implement WebSocket endpoint `/ws/admin/metrics`
   - Add endpoints for real-time CPU/RAM/GPU monitoring (use `psutil`, `GPUtil`)
   - Enhance DB health endpoint to return WAL status, fragmentation, query perf

2. **Frontend**:
   - Create `adminMetricsStore.ts` Zustand store with WebSocket sync
   - Build Mission Control layout with responsive card grid
   - Implement 6 core widgets (System Vitals, User Activity, DB Health, Ollama, P2P, Alerts)
   - Add real-time chart updates (sparklines, bars, gauges)

3. **Testing**:
   - Load test WebSocket with 10 concurrent admin clients
   - Verify metric accuracy (compare with macOS Activity Monitor)

**Phase 10.2: Enhanced Analytics** (1.5 weeks)

1. **Backend**:
   - Build analytics aggregation queries (user growth, session duration, feature adoption)
   - Implement heatmap data endpoints (activity by hour/day)
   - Add performance benchmark queries (slow queries, API response times)
   - Create PDF export service (use `reportlab` or `weasyprint`)

2. **Frontend**:
   - Build time-series charts (Recharts, line/bar/area charts)
   - Create heatmap visualizations (day-of-week × hour-of-day grid)
   - Add export UI (PDF, CSV, JSON download buttons)

3. **Testing**:
   - Verify analytics accuracy with known test data
   - Test PDF generation with different templates

**Phase 10.3: System Health Deep Dive** (1 week)

1. **Backend**:
   - Add process monitoring endpoint (list PIDs, resource usage)
   - Implement log streaming endpoint (`tail -f` style with filters)
   - Create diagnostic tool endpoints (health checks, vacuum, clear cache)

2. **Frontend**:
   - Build process monitor table (PID, uptime, CPU, RAM)
   - Create log viewer with live streaming + search
   - Add diagnostic tool UI (one-click actions)

3. **Testing**:
   - Test log streaming with high log volume (1000+ lines/sec)
   - Verify diagnostic tools don't crash backend

**Phase 10.4: Alerting System** (1.5 weeks)

1. **Backend**:
   - Design `alerts` table schema (id, rule, severity, status, timestamp, metadata)
   - Implement alert engine service (rule evaluation loop)
   - Add alert CRUD endpoints (create rule, list alerts, acknowledge, resolve)
   - Integrate WebSocket broadcast for new alerts

2. **Frontend**:
   - Build alerts sidebar widget (badge count, timeline)
   - Create alert configuration UI (rule builder)
   - Add alert detail modal (view message, stack trace, affected users)

3. **Testing**:
   - Simulate alert conditions (e.g., spike CPU to 90%)
   - Verify alerts fire correctly and appear in UI

**Phase 10.5: Polish & Documentation** (1 week)

1. **UX Refinement**:
   - Consistent theming (colors, icons, spacing)
   - Loading states, empty states, error states
   - Accessibility (keyboard nav, ARIA labels, screen reader support)
   - Mobile responsiveness (test on iPad, collapse cards on phone)

2. **Documentation**:
   - Admin guide: How to use Mission Control, interpret metrics
   - Alert configuration guide: Setting thresholds, notification channels
   - API docs: OpenAPI specs for new admin endpoints
   - Troubleshooting guide: Common issues (slow DB, high CPU)

3. **Performance Optimization**:
   - Debounce WebSocket updates (avoid UI jank)
   - Lazy-load charts (only render visible widgets)
   - Cache metric history (reduce DB queries)

### Success Criteria

- **Real-Time Updates**: All Mission Control widgets update via WebSocket ≤1s latency
- **Comprehensive Coverage**: 100% of system metrics visible (CPU, RAM, GPU, DB, Ollama, P2P)
- **Actionable Insights**: Admins can identify and resolve performance issues in <5 minutes
- **Alert Coverage**: 90%+ of critical issues trigger alerts before user impact
- **Performance**: Dashboard loads in <2s, no UI jank during live updates
- **Accessibility**: WCAG 2.1 AA compliant, keyboard navigable
- **Documentation**: Complete admin guide + API docs + troubleshooting guide
- **User Satisfaction**: Admins report 80%+ satisfaction with new dashboard (survey)

### Testing Requirements

**Unit Tests**:
- Alert engine rule evaluation logic
- Metric aggregation calculations (accuracy tests)
- WebSocket message formatting

**Integration Tests**:
- WebSocket connection lifecycle (connect, update, disconnect, reconnect)
- End-to-end alert flow (trigger → fire → notify → acknowledge)
- PDF export generation (verify content, layout)

**E2E Tests** (Playwright):
- Load Mission Control → verify all widgets render
- Simulate high CPU → verify alert fires in UI
- Export analytics PDF → verify download succeeds
- Stream logs → verify real-time updates
- User journey: Admin investigates slow DB → runs vacuum → confirms improvement

**Load Tests**:
- 10 concurrent admin WebSocket connections (no dropped messages)
- 1000 alerts/hour processing (no queue backlog)
- Log streaming with 10,000 lines/sec (no lag)

**Performance Benchmarks**:
- Mission Control initial load: <2s (p95)
- WebSocket update latency: <500ms (p95)
- Analytics query response: <5s (p95)
- PDF export generation: <10s (p95)

### Dependencies

- **Requires**:
  - Phase 2 (Backend Services refactor) for cleaner service layer
  - Phase 4 (Frontend refactor) for AdminPage modularization
  - Existing diagnostics endpoint (`/api/v1/diagnostics`)
  - Existing DB health endpoint (`/api/v1/system/db-health`)
  - WebSocket infrastructure (already exists for chat)
  - Python packages: `psutil`, `GPUtil` (or Metal API bindings)

- **Blocks**: None (standalone enhancement)

### Estimated Effort

- **Phase 10.1 (Mission Control)**: 10 days
- **Phase 10.2 (Analytics)**: 7 days
- **Phase 10.3 (Health Deep Dive)**: 5 days
- **Phase 10.4 (Alerting)**: 7 days
- **Phase 10.5 (Polish & Docs)**: 5 days
- **Buffer for edge cases**: 5 days
- **Total**: ~39 days (6 weeks)

### Priority Justification

**Deferred to Phase 10** because:
- Requires real-time infrastructure (WebSocket broadcasting)
- Needs careful UX design to avoid overwhelming users with metrics
- High complexity due to multi-source data aggregation (system, DB, Ollama, P2P)
- Risk of performance issues if not optimized (polling overhead, chart rendering)
- Should be done after core admin RBAC (Phase 9) to ensure proper access control
- Not blocking other features (current admin dashboard is functional, just limited)
- Current workaround: Admins can manually check logs, run CLI commands, use macOS Activity Monitor

**High value once implemented**:
- Dramatically improves admin productivity (proactive vs reactive monitoring)
- Reduces mean time to resolution (MTTR) for incidents
- Enables data-driven scaling decisions (forecast user growth, storage needs)
- Professionalizes ElohimOS for production deployment

### Future Enhancements (Post-Phase 10)

- **Custom Dashboards**: Let admins create personalized views (drag-drop widgets)
- **Historical Playback**: Scrub timeline to see metrics at any point in past
- **Comparative Analysis**: Compare today vs. last week/month
- **ML Anomaly Detection**: Auto-detect unusual patterns (sudden traffic spike, model drift)
- **Multi-Device Fleet Management**: If ElohimOS expands to multi-device, show fleet dashboard
- **Automated Remediation**: Auto-run fixes for common issues (e.g., auto-vacuum DB when fragmented >20%)
- **Billing Integration**: If monetized, show revenue metrics, user tier distribution

---

## 📋 Document History

**Document Version**: 2.3 (Phase 2 Partial - Team/Vault/Chat)
**Last Updated**: 2025-11-17
**Status**: 🔄 Phase 2 IN PROGRESS - Team (✅ Complete), Vault (✅ Partial), Chat (✅ Foundation)

### Version 2.3 Changes (2025-11-17):
**Phase 2.3a (Chat Sessions + Storage) Completion Update**

1. **Marked Phase 2.3a as COMPLETED** (Chat Sessions + Storage):
   - Commits: `50295d7f` + `8863b418` - refactor(chat): Phase 2.3a foundation + session delegation
   - Created `types.py` (123 lines) - Enums, type aliases, constants for chat service
   - Created `storage.py` (410 lines) - 16 DB functions wrapping NeutronChatMemory (sessions, messages, documents, search)
   - Created `sessions.py` (360 lines) - 11 orchestration functions (session lifecycle, context assembly, message handling)
   - Updated `core.py` (-53 lines refactored) - 6 methods now delegate to sessions.py
   - Chat service now follows types + storage + orchestration pattern (same as Team/Vault)

2. **Updated Large Files Analysis**:
   - `api/services/chat/core.py`: 1,751 → 1,698 lines (-3% reduction, sessions/messages extracted)
   - Marked as "PARTIAL REFACTOR" with module breakdown

3. **Chat Service Architecture Documented**:
   - Session/message persistence now in sessions.py + storage.py
   - Streaming, routing, model selection, analytics remain in core.py (Phase 2.3b+)
   - Thread-local SQLite connections via NeutronChatMemory (WAL mode)
   - 6 methods delegated: create/get/list/delete session, append_message, auto-title

4. **Updated Repo State**:
   - Phase 2 progress now shows: Team (6 modules), Vault (5 modules), Chat (3 modules)

### Version 2.2 Changes (2025-11-17):
**Phase 2.1b & 2.2b Completion Update**

1. **Marked Phase 2.1b as COMPLETED** (Team Roles/Promotions + Founder Rights):
   - Commit: `19fdac03` - refactor(team): Phase 2.1b - Extract Roles/Promotions + Founder Rights
   - Created `roles.py` (490 lines) - 11 role/promotion orchestration functions (auto-promotion, delayed promotions, temp promotions)
   - Created `founder_rights.py` (204 lines) - 5 Founder Rights (God Rights) management functions
   - Extended `storage.py` (+531 lines) - Added 17 DB functions for 3 tables (delayed_promotions, temp_promotions, god_rights_auth)
   - Updated `core.py` (-1,236 lines refactored) - 19 methods now delegate to roles.py and founder_rights.py
   - Team service now fully modular: core.py (1,784 lines) + 6 modules

2. **Marked Phase 2.2b as COMPLETED** (Vault File Operations + Encryption Helpers):
   - Commit: `0f91293c` - refactor(vault): Phase 2.2b - Extract file operations + encryption helpers
   - Extended `encryption.py` (+15 lines) - Moved `get_encryption_key()` and `generate_file_key()` from core.py
   - Extended `storage.py` (+259 lines) - Added file CRUD operations (create, list, delete, rename, move)
   - Updated `core.py` (-147 lines refactored) - 5 file methods now delegate to storage.py + encryption.py
   - Vault service partially modular: core.py (2,370 lines) + 5 modules, remaining work in Phase 2.2c

3. **Updated Large Files Analysis**:
   - `api/services/team/core.py`: 2,872 → 1,784 lines (-38% reduction, fully modular)
   - `api/services/vault/core.py`: 2,780 → 2,370 lines (-15% reduction, partially modular)
   - Marked both as "REFACTORED" with module breakdowns

4. **Added Modularization Pattern Documentation**:
   - Documented "manager parameter" pattern for cross-module calls
   - Documented `_get_app_conn()` / `_get_vault_conn()` per-function connection pattern
   - Documented zero `self.conn` usage in refactored paths
   - Documented backward-compatible public API preservation

5. **Updated Repo State Metrics**:
   - Backend now shows modularization progress (Team: 6 modules, Vault: 5 modules, Chat: 2 modules)
   - Status updated to reflect Phase 2 in progress

### Version 2.1 Changes (2025-11-17):
**Phase 1 Completion Update**

1. **Marked Phase 1 as COMPLETED** (Tasks 1.1, 1.2, 1.3):
   - Task 1.1: Backend SQL templates → `templates/` package (13 files, 256 templates)
   - Task 1.2: Backend NLP templates → `nlp/` package (13 files, 49 templates, intent-category architecture)
   - Task 1.3: Frontend Automation workflows → `Automation/templates/` (5 files)
   - Total: 3,511 lines of monolithic code → 31 modular files
   - Zero behavior changes, all builds passing

2. **Updated Task Descriptions with Actual Implementations**:
   - Task 1.1: Documented actual `templates/` structure (product_enrichment, pricing_analysis, etc.)
   - Task 1.2: Documented intent-category architecture (code_generation, debugging, research, etc.) vs. original generic NLP proposal
   - Task 1.3: Documented actual split by content type (types, styles, definitions, metadata)
   - Added "Implementation Details" and "Design Decision" sections explaining architectural choices

3. **Updated Large-File Analysis Tables**:
   - Marked `api/template_library_full.py` as ✅ REFACTORED → `templates/` (Phase 1.1)
   - Marked `api/core_nlp_templates.py` as ✅ REFACTORED → `nlp/` (Phase 1.2)
   - Marked `components/Automation/shared/templates.ts` as ✅ REFACTORED → `Automation/templates/` (Phase 1.3)
   - Used strikethrough formatting to indicate completed refactors

4. **Added Phase 1 Summary Section**:
   - Documented "types + data + registry" pattern established across backend and frontend
   - Quantified impact: 3,511 lines → 31 modular files
   - Confirmed zero behavior changes and passing builds

5. **Rationale for Intent-Category NLP Architecture**:
   - Original roadmap proposed generic NLP modules (entity_extraction, sentiment_analysis, etc.)
   - Actual implementation uses intent-category architecture matching codebase's `IntentCategory` enum
   - Added explanation that intent-based split aligns with Jarvis's developer-command use cases

### Version 2.0 Changes (2025-11-17):
**Major Overhaul - Aligned with Current Repo State**

1. **Added Phase 0**: Docs & Roadmap Alignment (NEW)
   - Task 0.1: Commit 39 deleted docs
   - Task 0.2: Update docs/README.md to reflect 6-doc structure
   - Task 0.3: Verify core architecture docs

2. **Updated All File Size Metrics**:
   - Backend: Verified 22,669 lines across 15 critical files (accurate as of 2025-11-17)
   - **Corrected**: 2 files >2,500 lines (team/core.py: 2,872, vault/core.py: 2,780), not 3
   - Frontend: Verified 10,070 lines across 9 critical files (App.tsx corrected to 547 lines)
   - Confirmed: 220 TS/TSX components, 14 Zustand stores

3. **Normalized Phase Structure**: Phases 0-9 (was inconsistent)
   - Phase 0: Docs alignment (NEW)
   - Phases 1-7: Refactoring (existing, improved)
   - Phases 8-9: Deferred features (Stealth Labels, Admin RBAC)
   - Phase 10: Marked as "Optional - Post-Phase 9 Enhancement" to clarify relationship

4. **Added Immediate Execution Plan**: 3-week day-by-day sprint breakdown
   - Week 1: Phase 0 + Phase 1 (template splits)
   - Week 2: Phase 2 Team service refactor
   - Week 3: Phase 2 Vault service refactor
   - Concrete tasks with acceptance criteria, file paths, test commands

5. **Enhanced Phase 1**: Converted prose into discrete tasks with acceptance criteria
   - Task 1.1: Template library split (1 day)
   - Task 1.2: NLP templates split (0.5 day)
   - Task 1.3: Automation templates split (0.5 day)
   - Each task has "Files Touched", "Estimated Time", "Done When" checklist

6. **Added Non-Negotiable Constraints** to each phase:
   - No breaking API changes
   - No RBAC regressions
   - No vault data corruption
   - All tests must pass

7. **Updated Executive Summary**:
   - Declared this document as "single source of truth"
   - Added current repo state (2025-11-17)
   - Linked to core architecture docs

8. **Improved Navigability**:
   - Clear phase headers (PHASE 0-9)
   - Task breakdowns with checkboxes
   - "Phase Complete When" checklists
   - References to specific file paths

### Version 1.3 Changes (2025-11-16):
- Added Phase 8 - Stealth Labels app-wide implementation plan
- Added Phase 9 - Admin Tab RBAC & Multi-Profile System
- Added Phase 10 - Admin Dashboard Modernization

### Version 1.0 (Initial - 2025-11-16):
- Initial comprehensive refactoring plan
- Phases 1-7 defined
- Large file analysis tables
- Implementation guidelines
