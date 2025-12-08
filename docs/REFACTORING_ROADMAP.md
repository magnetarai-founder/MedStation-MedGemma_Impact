# MagnetarStudio - Systematic Fix Plan
## Updated: 2025-12-08

---

## ✅ COMPLETED PHASES

### PHASE 1: TRIVIAL FIXES ✅ (Completed)
1. Delete model button - MagnetarHub
2. Update model button - MagnetarHub
3. Format timestamps - Automation

### PHASE 2: EASY FIXES ✅ (Completed)
1. Hot slot model picker - Settings
2. System resource display - Vault Admin
3. Extract tags - Work items

### PHASE 3: MODERATE FIXES ✅ (Completed)
1. Workflow execution tracking
2. Git status in code context
3. User preferences persistence

### PHASE 4: SEMANTIC SEARCH ✅ (Completed)
1. Vault semantic search endpoint
2. Database query semantic search
3. Workflow semantic search
4. Swift ContextBundle integration

**Commit:** `c528c164` - feat: Implement Phase 4 semantic search

---

## 🚀 PHASE 6: MAJOR REFACTORINGS (IN PROGRESS)

**Execution Order:** Phase 6 → Phase 5
**Rationale:** Cleaner codebase before adding cloud features
**Commit Strategy:** Commit and push after EVERY successful sub-phase

---

## 📋 PHASE 6.1: REFACTOR TeamWorkspace.swift (3,196 lines)

**Current Status:** Monolithic file with 26 types, 8 logical groups
**Target:** 8 focused files averaging ~400 lines each
**Estimated Time:** 3-4 hours
**Risk Level:** HIGH - Many interconnected components

### **Pre-Refactoring Checklist**
- [ ] Ensure all changes are committed and pushed
- [ ] Run full Swift build to establish baseline
- [ ] Create feature branch: `refactor/team-workspace-split`
- [ ] Document current import dependencies

### **6.1.1: Extract TeamChatComponents.swift**
**Lines to Extract:** 328-1002 (~675 lines)
**Components:**
- TeamChatView (main chat interface)
- TeamChatSidebar (channel list)
- TeamChatWindow (message display)
- TeamMessageRow (individual message)
- P2PStatus enum
- TeamChannel extension (mock data)

**Step-by-step Process:**
1. **Create new file** `apps/native/macOS/Workspaces/TeamChat/TeamChatComponents.swift`
2. **Copy imports** from TeamWorkspace.swift (lines 1-15)
3. **Copy** lines 328-1002 to new file
4. **Add** `import SwiftUI` and `import Foundation` to new file
5. **Build** - expect errors for missing types
6. **Add** missing imports (TeamService, models, colors)
7. **Build again** - should succeed
8. **In TeamWorkspace.swift**, delete lines 328-1002
9. **Add** `import TeamChatComponents` (or inline if same module)
10. **Build** - should succeed
11. **Test** - Verify chat view still works
12. **Commit**: `refactor(team): Extract TeamChatComponents from TeamWorkspace`
13. **Push** to remote

**Validation:**
- [ ] Build succeeds (no errors)
- [ ] Chat view loads correctly
- [ ] Channels display properly
- [ ] Messages render correctly
- [ ] P2P banner shows when needed

---

### **6.1.2: Extract TeamChatModals.swift**
**Lines to Extract:** 1006-1160 (~155 lines)
**Components:**
- NewChannelDialog
- PeerDiscoveryPanel
- FileSharingPanel

**Step-by-step Process:**
1. **Create** `apps/native/macOS/Workspaces/TeamChat/TeamChatModals.swift`
2. **Copy** lines 1006-1160
3. **Add** necessary imports
4. **Build** and fix import errors
5. **Delete** lines from TeamWorkspace.swift
6. **Build** and verify
7. **Test** modal interactions
8. **Commit**: `refactor(team): Extract TeamChatModals from TeamWorkspace`
9. **Push** to remote

**Validation:**
- [ ] Build succeeds
- [ ] New channel dialog opens
- [ ] Dialog creates channel
- [ ] P2P panels render (even if placeholder)

---

### **6.1.3: Extract DocsWorkspaceView.swift**
**Lines to Extract:** 1162-1646 (~484 lines, minus duplicates)
**Components:**
- DocsWorkspace (main view)
- DocumentRowView
- DocumentType enum

**Remove/Don't Copy:**
- DocumentsSidebar (lines 1451-1520) - DUPLICATE, unused
- Document struct (lines 1549-1561) - LEGACY mock

**Step-by-step Process:**
1. **Create** `apps/native/macOS/Workspaces/TeamDocs/DocsWorkspaceView.swift`
2. **Copy** lines 1162-1449 (DocsWorkspace)
3. **Copy** lines 1522-1547 (DocumentType enum)
4. **Copy** lines 1565-1646 (DocumentRowView)
5. **Skip** lines 1451-1520 (duplicate sidebar)
6. **Skip** lines 1549-1561 (legacy mock)
7. **Add** imports
8. **Build** and fix errors
9. **Delete** extracted lines from TeamWorkspace.swift
10. **Build** and verify
11. **Test** docs workspace
12. **Commit**: `refactor(team): Extract DocsWorkspaceView from TeamWorkspace`
13. **Push** to remote

**Validation:**
- [ ] Build succeeds
- [ ] Docs tab loads
- [ ] Document list displays
- [ ] Can create document
- [ ] Can edit/delete document

---

### **6.1.4: Extract VaultWorkspaceView.swift**
**Lines to Extract:** 1650-2423 (~773 lines)
**Components:**
- VaultWorkspace (main vault UI)
- VaultViewMode enum

**Remove/Don't Copy:**
- LegacyVaultFile (lines 2425-2464) - LEGACY mock

**Step-by-step Process:**
1. **Create** `apps/native/macOS/Workspaces/TeamVault/VaultWorkspaceView.swift`
2. **Copy** lines 1650-2416 (VaultWorkspace)
3. **Copy** lines 2420-2423 (VaultViewMode enum)
4. **Skip** lines 2425-2464 (legacy mock)
5. **Add** imports
6. **Build** and fix errors
7. **Delete** extracted lines from TeamWorkspace.swift
8. **Build** and verify
9. **Test** vault operations
10. **Commit**: `refactor(team): Extract VaultWorkspaceView from TeamWorkspace`
11. **Push** to remote

**Validation:**
- [ ] Build succeeds
- [ ] Vault tab loads
- [ ] Lock/unlock works
- [ ] File browsing works
- [ ] Upload/download works
- [ ] Create folder works

---

### **6.1.5: Extract VaultComponents.swift**
**Lines to Extract:** 2468-2745 (~278 lines)
**Components:**
- NewFolderDialog
- FilePreviewModal

**Step-by-step Process:**
1. **Create** `apps/native/macOS/Workspaces/TeamVault/VaultComponents.swift`
2. **Copy** lines 2468-2531 (NewFolderDialog)
3. **Copy** lines 2535-2745 (FilePreviewModal)
4. **Add** imports
5. **Build** and fix errors
6. **Delete** extracted lines from TeamWorkspace.swift
7. **Build** and verify
8. **Test** folder creation and file preview
9. **Commit**: `refactor(team): Extract VaultComponents from TeamWorkspace`
10. **Push** to remote

**Validation:**
- [ ] Build succeeds
- [ ] New folder dialog works
- [ ] File preview modal opens
- [ ] File download works from preview
- [ ] File delete works from preview

---

### **6.1.6: Extract TeamModals.swift**
**Lines to Extract:** 2749-3189 (~441 lines)
**Components:**
- DiagnosticsPanel
- CreateTeamModal
- JoinTeamModal
- VaultSetupModal

**Step-by-step Process:**
1. **Create** `apps/native/macOS/Workspaces/TeamModals.swift`
2. **Copy** lines 2749-2919 (DiagnosticsPanel)
3. **Copy** lines 2921-3006 (CreateTeamModal)
4. **Copy** lines 3008-3083 (JoinTeamModal)
5. **Copy** lines 3085-3189 (VaultSetupModal)
6. **Add** imports
7. **Build** and fix errors
8. **Delete** extracted lines from TeamWorkspace.swift
9. **Build** and verify
10. **Test** all modals
11. **Commit**: `refactor(team): Extract TeamModals from TeamWorkspace`
12. **Push** to remote

**Validation:**
- [ ] Build succeeds
- [ ] Diagnostics panel opens and displays data
- [ ] Create team modal works
- [ ] Join team modal works
- [ ] Vault setup modal works

---

### **6.1.7: Final TeamWorkspace.swift Cleanup**
**What Remains:** ~300 lines
**Components:**
- Main TeamWorkspace container (lines 17-282)
- TeamTabButton component (lines 284-316)
- TeamView enum (lines 318-325)
- Preview provider (lines 3191-3196)

**Step-by-step Process:**
1. **Review** remaining TeamWorkspace.swift
2. **Verify** all imports are correct
3. **Remove** unused imports
4. **Add** comments documenting the file structure
5. **Build** full project
6. **Run** all team-related features end-to-end
7. **Commit**: `refactor(team): Finalize TeamWorkspace split - 3196 lines → 8 files`
8. **Push** to remote

**Final Validation:**
- [ ] TeamWorkspace.swift is ~300 lines
- [ ] All 8 files build successfully
- [ ] Chat functionality works end-to-end
- [ ] Docs functionality works end-to-end
- [ ] Vault functionality works end-to-end
- [ ] All modals work correctly
- [ ] No compiler warnings
- [ ] No unused imports

---

## 📋 PHASE 6.2: REFACTOR AutomationWorkspace.swift (2,040 lines)

**Current Status:** Monolithic file with 23 types, 7 logical groups
**Target:** 10+ focused files averaging ~200 lines each
**Estimated Time:** 2-3 hours
**Risk Level:** MEDIUM - Well-structured but extensive

### **Pre-Refactoring Checklist**
- [ ] TeamWorkspace refactoring complete and committed
- [ ] Run full Swift build
- [ ] Create feature branch: `refactor/automation-workspace-split`

### **Directory Structure to Create:**
```
apps/native/Shared/Components/AutomationWorkspace/
├── Core/
│   ├── AutomationWorkspaceView.swift
│   └── WorkflowTabButton.swift
├── Dashboard/
│   ├── WorkflowDashboardView.swift
│   ├── WorkflowDashboardModels.swift
│   └── Components/
│       ├── WorkflowGrid.swift
│       ├── WorkflowCardView.swift
│       └── AgentAssistCard.swift
├── Builder/
│   ├── WorkflowBuilderView.swift
│   └── Components/
│       └── DotPattern.swift
├── Designer/
│   └── WorkflowDesignerView.swift
├── Analytics/
│   ├── WorkflowAnalyticsView.swift
│   ├── WorkflowAnalyticsModels.swift
│   └── Components/
│       ├── MetricCard.swift
│       └── StagePerformanceTable.swift
└── Queue/
    ├── WorkflowQueueView.swift
    ├── WorkflowQueueModels.swift
    └── Components/
        ├── QueueItemCard.swift
        ├── ToggleButton.swift
        └── StatusPill.swift
```

### **6.2.1: Extract Dashboard Components**
**Order:** Models → Components → Main View

**Step 6.2.1a: Create WorkflowDashboardModels.swift**
**Lines:** 552-662 (DashboardScope, WorkflowVisibility, WorkflowCard)
1. Create file with models
2. Build and verify
3. Commit: `refactor(automation): Extract WorkflowDashboardModels`
4. Push

**Step 6.2.1b: Create Dashboard Components**
**Files:**
- WorkflowGrid.swift (lines 340-358)
- WorkflowCardView.swift (lines 360-456)
- AgentAssistCard.swift (lines 458-550)

For each file:
1. Create file
2. Copy relevant lines
3. Build and fix imports
4. Commit individually
5. Push

**Step 6.2.1c: Create WorkflowDashboardView.swift**
**Lines:** 148-338
1. Create main view
2. Import models and components
3. Build and verify
4. Delete from main file
5. Test dashboard functionality
6. Commit: `refactor(automation): Extract WorkflowDashboardView`
7. Push

**Validation:**
- [ ] Dashboard loads
- [ ] Workflows display in grid
- [ ] Filters work
- [ ] Cards are clickable
- [ ] Agent assist card shows

---

### **6.2.2: Extract Builder Components**

**Step 6.2.2a: Create DotPattern.swift**
**Lines:** 1015-1038
1. Create component file
2. Build and verify
3. Commit: `refactor(automation): Extract DotPattern component`
4. Push

**Step 6.2.2b: Create WorkflowBuilderView.swift**
**Lines:** 664-1013
1. Create main builder view
2. Import DotPattern
3. Build and verify
4. Delete from main file
5. Test builder canvas
6. Commit: `refactor(automation): Extract WorkflowBuilderView`
7. Push

**Validation:**
- [ ] Builder view loads
- [ ] Canvas displays with dot pattern
- [ ] Controls work (zoom, help)
- [ ] Title editable

---

### **6.2.3: Extract Analytics Components**

**Step 6.2.3a: Create WorkflowAnalyticsModels.swift**
**Lines:** 1297-1340
1. Create models file
2. Build and verify
3. Commit: `refactor(automation): Extract WorkflowAnalyticsModels`
4. Push

**Step 6.2.3b: Create Analytics Components**
**Files:**
- MetricCard.swift (lines 1157-1204)
- StagePerformanceTable.swift (lines 1206-1295)

For each:
1. Create file
2. Build and verify
3. Commit individually
4. Push

**Step 6.2.3c: Create WorkflowAnalyticsView.swift**
**Lines:** 1060-1155
1. Create main view
2. Import models and components
3. Build and verify
4. Delete from main file
5. Test analytics display
6. Commit: `refactor(automation): Extract WorkflowAnalyticsView`
7. Push

**Validation:**
- [ ] Analytics view loads
- [ ] Metrics display correctly
- [ ] Performance table renders
- [ ] Data loads from backend

---

### **6.2.4: Extract Queue Components**

**Step 6.2.4a: Create WorkflowQueueModels.swift**
**Lines:** 1897-2033
1. Create models file (enums + QueueItem struct)
2. Build and verify
3. Commit: `refactor(automation): Extract WorkflowQueueModels`
4. Push

**Step 6.2.4b: Create Queue Components**
**Files:**
- QueueItemCard.swift (lines 1704-1844)
- ToggleButton.swift (lines 1846-1867)
- StatusPill.swift (lines 1869-1895)

For each:
1. Create file
2. Build and verify
3. Commit individually
4. Push

**Step 6.2.4c: Create WorkflowQueueView.swift**
**Lines:** 1379-1702 (largest single view)
1. Create main view
2. Import models and components
3. Build and verify
4. Delete from main file
5. Test queue functionality
6. Commit: `refactor(automation): Extract WorkflowQueueView`
7. Push

**Validation:**
- [ ] Queue view loads
- [ ] Items display correctly
- [ ] Filtering works (priority, mode)
- [ ] Can claim work items
- [ ] Error states work
- [ ] Loading states work

---

### **6.2.5: Extract Core Workspace**

**Step 6.2.5a: Create WorkflowTabButton.swift**
**Lines:** 112-143
1. Create component
2. Build and verify
3. Commit: `refactor(automation): Extract WorkflowTabButton`
4. Push

**Step 6.2.5b: Create WorkflowDesignerView.swift**
**Lines:** 1040-1058 (placeholder)
1. Create view file
2. Build and verify
3. Commit: `refactor(automation): Extract WorkflowDesignerView`
4. Push

**Step 6.2.5c: Final AutomationWorkspaceView.swift**
**What Remains:** Lines 12-110, enum at 1342-1370
1. Keep main container and enum
2. Update all imports
3. Remove unused code
4. Build full project
5. Test all tabs
6. Commit: `refactor(automation): Finalize AutomationWorkspace split - 2040 lines → 15 files`
7. Push

**Final Validation:**
- [ ] All 5 tabs work (Dashboard, Builder, Designer, Analytics, Queue)
- [ ] Navigation between tabs smooth
- [ ] All backend calls work
- [ ] No console errors
- [ ] Build has no warnings

---

## 📋 PHASE 6.3: REFACTOR team/core.py (1,785 lines)

**Current Status:** Partially modular (46% delegated), 54% inline
**Target:** 3 new modules + updated core orchestrator
**Estimated Time:** 2.5-3 hours
**Risk Level:** MEDIUM - Backend refactoring with database ops

### **Pre-Refactoring Checklist**
- [ ] All Swift refactoring complete and committed
- [ ] Run backend import validation
- [ ] Create feature branch: `refactor/team-service-split`
- [ ] Review database migration needs

### **Current Module Status:**
✅ **Already Modular:**
- storage.py - Database operations
- members.py - Member management
- invitations.py - Invite codes
- roles.py - Role validation
- founder_rights.py - God rights
- types.py - Shared types

🔴 **Needs Extraction:**
- workflows.py - Workflow permissions (lines 573-821)
- queues.py - Queue ACL (lines 822-1152)
- vault.py - Team vault ops (lines 1211-1780)

### **6.3.1: Extract workflows.py Module**
**Lines to Extract:** 573-821 (248 lines)
**Methods:**
- add_workflow_permission()
- remove_workflow_permission()
- check_workflow_permission()
- _check_default_permission()
- get_workflow_permissions()

**Step-by-step Process:**
1. **Create** `apps/backend/api/services/team/workflows.py`
2. **Copy** method signatures and implementations
3. **Add** necessary imports (sqlite3, logging, typing)
4. **Replace** `self.conn` with `storage.get_connection()` pattern
5. **Convert** to module-level functions (remove self parameter)
6. **Add** docstrings
7. **Run** import validator
8. **Update** core.py to delegate to this module
9. **Run** backend tests (if any exist)
10. **Commit**: `refactor(backend): Extract workflow permissions to workflows.py`
11. **Push** to remote

**Validation:**
- [ ] Import validation passes
- [ ] Backend starts without errors
- [ ] Workflow permission checks work
- [ ] No database connection leaks

---

### **6.3.2: Extract queues.py Module**
**Lines to Extract:** 822-1152 (330 lines)
**Methods:**
- create_queue()
- add_queue_permission()
- remove_queue_permission()
- check_queue_access()
- _check_default_queue_access()
- get_accessible_queues()
- get_queue_permissions()
- get_queue()

**Step-by-step Process:**
1. **Create** `apps/backend/api/services/team/queues.py`
2. **Copy** all queue-related methods
3. **Add** imports
4. **Replace** `self.conn` with storage pattern
5. **Convert** to module functions
6. **Add** docstrings with examples
7. **Run** import validator
8. **Update** core.py to delegate
9. **Test** queue operations
10. **Commit**: `refactor(backend): Extract queue management to queues.py`
11. **Push** to remote

**Validation:**
- [ ] Import validation passes
- [ ] Can create queues
- [ ] Permission checks work
- [ ] Can list accessible queues
- [ ] No regressions in existing code

---

### **6.3.3: Extract vault.py Module**
**Lines to Extract:** 1211-1780 (569 lines)
**Methods:**
- _get_vault_encryption_key()
- _encrypt_content()
- _decrypt_content()
- create_vault_item()
- update_vault_item()
- delete_vault_item()
- get_vault_item()
- list_vault_items()
- check_vault_permission()
- add_vault_permission()
- remove_vault_permission()
- get_vault_permissions()

**IMPORTANT:** This is team vault, different from main VaultService

**Step-by-step Process:**
1. **Create** `apps/backend/api/services/team/vault.py`
2. **Copy** all vault methods
3. **Add** cryptography imports
4. **Replace** `self.conn` with storage
5. **Convert** to module functions
6. **Add** extensive docstrings (security-critical code)
7. **Document** encryption key derivation (needs KMS in production)
8. **Run** import validator
9. **Update** core.py to delegate
10. **Test** vault operations thoroughly
11. **Commit**: `refactor(backend): Extract team vault to vault.py`
12. **Push** to remote

**Validation:**
- [ ] Import validation passes
- [ ] Encryption/decryption works
- [ ] Can create vault items
- [ ] Can retrieve and decrypt items
- [ ] Permission checks work
- [ ] Soft delete works

---

### **6.3.4: Update TeamManager to Thin Orchestrator**
**What Remains in core.py:**
- generate_team_id() - Business logic
- create_team() - Multi-step orchestration
- check_super_admin_offline() - Needs storage migration first
- All delegation methods (thin wrappers)

**Step-by-step Process:**
1. **Update** all methods to delegate to new modules
2. **Add** imports for workflows, queues, vault modules
3. **Remove** now-unused database direct access code
4. **Add** module-level docstring explaining architecture
5. **Run** full import validation
6. **Test** all team operations end-to-end
7. **Commit**: `refactor(backend): Convert TeamManager to thin orchestrator`
8. **Push** to remote

**Final Validation:**
- [ ] core.py reduced to ~600 lines (from 1785)
- [ ] All imports valid
- [ ] Backend starts successfully
- [ ] All team operations work
- [ ] No performance regressions
- [ ] Logging still works correctly

---

## 📋 PHASE 6.4: REFACTOR vault/core.py (1,538 lines)

**Current Status:** 46% delegated, 52% inline implementations
**Target:** 8 new focused modules + thin orchestrator
**Estimated Time:** 2-3 hours
**Risk Level:** MEDIUM-HIGH - Security-critical encryption code

### **Pre-Refactoring Checklist**
- [ ] team/core.py refactoring complete
- [ ] Run backend tests
- [ ] Create feature branch: `refactor/vault-service-split`
- [ ] Review existing vault modules (6 exist already)

### **Existing Modules (Keep As-Is):**
- documents.py - Document operations ✅
- files.py - File operations ✅
- folders.py - Folder operations ✅
- search.py - Search functionality ✅
- automation.py - Automation features ✅
- encryption.py - Encryption utils ✅

### **6.4.1: Extract tags.py Module**
**Lines to Extract:** 661-723 (63 lines)
**Methods:**
- add_tag_to_file()
- remove_tag_from_file()
- get_file_tags()

**Step-by-step Process:**
1. **Create** `apps/backend/api/services/vault/tags.py`
2. **Copy** methods
3. **Add** imports (sqlite3, logging, typing)
4. **Convert** to module functions
5. **Add** docstrings
6. **Run** import validator
7. **Update** core.py to delegate
8. **Test** tagging operations
9. **Commit**: `refactor(vault): Extract tags management to tags.py`
10. **Push** to remote

**Validation:**
- [ ] Can add tags to files
- [ ] Can remove tags
- [ ] Can list file tags
- [ ] Tag colors work

---

### **6.4.2: Extract favorites.py Module**
**Lines to Extract:** 727-788 (62 lines)
**Methods:**
- add_favorite()
- remove_favorite()
- get_favorites()

**Step-by-step Process:**
1. **Create** `apps/backend/api/services/vault/favorites.py`
2. **Copy** methods
3. **Convert** to module functions
4. **Add** docstrings
5. **Run** import validator
6. **Update** core.py
7. **Test** favorites
8. **Commit**: `refactor(vault): Extract favorites to favorites.py`
9. **Push** to remote

**Validation:**
- [ ] Can add favorites
- [ ] Can remove favorites
- [ ] Can list favorites

---

### **6.4.3: Extract analytics.py Module**
**Lines to Extract:** 792-906 (115 lines)
**Methods:**
- log_file_access()
- get_recent_files()
- get_storage_stats()

**Step-by-step Process:**
1. **Create** `apps/backend/api/services/vault/analytics.py`
2. **Copy** methods including complex JOIN queries
3. **Convert** to module functions
4. **Add** docstrings explaining query logic
5. **Run** import validator
6. **Update** core.py
7. **Test** analytics queries
8. **Commit**: `refactor(vault): Extract analytics to analytics.py`
9. **Push** to remote

**Validation:**
- [ ] Access logging works
- [ ] Recent files query works
- [ ] Storage stats accurate
- [ ] Performance acceptable

---

### **6.4.4: Move Sharing Methods to Existing sharing.py**
**Lines to Extract:** 977-1172 (196 lines)
**Methods to Move:**
- create_share_link()
- get_share_link()
- verify_share_password()
- increment_share_download()
- revoke_share_link()
- get_file_shares()

**NOTE:** There's already a `sharing.py` module!

**Step-by-step Process:**
1. **Review** existing `apps/backend/api/services/vault/sharing.py`
2. **Check** if these methods already exist
3. **If missing**, add them to existing module
4. **If duplicates**, reconcile implementations
5. **Ensure** consistent API
6. **Run** import validator
7. **Update** core.py to use consolidated sharing module
8. **Test** all sharing features
9. **Commit**: `refactor(vault): Consolidate sharing methods in sharing.py`
10. **Push** to remote

**Validation:**
- [ ] Can create share links
- [ ] Password protection works
- [ ] Download counting works
- [ ] Can revoke shares
- [ ] Expiration works

---

### **6.4.5: Extract audit.py Module**
**Lines to Extract:** 1176-1267 (92 lines)
**Methods:**
- log_audit()
- get_audit_logs()

**Step-by-step Process:**
1. **Create** `apps/backend/api/services/vault/audit.py`
2. **Copy** audit methods
3. **Convert** to module functions
4. **Add** comprehensive docstrings (compliance feature)
5. **Run** import validator
6. **Update** core.py
7. **Test** audit logging
8. **Commit**: `refactor(vault): Extract audit logging to audit.py`
9. **Push** to remote

**Validation:**
- [ ] Audit events logged
- [ ] Can query audit logs
- [ ] Filtering works
- [ ] Performance acceptable

---

### **6.4.6: Extract comments.py Module**
**Lines to Extract:** 1271-1383 (113 lines)
**Methods:**
- add_file_comment()
- get_file_comments()
- update_file_comment()
- delete_file_comment()

**Step-by-step Process:**
1. **Create** `apps/backend/api/services/vault/comments.py`
2. **Copy** comment methods
3. **Convert** to module functions
4. **Add** docstrings
5. **Run** import validator
6. **Update** core.py
7. **Test** commenting features
8. **Commit**: `refactor(vault): Extract comments to comments.py`
9. **Push** to remote

**Validation:**
- [ ] Can add comments
- [ ] Comments display correctly
- [ ] Can edit comments
- [ ] Can delete comments
- [ ] Ownership validation works

---

### **6.4.7: Extract metadata.py Module**
**Lines to Extract:** 1387-1447 (61 lines)
**Methods:**
- set_file_metadata()
- get_file_metadata()

**Step-by-step Process:**
1. **Create** `apps/backend/api/services/vault/metadata.py`
2. **Copy** metadata methods
3. **Convert** to module functions
4. **Add** docstrings
5. **Run** import validator
6. **Update** core.py
7. **Test** metadata operations
8. **Commit**: `refactor(vault): Extract metadata to metadata.py`
9. **Push** to remote

**Validation:**
- [ ] Can set metadata
- [ ] Can get metadata
- [ ] Upsert logic works
- [ ] Different value types supported

---

### **6.4.8: Extract media.py Module (or extend files.py)**
**Lines to Extract:** 1481-1522 (42 lines)
**Methods:**
- generate_thumbnail()

**Step-by-step Process:**
1. **Decide**: New module or add to files.py?
2. **If new**, create `apps/backend/api/services/vault/media.py`
3. **Copy** thumbnail generation
4. **Add** PIL/Pillow imports
5. **Convert** to module function
6. **Add** docstrings with image format notes
7. **Run** import validator
8. **Update** core.py
9. **Test** thumbnail generation
10. **Commit**: `refactor(vault): Extract media processing to media.py`
11. **Push** to remote

**Validation:**
- [ ] Thumbnails generated for images
- [ ] Max size respected
- [ ] EXIF orientation handled
- [ ] Non-images handled gracefully

---

### **6.4.9: Extract database.py (Schema Definition)**
**Lines to Extract:** 67-556 (489 lines)
**Content:** `_init_db()` method with all table definitions

**Step-by-step Process:**
1. **Create** `apps/backend/api/services/vault/database.py`
2. **Extract** `_init_db()` as module-level function
3. **Add** docstrings for each table
4. **Add** migration notes
5. **Run** import validator
6. **Update** core.py `__init__` to call module function
7. **Test** fresh database initialization
8. **Commit**: `refactor(vault): Extract database schema to database.py`
9. **Push** to remote

**Validation:**
- [ ] Fresh DB initialization works
- [ ] All 18 tables created
- [ ] All indexes created
- [ ] No SQL errors

---

### **6.4.10: Finalize VaultService as Thin Orchestrator**
**What Remains in core.py:**
- `__init__()` - Service initialization
- All delegation methods (26 existing + 8 new)
- get_vault_service() singleton

**Step-by-step Process:**
1. **Update** all methods to delegate to new modules
2. **Add** imports for all 14 modules
3. **Remove** inline implementations
4. **Verify** all methods are delegating
5. **Add** comprehensive module docstring
6. **Run** full import validation
7. **Run** backend tests
8. **Test** all vault operations end-to-end
9. **Commit**: `refactor(vault): Finalize VaultService as orchestrator - 1538 → 200 lines`
10. **Push** to remote

**Final Module List:**
1. documents.py (existing) ✅
2. files.py (existing) ✅
3. folders.py (existing) ✅
4. search.py (existing) ✅
5. automation.py (existing) ✅
6. encryption.py (existing) ✅
7. tags.py (new) 🆕
8. favorites.py (new) 🆕
9. analytics.py (new) 🆕
10. sharing.py (updated) 📝
11. audit.py (new) 🆕
12. comments.py (new) 🆕
13. metadata.py (new) 🆕
14. media.py (new) 🆕
15. database.py (new) 🆕

**Final Validation:**
- [ ] core.py ~200 lines (down from 1538)
- [ ] All 15 modules import successfully
- [ ] Backend starts without errors
- [ ] All vault operations work
- [ ] Upload/download works
- [ ] Sharing works
- [ ] Comments work
- [ ] Tags work
- [ ] Favorites work
- [ ] Analytics work
- [ ] Audit logging works
- [ ] No performance regressions

---

## 📋 PHASE 6 COMPLETION CHECKLIST

### **Code Quality:**
- [ ] All files under 800 lines
- [ ] No duplicate code
- [ ] No unused imports
- [ ] Consistent naming conventions
- [ ] All functions have docstrings

### **Build & Tests:**
- [ ] Swift project builds with zero warnings
- [ ] Backend import validation passes
- [ ] Backend starts successfully
- [ ] All manual tests pass

### **Git Hygiene:**
- [ ] All feature branches merged to main
- [ ] All commits have descriptive messages
- [ ] All commits pushed to remote
- [ ] No merge conflicts

### **Documentation:**
- [ ] Update README if needed
- [ ] Document new module structure
- [ ] Note any breaking changes

---

## 🌥️ PHASE 5: MAGNETARCLOUD INTEGRATION

**Prerequisites:** Phase 6 complete
**Estimated Time:** 6-8 hours
**Risk Level:** VERY HIGH - Cloud infrastructure and OAuth

### **Pre-Implementation Research Phase (1 hour)**
- [ ] Review MagnetarCloud API documentation
- [ ] Understand OAuth 2.0 flow requirements
- [ ] Review sync strategy (conflict resolution)
- [ ] Plan backend endpoints needed
- [ ] Design client-side sync service

---

### **5.1: OAuth 2.0 Integration (2 hours)**

**Backend Components:**
1. Create OAuth client registration
2. Implement authorization endpoint handler
3. Implement token exchange endpoint
4. Add token refresh logic
5. Add secure token storage (encrypted)

**Swift Components:**
1. Create OAuthService.swift
2. Implement authorization URL generation
3. Handle redirect callback
4. Store tokens in Keychain
5. Automatic token refresh

**Step-by-step:**
1. **Backend - Create** `apps/backend/api/services/cloud/oauth.py`
   - Implement OAuth client
   - Add authorization handler
   - Add token exchange
   - Commit: `feat(cloud): Implement OAuth 2.0 backend`
   - Push

2. **Swift - Create** `apps/native/Shared/Services/OAuthService.swift`
   - Authorization flow
   - Token management
   - Keychain integration
   - Commit: `feat(cloud): Implement OAuth client in Swift`
   - Push

**Validation:**
- [ ] Can initiate OAuth flow
- [ ] Redirect URL works
- [ ] Tokens stored securely
- [ ] Token refresh works
- [ ] Error handling works

---

### **5.2: Sync Service Backend (2 hours)**

**Endpoints to Create:**
1. `/v1/cloud/sync/vault` - Vault sync
2. `/v1/cloud/sync/workflows` - Workflow sync
3. `/v1/cloud/sync/teams` - Team sync
4. `/v1/cloud/sync/status` - Sync status
5. `/v1/cloud/sync/conflicts` - Conflict resolution

**Database Schema:**
1. sync_state table (last sync timestamps)
2. sync_conflicts table (pending conflicts)
3. sync_log table (sync history)

**Step-by-step:**
1. **Create** `apps/backend/api/services/cloud/sync.py`
2. **Create** `apps/backend/api/routes/cloud.py`
3. **Implement** sync endpoints
4. **Add** conflict detection logic
5. **Add** delta sync (only changes since last sync)
6. **Test** with mock data
7. **Commit**: `feat(cloud): Implement sync service backend`
8. **Push**

**Validation:**
- [ ] Can detect changes
- [ ] Can push changes to cloud
- [ ] Can pull changes from cloud
- [ ] Conflicts detected correctly
- [ ] Delta sync reduces bandwidth

---

### **5.3: Sync Service Swift Client (1.5 hours)**

**Components:**
1. SyncService.swift - Main sync coordinator
2. SyncState.swift - Sync status tracking
3. ConflictResolver.swift - Conflict resolution UI

**Step-by-step:**
1. **Create** `apps/native/Shared/Services/SyncService.swift`
2. **Implement** sync coordinator
3. **Add** background sync with NSBackgroundActivityScheduler
4. **Create** conflict resolution UI
5. **Integrate** with VaultService, WorkflowService
6. **Add** sync status to UI
7. **Test** sync scenarios
8. **Commit**: `feat(cloud): Implement sync client in Swift`
9. **Push**

**Validation:**
- [ ] Manual sync works
- [ ] Automatic background sync works
- [ ] Conflicts shown to user
- [ ] User can resolve conflicts
- [ ] Sync status visible

---

### **5.4: Cloud Storage Integration (1.5 hours)**

**Features:**
1. Remote vault file storage
2. File versioning in cloud
3. Large file chunked upload
4. Background upload/download

**Step-by-step:**
1. **Backend - Create** `apps/backend/api/services/cloud/storage.py`
2. **Implement** chunked upload
3. **Implement** resume support
4. **Swift - Create** `apps/native/Shared/Services/CloudStorageService.swift`
5. **Implement** background upload queue
6. **Add** progress tracking
7. **Test** large file upload
8. **Commit**: `feat(cloud): Implement cloud storage service`
9. **Push**

**Validation:**
- [ ] Can upload files to cloud
- [ ] Can download files from cloud
- [ ] Resume works after network interruption
- [ ] Progress shown to user
- [ ] Background upload works

---

### **5.5: MagnetarHub Cloud UI (1 hour)**

**UI Components:**
1. Cloud connection status indicator
2. Sync now button
3. Conflict resolution modal
4. Cloud storage usage display
5. Account management

**Step-by-step:**
1. **Update** MagnetarHubWorkspace.swift
2. **Replace** placeholder cloud buttons with real implementations
3. **Add** sync status indicator
4. **Create** CloudSettingsView.swift
5. **Add** conflict resolution modal
6. **Test** all UI flows
7. **Commit**: `feat(cloud): Complete MagnetarHub cloud UI`
8. **Push**

**Validation:**
- [ ] Connection status accurate
- [ ] Sync button triggers sync
- [ ] Conflicts resolvable in UI
- [ ] Storage usage displays correctly
- [ ] Can disconnect account

---

### **5.6: Testing & Polish (1 hour)**

**Test Scenarios:**
1. First-time cloud setup
2. Offline → online sync
3. Conflict resolution (same file edited both sides)
4. Network interruption during sync
5. Large file upload/download
6. Multiple device sync

**Step-by-step:**
1. **Test** all scenarios above
2. **Fix** any bugs found
3. **Add** error messages for all failure cases
4. **Add** loading states
5. **Polish** animations
6. **Add** analytics/logging
7. **Commit**: `feat(cloud): Complete MagnetarCloud integration`
8. **Push**

**Final Validation:**
- [ ] All test scenarios pass
- [ ] No crashes or errors
- [ ] Errors have user-friendly messages
- [ ] Performance acceptable
- [ ] UI feels polished

---

## 📊 PHASE SUMMARY

### **Phase 6: Major Refactorings**
| Task | Files | Lines Reduced | Time | Status |
|------|-------|---------------|------|--------|
| 6.1 TeamWorkspace | 3196 → 8 files | 2896 lines split | 3-4h | ⏳ Pending |
| 6.2 AutomationWorkspace | 2040 → 15 files | 1840 lines split | 2-3h | ⏳ Pending |
| 6.3 team/core.py | 1785 → 4 files | 1185 lines split | 2.5h | ⏳ Pending |
| 6.4 vault/core.py | 1538 → 15 files | 1338 lines split | 2-3h | ⏳ Pending |
| **TOTAL** | **8559 → 42 files** | **7259 lines refactored** | **10-13h** | |

### **Phase 5: MagnetarCloud Integration**
| Task | Components | Time | Status |
|------|------------|------|--------|
| 5.1 OAuth | Backend + Swift | 2h | ⏳ Pending |
| 5.2 Sync Backend | Endpoints + DB | 2h | ⏳ Pending |
| 5.3 Sync Client | Swift service | 1.5h | ⏳ Pending |
| 5.4 Cloud Storage | Upload/download | 1.5h | ⏳ Pending |
| 5.5 Hub UI | UI components | 1h | ⏳ Pending |
| 5.6 Testing | E2E tests | 1h | ⏳ Pending |
| **TOTAL** | | **9h** | |

---

## 🎯 EXECUTION PRINCIPLES

### **Golden Rules:**
1. **Never skip commits** - Commit after every successful sub-phase
2. **Always push** - Push immediately after commit
3. **Build after every change** - Catch errors early
4. **Test each extraction** - Don't accumulate untested changes
5. **One file at a time** - Don't extract multiple files in one commit
6. **Descriptive commit messages** - Future you will thank you

### **If Something Breaks:**
1. **Don't panic** - Git has your back
2. **Check** compiler errors carefully
3. **Fix** imports first (usually the culprit)
4. **If stuck**, revert last commit and try smaller steps
5. **Ask** for help if needed (create GitHub issue)

### **Quality Gates:**
- **Before each commit:**
  - [ ] Build succeeds
  - [ ] No compiler warnings
  - [ ] Feature still works

- **Before each push:**
  - [ ] Commit message descriptive
  - [ ] No sensitive data in commit
  - [ ] Confidence level high

---

## 📅 ESTIMATED TIMELINE

**Assuming 4-hour focused work sessions:**

- **Session 1:** Phase 6.1 (TeamWorkspace) - 4 hours
- **Session 2:** Phase 6.2 (AutomationWorkspace) - 3 hours
- **Session 3:** Phase 6.3 + 6.4 start (Backend) - 4 hours
- **Session 4:** Phase 6.4 complete (Vault) - 3 hours
- **Session 5:** Phase 5.1 + 5.2 (OAuth + Sync backend) - 4 hours
- **Session 6:** Phase 5.3 + 5.4 (Sync client + Storage) - 3 hours
- **Session 7:** Phase 5.5 + 5.6 (UI + Testing) - 2 hours

**Total: ~23 hours across 7 sessions**

---

## ✅ SUCCESS CRITERIA

### **Phase 6 Success:**
- [ ] All 4 large files split into focused modules
- [ ] All commits follow conventions
- [ ] All tests pass
- [ ] No regressions in functionality
- [ ] Codebase easier to navigate
- [ ] New developer onboarding easier

### **Phase 5 Success:**
- [ ] Users can connect to MagnetarCloud
- [ ] OAuth flow works seamlessly
- [ ] Sync works reliably
- [ ] Conflicts resolved gracefully
- [ ] Cloud storage integrated
- [ ] UI polished and intuitive

---

**End of Roadmap**
**Last Updated:** 2025-12-08
**Next Action:** Begin Phase 6.1.1 - Extract TeamChatComponents.swift
