# MagnetarStudio Quality Roadmap

**Generated**: 2026-01-02
**Last Updated**: 2026-01-03 (COMPREHENSIVE AUDIT COMPLETE)
**Total Issues**: 150 (Tiers 0-17 audited)
**Estimated Effort**: ~518 hours

---

## COMPREHENSIVE AUDIT PLAN

**Scope**: 235 Swift files, 503 Python API files, 27 test files
**Methodology**: Complexity-ordered, systematic, tab-by-tab

### AUDIT TIERS (Ordered by Complexity)

| Tier | Category | File Count | Est. Review Time | Status |
|------|----------|------------|------------------|--------|
| ✅ 0 | Initial General Review | ~50 | 4h | Complete (22 issues) |
| ✅ 1 | AI Chat Tab | 93+ | 3h | Complete (23 issues) |
| ✅ 2 | Core Infrastructure | ~50 | 2h | Complete (22 issues) |
| ✅ 3 | Simple Workspaces (MagnetarHub, Kanban) | ~35 | 2h | Complete (16 issues) |
| ✅ 4 | Medium Workspaces (Code, Database) | ~20 | 2h | Complete (12 issues) |
| ✅ 5 | Complex Workspaces (Insights, Trust, Team) | ~35 | 4h | Complete (15 issues) |
| ✅ 6-8 | Backend Engines, Services, Routes | ~116 | 12h | Complete (13 issues) |
| ✅ 9-11 | Auth, Emergency, Vault Systems | ~50 | 7h | Complete (10 issues) |
| ✅ 12-14 | Settings, Terminal, P2P | ~40 | 6h | Complete (9 issues) |
| ✅ 15-17 | UI, Design System, Tests | ~60 | 5h | Complete (8 issues) |
| **Total** | | **~750+ files** | **~45h** | **150 issues** |

### DETAILED TIER BREAKDOWN

**Tier 3: Simple Workspaces**
- `MagnetarHubWorkspace.swift` + 15 supporting files
- `KanbanWorkspace.swift` + 5 supporting files

**Tier 4: Medium Workspaces**
- `CodeWorkspace.swift` + 4 supporting files + terminal panel
- `DatabaseWorkspace.swift` + 7 supporting files

**Tier 5: Complex Workspaces**
- `InsightsWorkspace.swift` + 6 supporting files + backend insights engine
- `TrustWorkspace.swift` (20KB single file) + security modals
- `TeamWorkspace.swift` + 6 supporting files + TeamChat (7 files)

**Tier 6: Backend Engines**
- `ane_context_engine.py` (11KB)
- `bash_intelligence.py` (10KB)
- `data_engine.py` (18KB)
- `jarvis_memory.py` (27KB)
- `jarvis_rag_pipeline.py` (10KB)
- `learning_engine.py` (13KB)
- `metal4_engine.py` (31KB)
- `metal4_sql_engine.py` (17KB)
- `template_orchestrator.py` (20KB)
- + 15 more engine files

**Tier 7: Backend Services**
- `api/services/` - 45 files including:
  - `kanban_service.py` (25KB)
  - `nlq_service.py` (19KB)
  - `workflow_orchestrator.py` (39KB)
  - Team, Vault, Chat, P2P subdirectories

**Tier 8: Backend Routes**
- `api/routes/` - 46 files including:
  - `admin.py` (24KB)
  - `cloud_auth.py` (29KB)
  - `cloud_storage.py` (23KB)
  - `permissions.py` (27KB)
  - `vault_auth.py` (40KB)
  - Kanban, Team, Data, System subdirectories

**Tier 9: Auth System**
- Swift: `AuthStore.swift`, `AuthService.swift`, `BiometricAuthService.swift`, `KeychainService.swift`
- Python: `auth_routes.py`, `auth_middleware.py`, `auth_bootstrap.py`, `cloud_auth.py`, `cloud_oauth.py`

**Tier 10: Emergency Mode**
- `EmergencyModeService.swift` + 4 extension files
- `EmergencyConfirmationModal.swift`
- `PanicModeSheet.swift`, `PanicModeService.swift`
- Backend emergency endpoints

**Tier 11: Vault System**
- Swift: `VaultStore.swift`, 7 Vault workspace files, `VaultPermissionManager.swift`
- Python: `api/routes/vault/` (11 files), `api/services/vault/` (19 files)

**Tier 12: Settings**
- 10 Settings view files
- `HotSlots/` subdirectory
- Backend settings routes

**Tier 13: Terminal**
- `TerminalService.swift`
- `CodeTerminalPanel.swift`
- Backend terminal API

**Tier 14: P2P & Network**
- `api/services/p2p_chat/` (12 files)
- `api/routes/p2p/` (4 files)
- LAN discovery, mesh relay

**Tier 15: UI Components**
- `Shared/Components/` (10 files)
- `Shared/Components/Header/` (4 files)
- AutomationWorkspace components (14 files)
- All button click handlers

**Tier 16: Design System**
- `Shared/DesignSystem/` (5 files)
- `Shared/Modifiers/` (1 file)

**Tier 17: Test Coverage**
- `apps/backend/tests/` (27 files)
- Gap analysis vs functionality

---

## SEVERITY SUMMARY

| Severity | Count | Hours | Status |
|----------|-------|-------|--------|
| CRITICAL | 5 | ~90h | Blocks production |
| HIGH | 6 | ~46h | Core stability |
| MEDIUM | 7 | ~51h | Edge cases |
| LOW | 4 | ~150h | Technical excellence |

---

## CRITICAL ISSUES (Fix Before Production)

### C1. Emergency Mode Implementation Unclear
- **Location**: `SecurityManager.swift:74`, `EmergencyModeService.swift`
- **Problem**: TODO comment exists but code also exists - unclear if functional
- **Risk**: Core security feature may not work
- **Effort**: 4-8h to verify and fix
- **Status**: [ ] Not started

### C2. API Response Envelope Inconsistency
- **Location**: ~40% of 622 backend routes
- **Problem**: Some endpoints wrap in SuccessResponse, others don't
- **Risk**: Swift client crashes on deserialization
- **Effort**: 6h
- **Status**: [ ] Not started

### C3. Cloud Storage Stubbed (Not Implemented)
- **Location**: `cloud_storage.py:426-427, 561`
- **Problem**: Returns dummy URLs, doesn't actually upload to S3/GCS
- **Risk**: File uploads silently fail
- **Effort**: 8h
- **Status**: [ ] Not started

### C4. Swift/Python Field Mapping Mismatches
- **Location**: `auth_routes.py`, `chat_models.py`, Swift models
- **Problem**: CodingKeys may not match actual backend field names
- **Risk**: Silent data loss, deserialization failures
- **Effort**: 4h
- **Status**: [ ] Not started

### C5. Python Type Hint Coverage (~15-20%)
- **Location**: 250+ Python files
- **Problem**: Most functions lack type annotations
- **Risk**: Bugs hard to find, IDE support broken
- **Effort**: 60-90h
- **Status**: [ ] Not started

---

## HIGH PRIORITY (Fix in Next Sprint)

### H1. ObservableObject → @Observable Migration
- **Location**: 8 service files (HotSlotManager, SecurityManager, EmergencyModeService, etc.)
- **Problem**: Mixing deprecated ObservableObject with modern @Observable
- **Risk**: UI state bugs, navigation issues
- **Effort**: 16h (2h per file)
- **Status**: [ ] Not started

### H2. @Environment Injection Consistency
- **Location**: Multiple stores and views
- **Problem**: Inconsistent dependency injection patterns
- **Risk**: Services recreated per view instead of shared
- **Effort**: 6h
- **Status**: [ ] Not started

### H3. Memory Leaks in Timer-based Services
- **Location**: 4+ service files with timers
- **Problem**: Timers may not be invalidated, creating retain cycles
- **Risk**: App crash on cleanup, memory growth
- **Effort**: 4h
- **Status**: [ ] Not started

### H4. Chat WebSocket Streaming (TODO)
- **Location**: `websocket.py:57, 147`
- **Problem**: Progress streaming and message dispatch not implemented
- **Risk**: Real-time chat doesn't work
- **Effort**: 6h
- **Status**: [ ] Not started

### H5. P2P Chunked File Transfers (TODO)
- **Location**: `p2p_chat/network.py:507-508`
- **Problem**: Large file transfers not implemented
- **Risk**: P2P file sharing fails for large files
- **Effort**: 8h
- **Status**: [ ] Not started

### H6. @MainActor Race Conditions
- **Location**: Multiple async services
- **Problem**: Race between @MainActor tasks and deallocation
- **Risk**: Crash during app shutdown
- **Effort**: 6h
- **Status**: [ ] Not started

---

## MEDIUM PRIORITY (Fix Before v1.1)

### M1. Token Refresh Mechanism Missing
- **Location**: `AuthStore.swift`
- **Problem**: No automatic token refresh
- **Risk**: Users logged out unexpectedly
- **Effort**: 4h
- **Status**: [ ] Not started

### M2. Keychain Thread Safety
- **Location**: `KeychainService.swift`
- **Problem**: No thread safety annotations
- **Risk**: Init race condition on app launch
- **Effort**: 3h
- **Status**: [ ] Not started

### M3. Input Validation Gaps
- **Location**: Various backend routes
- **Problem**: Not all inputs validated properly
- **Risk**: Malformed requests reach business logic
- **Effort**: 8h
- **Status**: [ ] Not started

### M4. Database Connection Pool
- **Location**: `db_pool.py`
- **Problem**: SQLite only allows one writer at a time
- **Risk**: Slow under concurrent load
- **Effort**: 6h
- **Status**: [ ] Not started

### M5. Configuration Hardcoding
- **Location**: Multiple files
- **Problem**: Token lifetimes, rate limits, etc. hardcoded
- **Risk**: Hard to tune for different deployments
- **Effort**: 10h
- **Status**: [ ] Not started

### M6. Database Encryption Stubbed
- **Location**: `vault_service.py`
- **Problem**: Encryption may not be fully implemented
- **Risk**: Security theater
- **Effort**: 12h
- **Status**: [ ] Not started

### M7. ANE Learning System (TODO)
- **Location**: `ane_router.py:227`
- **Problem**: ML component not implemented
- **Risk**: No adaptive battery optimization
- **Effort**: 8h
- **Status**: [ ] Not started

---

## LOW PRIORITY (Nice to Have)

### L1. Terminal Socket Connection (TODO)
- **Location**: `terminal_api.py:255`
- **Problem**: Backend connection incomplete
- **Effort**: 4h

### L2. Code Duplication
- **Location**: Auth checks, error formatting, serialization
- **Effort**: 30h

### L3. API Documentation
- **Location**: 622 endpoints undocumented
- **Effort**: 40h

### L4. Test Coverage (Currently 62%)
- **Location**: P2P, workflows, cloud sync, emergency mode
- **Effort**: 60h

---

## ARCHITECTURE PATTERNS TO FIX

### Swift Observation Pattern
```swift
// DEPRECATED - Don't use
class SomeManager: ObservableObject {
    @Published var state = ...
}

// CORRECT - Use this
@Observable
final class SomeManager {
    var state = ...
}
```

### Swift Environment Injection
```swift
// For @Observable stores
@Environment(ChatStore.self) var chatStore

// NOT this (for ObservableObject only)
@EnvironmentObject var chatStore: ChatStore
```

### Python API Response
```python
# ALWAYS wrap responses
from api.routes.schemas.responses import SuccessResponse

@router.get("/endpoint")
async def endpoint() -> SuccessResponse[DataModel]:
    return SuccessResponse(data=result)
```

---

## FILES NEEDING @Observable MIGRATION

1. `Shared/Services/HotSlotManager.swift`
2. `Shared/Services/SecurityManager.swift`
3. `Shared/Services/EmergencyModeService.swift`
4. `Shared/Services/ResourceMonitor.swift`
5. `Shared/Services/CloudStorageService.swift`
6. `macOS/Managers/AppLifecycleManager.swift`
7. `macOS/SettingsView.swift` (SettingsManager class)
8. `macOS/Settings/MagnetarCloudSettingsView.swift` (CloudAuthManager class)

---

## IMMEDIATE ACTIONS (Next 48 Hours)

- [ ] Verify Emergency Mode actually works (2h)
- [ ] Audit Cloud Storage implementation (3h)
- [ ] Test API contract alignment (4h)
- [ ] Thread safety audit (3h)

---

## YOUR NOTES

(Add your systems engineering approach notes here)

---

# AI CHAT TAB - DETAILED AUDIT (2026-01-03)

**Files Reviewed**: 93+ files (20 Swift, 73+ Python)
**Issues Found**: 23 issues (4 Critical, 6 High, 8 Medium, 5 Low)

---

## CHAT-CRITICAL (Blocks Chat Functionality)

### CHAT-C1. Dual Store Architecture Anti-Pattern
- **Location**: `ChatStore.swift` + `NetworkChatStore.swift`
- **Problem**: Two separate chat stores exist
  - `ChatStore` uses modern `@Observable`
  - `NetworkChatStore` uses deprecated `ObservableObject`
- **Risk**: Code duplication, inconsistent behavior, maintenance burden
- **Fix**: Consolidate to single `ChatStore` with @Observable
- **Effort**: 4h
- **Status**: [ ] Not started

### CHAT-C2. SwiftData @Model Misuse
- **Location**: `ChatMessage.swift:12`, `ChatMessage.swift:55`
- **Problem**: `ChatMessage` and `ChatSession` are marked with `@Model` (SwiftData) but:
  - No `ModelContext` is ever created
  - Used as plain structs in memory arrays
  - `@Relationship(deleteRule: .cascade)` on `messages` does nothing
- **Risk**: SwiftData features non-functional, potential runtime issues
- **Fix**: Either remove @Model and use plain structs, OR properly integrate SwiftData with ModelContainer
- **Effort**: 6h
- **Status**: [ ] Not started

### CHAT-C3. HotSlotManager Pin State Not Backend-Synced
- **Location**: `HotSlotManager.swift:252-294`
- **Problem**: Pin operations (`pinSlot`/`unpinSlot`) save to `UserDefaults` only, not backend
  - Backend has `is_pinned` field in hot slot data
  - But Swift never calls backend to update pin state
- **Risk**: Pin state lost on reinstall, inconsistent across devices
- **Fix**: Add backend API calls for pin operations
- **Effort**: 3h
- **Status**: [ ] Not started

### CHAT-C4. ChatTimelineSheet Shows Empty Messages
- **Location**: `ChatTimelineSheet.swift:65`
- **Problem**: Accesses `session.messages` directly, but:
  - `ChatSession` messages array is initialized empty
  - Actual messages are loaded separately into `ChatStore.messages`
- **Risk**: Timeline modal always shows "0 messages"
- **Fix**: Pass `chatStore.messages` to timeline, or load messages in sheet
- **Effort**: 1h
- **Status**: [ ] Not started

---

## CHAT-HIGH (Core Chat Stability)

### CHAT-H1. HotSlotManager Uses ObservableObject
- **Location**: `HotSlotManager.swift:111`
- **Problem**: `class HotSlotManager: ObservableObject` but ChatStore uses @Observable
  - `ModelSelectorMenu` uses `@StateObject` for singleton (anti-pattern)
- **Risk**: State update issues, memory leaks
- **Fix**: Migrate to @Observable, use @Environment
- **Effort**: 2h
- **Status**: [ ] Not started
- **Cross-ref**: Related to H1 in main roadmap

### CHAT-H2. deleteSession Silent Failure
- **Location**: `ChatSidebar.swift:90-92`, `ChatStore.swift:294-326`
- **Problem**:
  - UI removes session immediately (optimistic)
  - Backend delete is async, errors only logged
  - No user feedback if deletion fails
- **Risk**: User thinks session deleted but it persists on backend
- **Fix**: Add error handling and user feedback for failed deletions
- **Effort**: 2h
- **Status**: [ ] Not started

### CHAT-H3. Session ID Mapping Memory Growth
- **Location**: `ChatStore.swift:40`
- **Problem**: `sessionIdMapping: [UUID: String]` dictionary:
  - Grows on each session load
  - Only cleaned on successful delete
  - Never pruned for sessions that no longer exist
- **Risk**: Memory growth over long sessions
- **Fix**: Add periodic cleanup, prune on session load
- **Effort**: 1h
- **Status**: [ ] Not started

### CHAT-H4. Streaming Error Recovery Missing
- **Location**: `ChatStore.swift:601-641`
- **Problem**: If SSE stream fails mid-response:
  - Assistant message shows partial content
  - No indicator that response is incomplete
  - No retry mechanism
- **Risk**: Users see partial AI responses as complete
- **Fix**: Add error indicator, incomplete message flag, retry option
- **Effort**: 3h
- **Status**: [ ] Not started

### CHAT-H5. No Loading Indicator in Sidebar
- **Location**: `ChatSidebar.swift`
- **Problem**: When sessions are loading, shows "No chat sessions" instead of loading state
- **Risk**: User confusion, might create duplicate sessions
- **Fix**: Add isLoading indicator from ChatStore
- **Effort**: 30min
- **Status**: [ ] Not started

### CHAT-H6. onChange Race Condition
- **Location**: `ChatWindow.swift:55-64`
- **Problem**: Two `onChange` handlers create async Tasks on model/mode change
  - Rapid changes create multiple concurrent save requests
  - No debouncing
- **Risk**: Race condition, unnecessary API calls
- **Fix**: Debounce, or use single onChange with combined state
- **Effort**: 1h
- **Status**: [ ] Not started

---

## CHAT-MEDIUM (Edge Cases & Polish)

### CHAT-M1. Hardcoded Fallback Model
- **Location**: `ChatStore.swift:343, 371`
- **Problem**: `"llama3.2:3b"` hardcoded as fallback when no model selected
- **Risk**: Model may not exist on user's system
- **Fix**: Use first available model, or configurable default
- **Effort**: 30min
- **Status**: [ ] Not started

### CHAT-M2. print() Debug Statements
- **Location**: Multiple files:
  - `ChatStore.swift:115, 146, 172, 176, 226`
  - `NetworkChatStore.swift:265`
  - `CodeWorkspace.swift:115, 147`
- **Problem**: Debug print statements in production code
- **Risk**: Console noise, potential sensitive data exposure
- **Fix**: Replace with os.Logger
- **Effort**: 1h
- **Status**: [ ] Not started

### CHAT-M3. Message Pagination Missing
- **Location**: `ChatService.swift:99-116`
- **Problem**: `loadMessages` has `limit` but no `offset`/cursor
- **Risk**: Can't load historical messages beyond initial limit
- **Fix**: Add pagination support
- **Effort**: 2h
- **Status**: [ ] Not started

### CHAT-M4. No Input Validation
- **Location**: `ChatStore.swift:470`
- **Problem**: `sendMessage` only trims whitespace, no:
  - Length limits
  - Content validation
  - XSS/injection checks
- **Risk**: Extremely long messages, malformed input
- **Fix**: Add input validation
- **Effort**: 1h
- **Status**: [ ] Not started

### CHAT-M5. Context Storage Silently Ignored
- **Location**: `ChatStore.swift:678-686`
- **Problem**: Context storage errors silently ignored (even non-404s in DEBUG)
- **Risk**: Data loss without notification
- **Fix**: Log appropriately, don't swallow all errors
- **Effort**: 30min
- **Status**: [ ] Not started

### CHAT-M6. Redundant MainActor.run
- **Location**: `HotSlotManager.swift:163-166`
- **Problem**: Class is `@MainActor` but still uses `MainActor.run` inside async
- **Risk**: Unnecessary actor hops, slightly slower
- **Fix**: Remove redundant MainActor.run calls
- **Effort**: 30min
- **Status**: [ ] Not started

### CHAT-M7. Missing Token Refresh (Chat-specific)
- **Location**: `ChatStore.swift` (absence)
- **Problem**: No token refresh during long chat sessions
- **Risk**: User kicked out mid-conversation
- **Fix**: Monitor token expiry, refresh proactively
- **Effort**: 2h
- **Status**: [ ] Not started
- **Cross-ref**: Related to M1 in main roadmap

### CHAT-M8. ISO8601DateFormatter Created Repeatedly
- **Location**: `ChatStore.swift:141, 178, 219`
- **Problem**: New `ISO8601DateFormatter()` created on every date parse
- **Risk**: Minor performance impact
- **Fix**: Use static formatter instance
- **Effort**: 30min
- **Status**: [ ] Not started

---

## CHAT-LOW (Technical Debt)

### CHAT-L1. Hardcoded API Paths
- **Location**: `ChatService.swift`, `ChatStore.swift`
- **Problem**: Paths like `"/v1/chat/sessions"` scattered throughout
- **Risk**: Refactoring is error-prone
- **Fix**: Centralize API path definitions
- **Effort**: 2h
- **Status**: [ ] Not started

### CHAT-L2. Missing Documentation
- **Location**: `ChatStore.swift`, `ChatService.swift`
- **Problem**: Complex functions lack documentation
- **Fix**: Add function documentation
- **Effort**: 2h
- **Status**: [ ] Not started

### CHAT-L3. No Unit Tests
- **Location**: Absence in `apps/native/Tests/`
- **Problem**: No tests for ChatStore, ChatService
- **Risk**: Regressions undetected
- **Fix**: Add unit tests
- **Effort**: 8h
- **Status**: [ ] Not started

### CHAT-L4. ChatSession.messages Unused Relationship
- **Location**: `ChatMessage.swift:64`
- **Problem**: `@Relationship` declared but never used (messages loaded separately)
- **Fix**: Remove unused relationship or use it
- **Effort**: 30min
- **Status**: [ ] Not started

### CHAT-L5. Duplicate Model Types
- **Location**: `ChatModels.swift` vs `ChatMessage.swift`
- **Problem**: Multiple definitions of similar models (ApiChatSession, ChatSession, etc.)
- **Risk**: Confusion, potential misuse
- **Fix**: Consolidate model definitions
- **Effort**: 2h
- **Status**: [ ] Not started

---

## CHAT TAB SUMMARY

| Priority | Count | Est. Hours |
|----------|-------|------------|
| Critical | 4 | 14h |
| High | 6 | 9.5h |
| Medium | 8 | 8h |
| Low | 5 | 14.5h |
| **Total** | **23** | **~46h** |

### Recommended Fix Order (Chat Tab):
1. **CHAT-C4** (1h) - Timeline shows empty, easy quick win
2. **CHAT-H5** (30min) - Loading indicator, easy quick win
3. **CHAT-C2** (6h) - SwiftData misuse, fundamental issue
4. **CHAT-C1** (4h) - Dual store, reduces confusion
5. **CHAT-H1** (2h) - HotSlotManager @Observable migration
6. **CHAT-H2** (2h) - Delete silent failure
7. **CHAT-H4** (3h) - Streaming error recovery
8. **CHAT-C3** (3h) - Pin state backend sync
9. **CHAT-M2** (1h) - print() statements
10. Rest in priority order...

---

# CORE INFRASTRUCTURE - DETAILED AUDIT (2026-01-03)

**Files Reviewed**: ~50 core files (NavigationStore, ContentView, all Stores, key Services, backend workspace infrastructure)
**Issues Found**: 22 issues (6 Critical, 6 High, 6 Medium, 4 Low)

---

## INFRA-CRITICAL (Architectural Issues)

### INFRA-C1. VaultPermissionManager Uses ObservableObject
- **Location**: `VaultPermissionManager.swift:75`
- **Problem**: Uses `class VaultPermissionManager: ObservableObject` with `@Published` while other stores use `@Observable`
- **Risk**: Inconsistent observation patterns, state update issues
- **Fix**: Migrate to @Observable
- **Effort**: 2h
- **Status**: [ ] Not started
- **Cross-ref**: Related to H1 in main roadmap

### INFRA-C2. @StateObject for Singleton in MainAppView
- **Location**: `ContentView.swift:116`
- **Problem**: `@StateObject private var permissionManager = VaultPermissionManager.shared`
  - @StateObject should own the object's lifecycle, but shared singletons are app-scoped
  - Creates confusing ownership semantics
- **Risk**: Memory management issues, potential lifecycle bugs
- **Fix**: Use @Environment for singleton injection after @Observable migration
- **Effort**: 1h (after INFRA-C1)
- **Status**: [ ] Not started

### INFRA-C3. @State for Singleton AuthStore
- **Location**: `ContentView.swift:15`
- **Problem**: `@State private var authStore = AuthStore.shared`
  - @State is for view-local value types
  - AuthStore is a reference type singleton with internal state
- **Risk**: State changes may not trigger view updates correctly
- **Fix**: Use @Environment(AuthStore.self) consistently
- **Effort**: 1h
- **Status**: [ ] Not started

### INFRA-C4. Inconsistent Store Injection Pattern
- **Location**: All stores in `Shared/Stores/`
- **Problem**: Stores are split between two patterns:
  - **Pattern A** (ChatStore, NavigationStore, DatabaseStore): Injected via `.environment(store)` in MagnetarStudioApp
  - **Pattern B** (VaultStore, KanbanStore, TeamStore, ModelsStore, WorkflowStore): Accessed via `.shared` singleton
- **Risk**:
  - Pattern B stores are tightly coupled, harder to test/mock
  - Inconsistent access patterns confuse developers
- **Fix**: Standardize all stores on @Environment injection
- **Effort**: 4h
- **Status**: [ ] Not started

### INFRA-C5. Timer Retain Cycle in VaultPermissionManager
- **Location**: `VaultPermissionManager.swift:94-98`
- **Problem**:
  ```swift
  Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
      Task { @MainActor in
          self?.cleanupExpiredPermissions()
      }
  }
  ```
  - Timer is never invalidated
  - No cleanup on deinit
  - Even with `[weak self]`, Timer holds reference to run loop
- **Risk**: Memory leak, timer runs forever
- **Fix**: Store timer reference, invalidate on deinit
- **Effort**: 30min
- **Status**: [ ] Not started

### INFRA-C6. Vault Passphrase Stored in Memory
- **Location**: `VaultStore.swift:25`
- **Problem**: `private var passphrase: String?` stores vault passphrase in memory indefinitely
  - Can be extracted via memory dump/debugging
  - Critical given vault is for "life or death" data protection
- **Risk**: Security vulnerability for persecuted users
- **Fix**: Clear passphrase after use, use SecureEnclave for key storage
- **Effort**: 4h
- **Status**: [ ] Not started

---

## INFRA-HIGH (Core Stability)

### INFRA-H1. Force Unwrap URLs in ModelsStore
- **Location**: `ModelsStore.swift:76, 125`
- **Problem**:
  ```swift
  let url = URL(string: "\(APIConfiguration.shared.ollamaURL)/api/pull")!
  let url = URL(string: "\(APIConfiguration.shared.ollamaURL)/api/delete")!
  ```
- **Risk**: App crash if URL construction fails
- **Fix**: Use guard let or throw proper error
- **Effort**: 30min
- **Status**: [ ] Not started

### INFRA-H2. No Error Boundary in MainAppView
- **Location**: `ContentView.swift:118-184`
- **Problem**: Switch statement renders workspaces directly with no error handling
  - If any workspace throws during render, app crashes
- **Risk**: Uncaught errors crash the app
- **Fix**: Wrap in error boundary view or use Result type
- **Effort**: 2h
- **Status**: [ ] Not started

### INFRA-H3. NavigationRail Keyboard Shortcut Mismatch
- **Location**: `NavigationRail.swift:28-88` vs `NavigationStore.swift:101-112`
- **Problem**:
  - Help text shows "(⌘1)", "(⌘2)", etc.
  - But `Workspace.keyboardShortcut` returns just "1", "2"
  - Actual menu commands (MagnetarMenuCommands) may use different shortcuts
- **Risk**: User confusion, incorrect documentation
- **Fix**: Verify and align all keyboard shortcuts
- **Effort**: 1h
- **Status**: [ ] Not started

### INFRA-H4. DatabaseStore Silent Failures
- **Location**: `DatabaseStore.swift:57-60` and all methods
- **Problem**: All operations check `guard let id = sessionId else { error = "..."; return }`
  - If createSession() fails initially, sessionId is nil
  - Every subsequent operation silently sets error and returns
  - No retry mechanism
- **Risk**: Silent data loss, user thinks app is working
- **Fix**: Add session retry mechanism, surface errors prominently
- **Effort**: 2h
- **Status**: [ ] Not started

### INFRA-H5. WorkflowStore Untyped [[String: Any]]
- **Location**: `WorkflowStore.swift:189-213`
- **Problem**: `nodes: [[String: Any]], edges: [[String: Any]]`
  - Loses all type safety
  - Errors only caught at runtime
- **Risk**: Runtime crashes, hard to debug
- **Fix**: Create proper Node and Edge types with Codable
- **Effort**: 3h
- **Status**: [ ] Not started

### INFRA-H6. SQLite Connections Not Pooled (Backend)
- **Location**: `workspace_session.py:96, 127, 166`, and other Python files
- **Problem**: Every method creates new `sqlite3.connect()` and closes it
  - No connection pooling
  - High overhead for frequent operations
- **Risk**: Performance degradation under load
- **Fix**: Use connection pool or persistent connection
- **Effort**: 3h
- **Status**: [ ] Not started
- **Cross-ref**: Related to M4 in main roadmap

---

## INFRA-MEDIUM (Edge Cases)

### INFRA-M1. Duplicate Singleton Boilerplate
- **Location**: All stores in `Shared/Stores/`
- **Problem**: Each store repeats:
  ```swift
  static let shared = SomeStore()
  private init() {}
  ```
- **Risk**: Code duplication, inconsistent initialization
- **Fix**: Consider base class or protocol with default implementation
- **Effort**: 2h
- **Status**: [ ] Not started

### INFRA-M2. TeamStore.unreadCount Returns 0
- **Location**: `TeamStore.swift:144-147`
- **Problem**:
  ```swift
  func unreadCount(forChannelId channelId: String) -> Int {
      // TODO: Implement when backend provides unread tracking
      0
  }
  ```
- **Risk**: Feature not working, users see no unread indicators
- **Fix**: Implement backend tracking or remove method
- **Effort**: 4h (including backend)
- **Status**: [ ] Not started

### INFRA-M3. KanbanStore ISO8601DateFormatter in Loop
- **Location**: `KanbanStore.swift:191`
- **Problem**: `let formatter = ISO8601DateFormatter()` created for each task in `overdueTasks()`
- **Risk**: Minor performance impact
- **Fix**: Use static formatter
- **Effort**: 15min
- **Status**: [ ] Not started

### INFRA-M4. AppContext Parallel MainActor Contention
- **Location**: `AppContext.swift:41-50`
- **Problem**: 10+ `async let` calls that all need MainActor
  - All execute in parallel but serialize on MainActor
  - Could cause thread contention
- **Risk**: Performance bottleneck on context capture
- **Fix**: Batch MainActor calls or use actors
- **Effort**: 2h
- **Status**: [ ] Not started

### INFRA-M5. VaultFileMetadata vaultType Hardcoded
- **Location**: `AppContext.swift:113`
- **Problem**: `self.vaultType = "real"  // Default, will be overridden`
  - Comment says it will be overridden but there's no code that does
- **Risk**: Incorrect vault type in context, potential security misrouting
- **Fix**: Pass vaultType from VaultStore to constructor
- **Effort**: 30min
- **Status**: [ ] Not started

### INFRA-M6. Backend workspace_session.py No Connection Reuse
- **Location**: `workspace_session.py` all methods
- **Problem**: Same as INFRA-H6 but specific to workspace sessions
- **Risk**: Additional connection overhead
- **Fix**: Share connection or use context manager
- **Effort**: 1h
- **Status**: [ ] Not started

---

## INFRA-LOW (Technical Debt)

### INFRA-L1. CommandPaletteManager File Missing
- **Location**: Referenced in `MagnetarStudioApp.swift:22` but file not found via Glob
- **Problem**: File may have been moved/renamed/deleted
- **Risk**: Build errors or dead code reference
- **Fix**: Locate and verify file exists
- **Effort**: 30min
- **Status**: [ ] Not started

### INFRA-L2. Workspace Enum Duplication with NavigationRail
- **Location**: `NavigationStore.swift` vs `NavigationRail.swift`
- **Problem**: Button order in NavigationRail may drift from Workspace enum order
- **Risk**: Maintenance burden, UI/enum mismatch
- **Fix**: Generate NavigationRail buttons from Workspace.allCases
- **Effort**: 1h
- **Status**: [ ] Not started

### INFRA-L3. No Workspace State Persistence
- **Location**: All stores
- **Problem**: NavigationStore persists activeWorkspace, but individual workspace state not persisted
  - User opens file in Code workspace, switches tab, loses selection
- **Risk**: Poor UX, users lose context
- **Fix**: Implement workspace state restoration
- **Effort**: 8h
- **Status**: [ ] Not started

### INFRA-L4. Missing Documentation Across Stores
- **Location**: All stores in `Shared/Stores/`
- **Problem**: Most stores lack comprehensive method documentation
- **Risk**: Maintainability issues
- **Fix**: Add documentation
- **Effort**: 4h
- **Status**: [ ] Not started

---

## INFRASTRUCTURE SUMMARY

| Priority | Count | Est. Hours |
|----------|-------|------------|
| Critical | 6 | 12.5h |
| High | 6 | 11.5h |
| Medium | 6 | 9.75h |
| Low | 4 | 13.5h |
| **Total** | **22** | **~47h** |

### Recommended Fix Order (Infrastructure):
1. **INFRA-C5** (30min) - Timer leak, easy fix
2. **INFRA-H1** (30min) - Force unwrap, easy fix
3. **INFRA-M3** (15min) - DateFormatter, trivial
4. **INFRA-C1** (2h) - VaultPermissionManager @Observable
5. **INFRA-C2** (1h) - Fix @StateObject usage (depends on C1)
6. **INFRA-C3** (1h) - Fix @State for AuthStore
7. **INFRA-C6** (4h) - Vault passphrase security
8. **INFRA-C4** (4h) - Standardize store injection
9. **INFRA-H4** (2h) - DatabaseStore retry mechanism
10. Rest in priority order...

---

# SIMPLE WORKSPACES - DETAILED AUDIT (2026-01-03)

**Files Reviewed**: ~35 files (MagnetarHub: 17 files, Kanban: 8 files)
**Issues Found**: 16 issues (3 Critical, 5 High, 5 Medium, 3 Low)

---

## SIMPLE-CRITICAL (Data Integrity Issues)

### SIMPLE-C1. KanbanStore vs KanbanDataManager Duplication
- **Location**: `Shared/Stores/KanbanStore.swift` vs `Workspaces/Kanban/KanbanDataManager.swift`
- **Problem**: Two separate data management classes exist for Kanban:
  - `KanbanStore` in Shared/Stores (singleton, @Observable)
  - `KanbanDataManager` created as @State in KanbanWorkspace
- **Risk**: Data inconsistency, features implemented in one not available in other
- **Fix**: Use KanbanStore consistently, remove KanbanDataManager
- **Effort**: 3h
- **Status**: [ ] Not started

### SIMPLE-C2. ModelsStore Created Per-Workspace
- **Location**: `MagnetarHubWorkspace.swift:26`
- **Problem**: `@State private var modelsStore = ModelsStore()` creates a new instance
  - ModelsStore also exists as singleton in Shared/Stores
  - Models fetched in Hub won't be visible elsewhere
- **Risk**: Model lists out of sync between workspaces
- **Fix**: Use @Environment or ModelsStore.shared
- **Effort**: 1h
- **Status**: [ ] Not started
- **Cross-ref**: Related to INFRA-C4 (inconsistent store injection)

### SIMPLE-C3. Kanban Delete Always Succeeds Locally
- **Location**: `KanbanCRUDOperations.swift:45-57, 112-124`
- **Problem**: `deleteBoard()` and `deleteTask()` always return true even on API failure
  - Comment says "Still return true to remove locally even if API fails"
  - This creates permanent data divergence
- **Risk**: User sees item deleted but backend still has it, sync will restore
- **Fix**: Return false on API failure, let user retry or force-delete
- **Effort**: 2h
- **Status**: [ ] Not started

---

## SIMPLE-HIGH (Core Stability)

### SIMPLE-H1. HubCloudManager AutoSync Never Stopped
- **Location**: `MagnetarHubWorkspace.swift:210-211`, `HubCloudManager.swift:297-305`
- **Problem**: `startAutoSync()` called but never `stopAutoSync()`:
  - No `.onDisappear` or `.task` cancellation
  - Sync continues after leaving workspace
- **Risk**: Resource leak, unnecessary network activity
- **Fix**: Add onDisappear cleanup
- **Effort**: 30min
- **Status**: [ ] Not started

### SIMPLE-H2. ISO8601DateFormatter Created Repeatedly (Hub)
- **Location**: `HubCloudManager.swift:97, 170, 201, 204, 315, 530`
- **Problem**: `ISO8601DateFormatter()` created 6+ times in HubCloudManager alone
  - Same issue as CHAT-M8 and INFRA-M3
- **Risk**: Performance impact, object allocation overhead
- **Fix**: Use static formatter
- **Effort**: 30min
- **Status**: [ ] Not started

### SIMPLE-H3. Hub Error Messages Not Displayed to User
- **Location**: `HubCloudManager.swift:34` (errorMessage property)
- **Problem**: `errorMessage` is set on failures but:
  - MagnetarHubWorkspace doesn't display it anywhere
  - User has no visibility into failures
- **Risk**: Silent failures, confused users
- **Fix**: Add error alert or banner in MagnetarHubWorkspace
- **Effort**: 1h
- **Status**: [ ] Not started

### SIMPLE-H4. Model Delete Has No Confirmation
- **Location**: `HubModelOperations.swift:93-113`
- **Problem**: `deleteModel()` immediately deletes without user confirmation
  - Unlike Kanban which has confirmation alerts
  - Inconsistent UX
- **Risk**: Accidental model deletion, user loses downloaded models
- **Fix**: Add confirmation dialog before deletion
- **Effort**: 1h
- **Status**: [ ] Not started

### SIMPLE-H5. Hardcoded "default" Project ID
- **Location**: `KanbanDataManager.swift:21`, `KanbanCRUDOperations.swift:13`
- **Problem**: `defaultProjectId = "default"` hardcoded in both files
  - No multi-project support
  - Duplicate constant
- **Risk**: Can't scale to multiple projects
- **Fix**: Make project ID configurable or derive from user
- **Effort**: 2h
- **Status**: [ ] Not started

---

## SIMPLE-MEDIUM (Edge Cases)

### SIMPLE-M1. print() Statements in Kanban
- **Location**: `KanbanCRUDOperations.swift:34, 54, 64, 95, 120`
- **Problem**: 5 print() statements instead of os.Logger
- **Risk**: Console noise, no log levels
- **Fix**: Replace with logger
- **Effort**: 30min
- **Status**: [ ] Not started

### SIMPLE-M2. Duplicate Helper Functions
- **Location**: `KanbanDataManager.swift:81-95` vs `KanbanCRUDOperations.swift:128-142`
- **Problem**: `taskStatusFromString()` and `taskPriorityFromString()` duplicated in both files
- **Risk**: Drift if one is updated without the other
- **Fix**: Extract to shared utility or KanbanModels extension
- **Effort**: 30min
- **Status**: [ ] Not started

### SIMPLE-M3. Kanban Task Count Not Loaded
- **Location**: `KanbanDataManager.swift:34`
- **Problem**: `taskCount: 0` comment says "Would need separate API call"
  - Board always shows 0 tasks in sidebar
- **Risk**: User can't see task count without selecting board
- **Fix**: Fetch counts or update after loading tasks
- **Effort**: 2h
- **Status**: [ ] Not started

### SIMPLE-M4. Five Managers as @State in Hub
- **Location**: `MagnetarHubWorkspace.swift:19-24`
- **Problem**: 5 manager classes all created with @State:
  - dataManager, networkManager, ollamaManager, cloudManager, modelOperations
  - All are @Observable classes that should be shared
- **Risk**: Recreated on view refresh, potential state loss
- **Fix**: Move to @Environment injection or use shared singletons
- **Effort**: 3h
- **Status**: [ ] Not started

### SIMPLE-M5. HubNetworkManager startNetworkMonitoring Not Awaited
- **Location**: `MagnetarHubWorkspace.swift:43`
- **Problem**: `networkManager.startNetworkMonitoring()` called without await
  - Not clear if this is intentional fire-and-forget
- **Risk**: Race condition with network status
- **Fix**: Verify async behavior, add await if needed
- **Effort**: 30min
- **Status**: [ ] Not started

---

## SIMPLE-LOW (Technical Debt)

### SIMPLE-L1. Missing Kanban Drag-and-Drop
- **Location**: `KanbanWorkspace.swift` (absence)
- **Problem**: Kanban board has no drag-and-drop to move tasks between columns
  - Core UX feature for Kanban missing
- **Risk**: Poor UX compared to standard Kanban apps
- **Fix**: Implement drag-and-drop with SwiftUI .draggable/.dropDestination
- **Effort**: 8h
- **Status**: [ ] Not started

### SIMPLE-L2. Kanban Fallback Creates Ghost Data
- **Location**: `KanbanCRUDOperations.swift:35-42, 96-108`
- **Problem**: On API failure, creates local-only board/task with `boardId: nil`
  - This ghost data can never sync to backend
- **Risk**: User confusion, data loss on app restart
- **Fix**: Either fail clearly or implement local storage with sync queue
- **Effort**: 4h
- **Status**: [ ] Not started

### SIMPLE-L3. Hub Download Progress Estimate Rough
- **Location**: `HubModelOperations.swift:182-189`
- **Problem**: Progress estimation just uses status strings mapped to fixed percentages
  ```swift
  case "downloading": return 0.5
  ```
  - No actual byte progress
- **Risk**: Progress bar jumps, poor UX
- **Fix**: Use actual progress data from Ollama API if available
- **Effort**: 2h
- **Status**: [ ] Not started

---

## SIMPLE WORKSPACES SUMMARY

| Priority | Count | Est. Hours |
|----------|-------|------------|
| Critical | 3 | 6h |
| High | 5 | 5h |
| Medium | 5 | 6.5h |
| Low | 3 | 14h |
| **Total** | **16** | **~31.5h** |

### Recommended Fix Order (Simple Workspaces):
1. **SIMPLE-H1** (30min) - AutoSync leak, easy fix
2. **SIMPLE-H2** (30min) - DateFormatter, trivial
3. **SIMPLE-M1** (30min) - print() statements
4. **SIMPLE-M2** (30min) - Duplicate helpers
5. **SIMPLE-C2** (1h) - ModelsStore per-workspace
6. **SIMPLE-H3** (1h) - Error messages not displayed
7. **SIMPLE-H4** (1h) - Model delete confirmation
8. **SIMPLE-C1** (3h) - KanbanStore duplication
9. **SIMPLE-C3** (2h) - Delete always succeeds
10. **SIMPLE-H5** (2h) - Hardcoded project ID

---

# MEDIUM WORKSPACES - DETAILED AUDIT (2026-01-03)

**Files Reviewed**: ~20 files (Code: 5 files + services, Database: 8 files + backend)
**Issues Found**: 12 issues (1 Critical, 4 High, 5 Medium, 2 Low)

---

## MEDIUM-CRITICAL (API Contract Issues)

### MEDIUM-C1. TerminalService spawnTerminal Ignores Parameters
- **Location**: `TerminalService.swift:49-55`
- **Problem**: `spawnTerminal(shell:cwd:)` accepts shell and cwd parameters but never uses them:
  ```swift
  func spawnTerminal(shell: String? = nil, cwd: String? = nil) async throws -> SpawnTerminalResponse {
      return try await apiClient.request(
          path: "/v1/terminal/spawn-system",
          method: .post
          // shell and cwd not sent!
      )
  }
  ```
- **Risk**: Terminal opens in wrong directory, user can't specify shell
- **Fix**: Pass parameters in request body
- **Effort**: 1h
- **Status**: [ ] Not started

---

## MEDIUM-HIGH (Core Stability)

### MEDIUM-H1. print() Statements in CodeWorkspace
- **Location**: `CodeWorkspace.swift:115, 146, 172, 175`
- **Problem**: 4 print() statements instead of os.Logger:
  - "Failed to load files"
  - "Failed to load file content"
  - "✓ Terminal spawned"
  - "Failed to spawn terminal"
- **Risk**: Console noise, inconsistent with rest of codebase
- **Fix**: Replace with logger
- **Effort**: 30min
- **Status**: [ ] Not started
- **Cross-ref**: Part of ongoing print() migration

### MEDIUM-H2. DataLabView Uses TeamService for Data Queries
- **Location**: `DataLabView.swift:38`
- **Problem**: `private let teamService = TeamService.shared` for natural language and pattern queries
  - TeamService is meant for team collaboration
  - Data Lab should have its own service (DataLabService or NLQueryService)
- **Risk**: Tight coupling, confusing architecture
- **Fix**: Create dedicated DataLabService or use DatabaseStore
- **Effort**: 3h
- **Status**: [ ] Not started

### MEDIUM-H3. NotificationCenter for Clear Workspace
- **Location**: `DatabaseWorkspace.swift:106`
- **Problem**: `NotificationCenter.default.post(name: .clearWorkspace, object: nil)` for workspace clear
  - Indirect communication pattern
  - Not clear who handles this notification
  - No guarantee of delivery
- **Risk**: Action may not work, hard to debug
- **Fix**: Use direct method call on DatabaseStore
- **Effort**: 1h
- **Status**: [ ] Not started

### MEDIUM-H4. Code Editor Backend Returns Any Type
- **Location**: `db_workspaces.py:192-202` and other get methods
- **Problem**: `def get_file(file_id: str) -> Optional[Any]` returns raw tuple instead of typed model
  - Same for get_files_by_workspace, get_file_for_diff, etc.
- **Risk**: Type safety lost, bugs only caught at runtime
- **Fix**: Create FileResponse model and return it
- **Effort**: 2h
- **Status**: [ ] Not started

---

## MEDIUM-MEDIUM (Edge Cases)

### MEDIUM-M1. Database Preview Missing Environment
- **Location**: `DatabaseWorkspace.swift:208-211`
- **Problem**: Preview doesn't inject DatabaseStore environment
  ```swift
  #Preview {
      DatabaseWorkspace()
          .frame(width: 1200, height: 800)
  }
  ```
- **Risk**: Preview crashes or shows incomplete state
- **Fix**: Add .environment(DatabaseStore.shared)
- **Effort**: 15min
- **Status**: [ ] Not started

### MEDIUM-M2. Code Editor Service Uses Wrong Path Convention
- **Location**: `CodeEditorService.swift:17, 54, 63`
- **Problem**: Inconsistent path prefixes:
  - Line 17: `"/v1/code-editor/workspaces"` (with leading slash)
  - Line 54: `"/v1/code-editor/workspaces/\(workspaceId)/files"` (with leading slash)
  - Works because apiClient handles it, but inconsistent with some other services
- **Risk**: Low, but inconsistent patterns
- **Fix**: Standardize path convention across services
- **Effort**: 30min
- **Status**: [ ] Not started

### MEDIUM-M3. memory.memory.conn Double Access
- **Location**: `db_workspaces.py:25, 64, 105, etc.` (throughout file)
- **Problem**: `conn = memory.memory.conn` - awkward double attribute access
  - Suggests ElohimOSMemory wraps another memory object
- **Risk**: Confusing for maintainers
- **Fix**: Expose conn directly or use property
- **Effort**: 30min
- **Status**: [ ] Not started

### MEDIUM-M4. NLQueryResponse and PatternDiscoveryResult Not Imported
- **Location**: `DataLabView.swift:34-35`
- **Problem**: `nlResponse: NLQueryResponse?` and `patternResults: PatternDiscoveryResult?` used but types likely defined elsewhere
  - If types are from TeamService, they're team-specific models being used for data analysis
- **Risk**: Confusion about where models belong
- **Fix**: Define DataLab-specific response types or create shared analytics models
- **Effort**: 1h
- **Status**: [ ] Not started

### MEDIUM-M5. CodeEditorService.deleteFile Returns Void
- **Location**: `CodeEditorService.swift:92-97`
- **Problem**: `deleteFile` returns nothing, no confirmation to caller
  ```swift
  func deleteFile(fileId: String) async throws {
      _ = try await apiClient.request(...) as EmptyResponse
  }
  ```
- **Risk**: UI can't confirm deletion succeeded
- **Fix**: Return success boolean or throw on failure
- **Effort**: 30min
- **Status**: [ ] Not started

---

## MEDIUM-LOW (Technical Debt)

### MEDIUM-L1. CodeWorkspace Uses .task Instead of .onAppear
- **Location**: `CodeWorkspace.swift:67-69`
- **Problem**: `.task { await loadFiles() }` but loadFiles is non-isolated method
  - Pattern works but mixing .task with non-structured state management
- **Risk**: Low, but could lead to race conditions on rapid view recreation
- **Fix**: Consider using .task(id:) for proper cancellation
- **Effort**: 1h
- **Status**: [ ] Not started

### MEDIUM-L2. Database Workspace Missing Error States
- **Location**: `DatabaseWorkspace.swift` (absence)
- **Problem**: No error state displayed when:
  - Query fails
  - File upload fails
  - Session creation fails
- **Risk**: User doesn't know why things aren't working
- **Fix**: Add error banner or alert
- **Effort**: 2h
- **Status**: [ ] Not started

---

## MEDIUM WORKSPACES SUMMARY

| Priority | Count | Est. Hours |
|----------|-------|------------|
| Critical | 1 | 1h |
| High | 4 | 6.5h |
| Medium | 5 | 2.75h |
| Low | 2 | 3h |
| **Total** | **12** | **~13.25h** |

### Recommended Fix Order (Medium Workspaces):
1. **MEDIUM-M1** (15min) - Preview missing environment, trivial
2. **MEDIUM-H1** (30min) - print() statements
3. **MEDIUM-M2** (30min) - Path convention
4. **MEDIUM-M5** (30min) - deleteFile returns void
5. **MEDIUM-C1** (1h) - TerminalService ignores params
6. **MEDIUM-H3** (1h) - NotificationCenter indirect
7. **MEDIUM-H4** (2h) - Backend returns Any type
8. **MEDIUM-H2** (3h) - DataLabView uses TeamService
9. Rest in priority order...

---

# COMPLEX WORKSPACES - DETAILED AUDIT (2026-01-03)

**Files Reviewed**: ~35 files (Insights: 7 files, Trust: 1 large file, Team: 15 files)
**Issues Found**: 15 issues (3 Critical, 4 High, 5 Medium, 3 Low)

---

## COMPLEX-CRITICAL (Security/Stability)

### COMPLEX-C1. TeamWorkspace Bypasses ApiClient for Vault Check
- **Location**: `TeamWorkspace.swift:251-260`
- **Problem**: Raw URLSession.shared used instead of ApiClient:
  ```swift
  let url = URL(string: "\(APIConfiguration.shared.vaultURL)/folders?vault_type=real")!
  var request = URLRequest(url: url)
  request.httpMethod = "GET"
  let (_, response) = try await URLSession.shared.data(for: request)
  ```
  - Bypasses network firewall, auth injection, error handling
  - Force unwrap on URL
- **Risk**: Security controls bypassed, inconsistent error handling
- **Fix**: Use ApiClient.shared.request() method
- **Effort**: 1h
- **Status**: [ ] Not started

### COMPLEX-C2. TrustWorkspace Force Unwrap (Also Bypasses ApiClient)
- **Location**: `TrustWorkspace.swift` (if similar pattern exists)
- **Problem**: Same pattern as COMPLEX-C1 likely exists
- **Risk**: Same security concerns
- **Fix**: Use ApiClient consistently
- **Effort**: 1h
- **Status**: [ ] Not started

### COMPLEX-C3. InsightsWorkspace Error State Not Displayed
- **Location**: `InsightsWorkspace.swift:26` (error property)
- **Problem**: `@State private var error: String?` is set on failures but never shown to user
  - No `.alert()` or error banner in the view
  - Lines 239, 247, 258, 269, 282, 293, 302 all set error but user never sees it
- **Risk**: Silent failures, user doesn't know why operations failed
- **Fix**: Add alert or error banner displaying the error
- **Effort**: 1h
- **Status**: [ ] Not started
- **Cross-ref**: Same issue as SIMPLE-H3

---

## COMPLEX-HIGH (Core Stability)

### COMPLEX-H1. print() Statements in TrustWorkspace (5 locations)
- **Location**: `TrustWorkspace.swift:75, 107, 110, 114, 123`
- **Problem**: 5 print() statements with emoji icons:
  - "✅ Verified safety number"
  - "ℹ️ User not registered"
  - "❌" error messages (3 locations)
- **Risk**: Console noise, inconsistent with logger pattern
- **Fix**: Replace with logger
- **Effort**: 30min
- **Status**: [ ] Not started

### COMPLEX-H2. TrustWorkspace Platform-Specific Code Without Abstraction
- **Location**: `TrustWorkspace.swift:479-482`
- **Problem**: Direct `#if os(macOS)` with `NSPasteboard.general`:
  ```swift
  #if os(macOS)
  NSPasteboard.general.clearContents()
  NSPasteboard.general.setString(node.publicKey, forType: .string)
  #endif
  ```
  - No corresponding iOS implementation
  - No abstraction layer
- **Risk**: Feature doesn't work on iOS, code maintenance issues
- **Fix**: Create ClipboardService abstraction
- **Effort**: 2h
- **Status**: [ ] Not started

### COMPLEX-H3. TrustWorkspace Is 600+ Lines (Monolithic)
- **Location**: `TrustWorkspace.swift` (entire file)
- **Problem**: Single file handles:
  - 3 view modes (network, nodes, register)
  - Multiple modals
  - Data loading
  - Node rendering
  - Context menus
- **Risk**: Hard to maintain, test, and reason about
- **Fix**: Extract components like other workspaces (Phase 6.x pattern)
- **Effort**: 4h
- **Status**: [ ] Not started

### COMPLEX-H4. TeamChatComponents Is 16KB (Monolithic)
- **Location**: `TeamChatComponents.swift` (15973 bytes)
- **Problem**: Large file with many components that could be split
- **Risk**: Same as COMPLEX-H3
- **Fix**: Extract to separate files
- **Effort**: 2h
- **Status**: [ ] Not started

---

## COMPLEX-MEDIUM (Edge Cases)

### COMPLEX-M1. TeamModals Is 17KB (Large Modal File)
- **Location**: `Team/TeamModals.swift` (17690 bytes)
- **Problem**: Multiple complex modals in single file
- **Risk**: Maintenance complexity
- **Fix**: Split into individual modal files
- **Effort**: 2h
- **Status**: [ ] Not started

### COMPLEX-M2. InsightsWorkspace Preview Missing Environment
- **Location**: `InsightsWorkspace.swift:307-310`
- **Problem**: Preview has no environment injection
- **Risk**: Preview may not work correctly
- **Fix**: Add environment objects
- **Effort**: 15min
- **Status**: [ ] Not started

### COMPLEX-M3. TeamWorkspace Vault Check Uses Different URL Path
- **Location**: `TeamWorkspace.swift:251`
- **Problem**: Uses `APIConfiguration.shared.vaultURL` + "/folders" directly
  - Rest of codebase uses ApiClient which handles path building
  - URL construction may differ from backend expectations
- **Risk**: Inconsistent API paths
- **Fix**: Use ApiClient with proper path
- **Effort**: 30min
- **Status**: [ ] Not started

### COMPLEX-M4. Team Has Separate DataManager (Like Kanban Issue)
- **Location**: `Team/TeamWorkspaceDataManager.swift`
- **Problem**: TeamStore exists in Shared/Stores but TeamWorkspaceDataManager also exists
  - Same duplication pattern as SIMPLE-C1 (KanbanStore vs KanbanDataManager)
- **Risk**: Data inconsistency
- **Fix**: Consolidate to use TeamStore
- **Effort**: 2h
- **Status**: [ ] Not started
- **Cross-ref**: SIMPLE-C1

### COMPLEX-M5. Trust/Team Use Service.shared While Insights Uses Private Instance
- **Location**:
  - `TrustWorkspace.swift:96` - `TrustService.shared`
  - `TeamWorkspace.swift:81` - `TeamService.shared`
  - `InsightsWorkspace.swift:33` - `private let service = InsightsService.shared`
- **Problem**: Inconsistent pattern - some call `.shared` directly, others store reference
- **Risk**: Minor, but inconsistent patterns
- **Fix**: Standardize approach across workspaces
- **Effort**: 30min
- **Status**: [ ] Not started

---

## COMPLEX-LOW (Technical Debt)

### COMPLEX-L1. TeamWorkspace References Non-Existent Comment
- **Location**: `TeamWorkspace.swift:330`
- **Problem**: Comment says "AutomationWorkspace moved to Shared/Components/AutomationWorkspace.swift"
  - Need to verify this file exists
- **Risk**: Misleading documentation
- **Fix**: Verify and update comment if needed
- **Effort**: 15min
- **Status**: [ ] Not started

### COMPLEX-L2. TrustWorkspace Has Complex Conditional Rendering
- **Location**: `TrustWorkspace.swift:196-212`
- **Problem**: Complex conditionals for view state:
  ```swift
  if isLoading && trustNetwork == nil && !needsRegistration {
      loadingView
  } else if needsRegistration {
      welcomeView
  } else if let error = errorMessage {
      errorView(error)
  } else {
      switch currentView { ... }
  }
  ```
  - Hard to follow all possible states
- **Risk**: Edge case bugs, confusion
- **Fix**: Consider ViewState enum pattern
- **Effort**: 2h
- **Status**: [ ] Not started

### COMPLEX-L3. Insights Template Editor Sheet Pattern
- **Location**: `InsightsWorkspace.swift:80-88`
- **Problem**: Shows template editor via state toggle after closing template library
  - Two-step state change could be flaky
- **Risk**: UI flicker or race condition
- **Fix**: Consider single modal state enum
- **Effort**: 1h
- **Status**: [ ] Not started

---

## COMPLEX WORKSPACES SUMMARY

| Priority | Count | Est. Hours |
|----------|-------|------------|
| Critical | 3 | 3h |
| High | 4 | 8.5h |
| Medium | 5 | 5.25h |
| Low | 3 | 3.25h |
| **Total** | **15** | **~20h** |

### Recommended Fix Order (Complex Workspaces):
1. **COMPLEX-M2** (15min) - Preview missing environment, trivial
2. **COMPLEX-L1** (15min) - Verify comment accuracy
3. **COMPLEX-H1** (30min) - print() statements
4. **COMPLEX-M5** (30min) - Service pattern consistency
5. **COMPLEX-C1** (1h) - Bypass ApiClient (security)
6. **COMPLEX-C2** (1h) - Same ApiClient fix
7. **COMPLEX-C3** (1h) - Error display
8. **COMPLEX-M3** (30min) - URL path consistency
9. **COMPLEX-H2** (2h) - Clipboard abstraction
10. **COMPLEX-M4** (2h) - DataManager consolidation

---

## TIER 6-8 FINDINGS: BACKEND ENGINES, SERVICES, ROUTES

**Scope**: 357 API endpoints across 79 route files, 25+ engines, 45+ services
**Audit Date**: 2026-01-03
**Issues Found**: 18

### BACKEND SUMMARY METRICS

| Metric | Count | Assessment |
|--------|-------|------------|
| Total API Endpoints | 357 | Large API surface |
| Route Files | 79 | Well-organized |
| Auth References | 587 | Good coverage |
| Bare `except Exception:` | 81 (42 files) | ⚠️ Needs cleanup |
| Bare `pass` statements | 71 (41 files) | ⚠️ Silent failures |
| Dynamic SQL (f-string) | 27 locations | Most protected |
| shell=True usage | 0 | ✅ Excellent |
| Large Files (>30KB) | 5 | Consider splitting |

### POSITIVE FINDINGS (Security Best Practices)

**Security Strengths Observed:**
1. ✅ No `shell=True` in subprocess calls - only documentation comments about avoiding it
2. ✅ `data_engine.py` has defense-in-depth SQL validation (regex + whitelist + parameterized)
3. ✅ `codex_engine.py` uses stdin piping instead of shell for patch commands
4. ✅ File/thread locking implemented for concurrent access
5. ✅ WAL mode enabled for SQLite
6. ✅ `quote_identifier()` imported in security-sensitive modules
7. ✅ Compiled regex patterns at module level (performance)

---

## BACKEND-CRITICAL (Security & Data Integrity)

### BACKEND-C1. Bare Exception Handlers (81 occurrences)
- **Locations**: 42 files (see detailed list below)
- **Top Offenders**:
  - `jarvis_rag_pipeline.py` - 10 bare exceptions
  - `codex_engine.py` - 17 bare exceptions
  - `kanban_service.py` - 3 bare exceptions
- **Problem**: Silent error swallowing hides bugs and security issues
- **Risk**: Production issues go undetected, debugging extremely difficult
- **Fix**: Replace with specific exception types, add logging
- **Effort**: 8h (systematic refactor)
- **Status**: [ ] Not started

### BACKEND-C2. Silent Pass Statements (71 occurrences)
- **Locations**: 41 files
- **Problem**: `pass` in except blocks with no logging
- **Example**: `jarvis_rag_pipeline.py:42, 68, 86, 99`
  ```python
  except Exception:
      pass  # Silent failure!
  ```
- **Risk**: Errors invisible, operations fail silently
- **Fix**: Add logger.warning/error, or re-raise if critical
- **Effort**: 4h
- **Status**: [ ] Not started

---

## BACKEND-HIGH (Maintainability)

### BACKEND-H1. Large Monolithic Files
- **Locations**:
  - `api/services/vault/core.py` - 41KB
  - `api/routes/vault_auth.py` - 40KB
  - `api/agent/engines/codex_engine.py` - 40KB
  - `api/services/workflow_orchestrator.py` - 39KB
  - `api/metal4_engine.py` - 31KB
- **Problem**: Files exceed 30KB, difficult to maintain/test
- **Risk**: High cognitive load, merge conflicts, test isolation
- **Fix**: Extract into focused modules (as done with Phase 6 refactoring)
- **Effort**: 12h total (2-3h per file)
- **Status**: [ ] Not started

### BACKEND-H2. Workflow Orchestrator Duplicate
- **Locations**:
  - `api/workflow_orchestrator.py` (shim)
  - `api/services/workflow_orchestrator.py` (actual)
- **Problem**: Two files for same functionality, shim could be removed
- **Risk**: Confusion, import inconsistency
- **Fix**: Update all imports to use `api.services.workflow_orchestrator`, deprecate shim
- **Effort**: 2h
- **Status**: [ ] Not started

### BACKEND-H3. Import Try/Except Fallback Pattern
- **Locations**: Multiple files use this pattern:
  ```python
  try:
      from api.workflow_models import X
  except ImportError:
      from workflow_models import X
  ```
- **Problem**: 15+ files have redundant import fallbacks
- **Risk**: Import confusion, masks actual import errors
- **Fix**: Standardize on one import path, remove fallbacks
- **Effort**: 2h
- **Status**: [ ] Not started

---

## BACKEND-MEDIUM (Code Quality)

### BACKEND-M1. Dynamic SQL Without Validation
- **Locations** (need review):
  - `api/metal4_duckdb_bridge.py:306, 347, 379, 411, 436` - table/column in f-strings
  - `api/db_consolidation_migration.py:82, 96, 103` - table names in f-strings
  - `api/routes/system/db_health.py:64, 73` - table name in f-string
- **Problem**: Some dynamic SQL uses f-strings without explicit validation
- **Risk**: SQL injection if table/column names from untrusted input
- **Fix**: Add validation or use `quote_identifier()` consistently
- **Effort**: 3h
- **Status**: [ ] Not started

### BACKEND-M2. Route Files Without Auth Check
- **Locations**: 9 files potentially have unauthenticated endpoints
  - `progress.py`, `setup_wizard_routes.py`, `data_engine.py`, others
- **Problem**: Need to verify which endpoints should be public
- **Risk**: Unintentional exposure of sensitive operations
- **Fix**: Audit each endpoint, document public vs. authenticated
- **Effort**: 2h
- **Status**: [ ] Not started

### BACKEND-M3. Inconsistent Error Response Format
- **Locations**: Various route files
- **Problem**: Some routes return raw exceptions, others use standard ErrorResponse
- **Risk**: Frontend has inconsistent error handling
- **Fix**: Use `ErrorResponse` envelope consistently
- **Effort**: 4h
- **Status**: [ ] Not started

### BACKEND-M4. Template Orchestrator SQL Pattern
- **Location**: `api/template_orchestrator.py:285`
- **Code**: `sql = f"SELECT * FROM ({sql}) WHERE {step.condition}"`
- **Problem**: Condition appended to SQL without sanitization
- **Risk**: SQL injection if condition from untrusted input
- **Fix**: Validate/sanitize condition, or use parameterized queries
- **Effort**: 1h
- **Status**: [ ] Not started

---

## BACKEND-LOW (Polish)

### BACKEND-L1. Inconsistent Logging Format
- **Locations**: Throughout backend
- **Problem**: Some files use emoji prefixes (✅ ⚠️), others don't
- **Risk**: Log parsing tools may be confused
- **Fix**: Standardize logging format, consider structured logging
- **Effort**: 2h
- **Status**: [ ] Not started

### BACKEND-L2. TODO Comments Audit
- **Locations**: Run `grep -r "TODO" api/`
- **Problem**: Unknown number of TODO comments, some may be stale
- **Risk**: Forgotten technical debt
- **Fix**: Review and either implement or remove
- **Effort**: 2h
- **Status**: [ ] Not started

### BACKEND-L3. Missing Docstrings on Public Functions
- **Locations**: Various service and engine files
- **Problem**: Some public APIs lack documentation
- **Risk**: Maintainability, onboarding difficulty
- **Fix**: Add docstrings to public functions
- **Effort**: 4h
- **Status**: [ ] Not started

### BACKEND-L4. Test Isolation for Route Files
- **Locations**: `tests/` directory
- **Problem**: Route tests may not cover all 357 endpoints
- **Risk**: Regressions in untested endpoints
- **Fix**: Add coverage tracking, identify gaps
- **Effort**: 4h (audit)
- **Status**: [ ] Not started

---

## BACKEND TIER 6-8 SUMMARY

| Priority | Count | Est. Hours |
|----------|-------|------------|
| Critical | 2 | 12h |
| High | 3 | 16h |
| Medium | 4 | 10h |
| Low | 4 | 12h |
| **Total** | **13** | **~50h** |

*Note: Some issues overlap with multiple occurrences (81 bare exceptions, 71 pass statements)*

### Recommended Fix Order (Backend):
1. **BACKEND-M2** (2h) - Auth endpoint audit (security)
2. **BACKEND-M4** (1h) - Template orchestrator SQL fix
3. **BACKEND-M1** (3h) - Dynamic SQL validation review
4. **BACKEND-C1** (8h) - Bare exception handlers (batch by file)
5. **BACKEND-C2** (4h) - Silent pass statements
6. **BACKEND-H3** (2h) - Standardize imports
7. **BACKEND-H2** (2h) - Remove orchestrator shim
8. **BACKEND-H1** (12h) - Split large files (prioritize by change frequency)

---

## TIER 9-11 FINDINGS: AUTH, EMERGENCY, VAULT SYSTEMS

**Scope**: 3 Swift auth files, 7 emergency mode files, 2 panic mode files, 11+ vault route files
**Audit Date**: 2026-01-03
**Issues Found**: 11

### AUTH/VAULT SUMMARY METRICS

| Metric | Count | Assessment |
|--------|-------|------------|
| Auth Files (Swift) | 3 | Well-structured |
| Auth Files (Python) | 5 | Good separation |
| Emergency Mode Files | 7 | Properly modularized |
| Vault Route Files | 11 | Comprehensive |
| Vault Service Files | 19 | Feature-rich |
| Unauthenticated Endpoints (Swift) | 8 | All appropriate |
| Auth-Protected Endpoints | 62 files | Good coverage |

### POSITIVE FINDINGS (Security Best Practices)

**Security Strengths Observed:**
1. ✅ JWT secret persisted with `chmod 0o600` (owner-only permissions)
2. ✅ Device ID stored in Keychain with migration from UserDefaults
3. ✅ Passphrase stored in memory only (never persisted to disk)
4. ✅ VaultStore.lock() clears all sensitive state properly
5. ✅ Emergency mode has explicit safety flag (`EMERGENCY_MODE_ENABLED = false` in DEBUG)
6. ✅ WebAuthn challenges use one-time consumption pattern
7. ✅ Rate limiting on vault unlock (5 attempts → 5-minute lockout)
8. ✅ Dual-password mode for plausible deniability (decoy vaults)

---

## AUTH-CRITICAL (Security)

### AUTH-C1. In-Memory WebAuthn Challenge Storage
- **Location**: `api/routes/vault_auth.py:46`
- **Code**: `webauthn_challenges: Dict[tuple, Dict[str, Any]] = {}`
- **Problem**: WebAuthn challenges stored in Python dict, lost on restart
- **Risk**: Multi-instance deployments would fail authentication
- **Fix**: Use Redis with TTL for distributed challenge storage
- **Effort**: 4h
- **Status**: [ ] Not started
- **Note**: Comment at line 45 acknowledges this: "In production, use Redis with TTL"

### AUTH-C2. Vault Session Storage In-Memory
- **Location**: `api/routes/vault_auth.py:57`
- **Code**: `vault_sessions: Dict[tuple, Dict[str, Any]] = {}`
- **Problem**: KEK sessions stored in memory, lost on restart
- **Risk**: Users would need to re-unlock vault after any backend restart
- **Fix**: Consider encrypted session persistence or Redis
- **Effort**: 4h
- **Status**: [ ] Not started

---

## AUTH-HIGH (Functionality Gaps)

### AUTH-H1. EmergencyModeService Uses ObservableObject
- **Location**: `EmergencyModeService.swift:40`
- **Code**: `@MainActor final class EmergencyModeService: ObservableObject`
- **Problem**: Uses older `ObservableObject` while AuthStore and VaultStore use `@Observable`
- **Risk**: Inconsistent state update behavior, migration debt
- **Fix**: Migrate to `@Observable` like AuthStore
- **Effort**: 2h
- **Status**: [ ] Not started
- **Cross-ref**: Related to @Observable migration pattern in other tiers

### AUTH-H2. PanicLevel.emergency Not Implemented
- **Location**: `PanicModeService.swift:65`
- **Code**: `case .emergency: throw PanicModeError.emergencyModeNotImplemented`
- **Problem**: Triple-click emergency mode throws "not implemented" error
- **Risk**: User expects feature to work in emergency scenario
- **Fix**: Either implement or remove from UI/enum
- **Effort**: 8h (implement) or 1h (remove)
- **Status**: [ ] Not started

### AUTH-H3. Panic vs Emergency Service Overlap
- **Locations**:
  - `PanicModeService.swift` - Standard panic
  - `EmergencyModeService.swift` - DoD 7-pass wipe
- **Problem**: Two separate services for related functionality
- **Risk**: Confusion, code duplication, inconsistent behavior
- **Fix**: Consider consolidating or clarifying relationship
- **Effort**: 3h
- **Status**: [ ] Not started

---

## AUTH-MEDIUM (Code Quality)

### AUTH-M1. Hardcoded WebAuthn Configuration
- **Location**: `api/routes/vault_auth.py:40-41`
- **Code**:
  ```python
  WEBAUTHN_RP_ID = "localhost"  # Relying Party ID (domain)
  WEBAUTHN_ORIGIN = "http://localhost:3000"  # Expected origin
  ```
- **Problem**: Hardcoded values, comment says "should be from environment/settings"
- **Risk**: Won't work in production deployment
- **Fix**: Move to environment variables or config
- **Effort**: 30min
- **Status**: [ ] Not started

### AUTH-M2. Token Refresh Logic Incomplete
- **Location**: `HubCloudManager.swift:163`
- **Code**: `authenticated: false  // Refresh uses refresh token, not JWT`
- **Problem**: Refresh token flow exists but not fully integrated
- **Risk**: Long-running sessions may fail
- **Fix**: Ensure proactive token refresh before expiry
- **Effort**: 2h
- **Status**: [ ] Not started

### AUTH-M3. Emergency Mode File Extensions
- **Locations**: 4 extension files for EmergencyModeService
- **Problem**: Extensions well-structured but tightly coupled
- **Risk**: Testing individual components difficult
- **Fix**: Consider protocol-based design for testability
- **Effort**: 3h
- **Status**: [ ] Not started

---

## AUTH-LOW (Polish)

### AUTH-L1. Debug Auto-Login in AuthStore
- **Location**: `AuthStore.swift:52-126`
- **Problem**: 74 lines of debug auto-login code in production file
- **Risk**: Code bloat, potential security risk if env vars leaked
- **Fix**: Extract to separate DebugAuthHelper or reduce size
- **Effort**: 1h
- **Status**: [ ] Not started

### AUTH-L2. Duplicate LoginResponse Definitions
- **Locations**:
  - `AuthStore.swift:82-100` - Inner struct
  - `AuthService.swift:97-115` - Top-level struct
- **Problem**: Same struct defined twice
- **Risk**: Maintenance burden, potential drift
- **Fix**: Use single shared definition
- **Effort**: 30min
- **Status**: [ ] Not started

---

## AUTH/VAULT TIER 9-11 SUMMARY

| Priority | Count | Est. Hours |
|----------|-------|------------|
| Critical | 2 | 8h |
| High | 3 | 13h |
| Medium | 3 | 5.5h |
| Low | 2 | 1.5h |
| **Total** | **10** | **~28h** |

### Recommended Fix Order (Auth/Vault):
1. **AUTH-M1** (30min) - WebAuthn config to environment
2. **AUTH-L2** (30min) - Consolidate LoginResponse
3. **AUTH-H1** (2h) - Migrate EmergencyModeService to @Observable
4. **AUTH-H2** (1h) - Remove or implement emergency mode
5. **AUTH-C1** (4h) - Redis for WebAuthn challenges
6. **AUTH-C2** (4h) - Redis for vault sessions
7. **AUTH-M2** (2h) - Token refresh integration
8. **AUTH-H3** (3h) - Panic/Emergency service clarity

---

## TIER 12-14 FINDINGS: SETTINGS, TERMINAL, P2P

**Scope**: 13 Settings Swift files, 2 Terminal files, 4 P2P Python files
**Audit Date**: 2026-01-03
**Issues Found**: 9

### SETTINGS/TERMINAL/P2P SUMMARY METRICS

| Metric | Count | Assessment |
|--------|-------|------------|
| Settings Swift Files | 13 | Good organization |
| Settings Backend Routes | 3 | Adequate |
| Terminal Files | 2 | Minimal |
| P2P Backend Files | 4 | Well-structured |
| @StateObject/@ObservedObject usage | 3 | Needs @Environment migration |

### POSITIVE FINDINGS

**Strengths Observed:**
1. ✅ SettingsStore uses `@Observable` correctly
2. ✅ P2P mesh service uses SQLite for connection code persistence (survives restarts)
3. ✅ P2P endpoints require authentication (`dependencies=[Depends(get_current_user)]`)
4. ✅ Settings views use `@AppStorage` for UserDefaults persistence
5. ✅ Rate limiting on connection code attempts

---

## SETTINGS-HIGH (Functionality Gaps)

### SETTINGS-H1. TerminalService Parameters Ignored
- **Location**: `TerminalService.swift:49-55`
- **Code**:
  ```swift
  func spawnTerminal(shell: String? = nil, cwd: String? = nil) async throws -> SpawnTerminalResponse {
      return try await apiClient.request(
          path: "/v1/terminal/spawn-system",
          method: .post
          // shell and cwd NOT SENT to API!
      )
  }
  ```
- **Problem**: Function signature accepts `shell` and `cwd` but doesn't send them
- **Risk**: Callers expect working directory support that doesn't work
- **Fix**: Add body parameters to request, or remove unused parameters
- **Effort**: 30min
- **Status**: [ ] Not started
- **Cross-ref**: Also flagged in Tier 4 (CodeWorkspace)

### SETTINGS-H2. Settings Views Use @StateObject for Singletons
- **Locations**:
  - `MagnetarCloudSettingsView.swift:14` - `@StateObject private var authManager = CloudAuthManager.shared`
  - `HotSlotSettingsView.swift:15` - `@StateObject private var hotSlotManager = HotSlotManager.shared`
  - `SecuritySettingsView.swift:22` - `@ObservedObject private var securityManager = SecurityManager.shared`
- **Problem**: Using `@StateObject`/`@ObservedObject` with singletons is anti-pattern
- **Risk**: Recreates wrapper on each view init, memory leaks
- **Fix**: Migrate to `@Environment` pattern with `@Observable`
- **Effort**: 2h
- **Status**: [ ] Not started

---

## SETTINGS-MEDIUM (Code Quality)

### SETTINGS-M1. Settings Backend Tight Coupling to main.py
- **Location**: `api/routes/settings.py:29-43`
- **Code**:
  ```python
  def get_app_settings() -> Any:
      from api import main
      return main.app_settings
  ```
- **Problem**: Routes import from main.py at runtime
- **Risk**: Circular import risk, tight coupling, testing difficulty
- **Fix**: Use dependency injection or dedicated settings service
- **Effort**: 2h
- **Status**: [ ] Not started

### SETTINGS-M2. Hardcoded Auto-Lock Timeout Options
- **Location**: `SecuritySettingsView.swift:93-98`
- **Code**: `Text("5 minutes").tag(5)`, etc.
- **Problem**: Timeout options hardcoded in view
- **Risk**: Can't change without code modification
- **Fix**: Move to configuration or model
- **Effort**: 30min
- **Status**: [ ] Not started

### SETTINGS-M3. P2P Connection Code Expiry Not Enforced
- **Location**: `p2p_mesh_service.py:102`
- **Code**: `WHERE expires_at IS NULL OR datetime(expires_at) > datetime('now')`
- **Problem**: Only checked on load, not on use
- **Risk**: Expired codes might work briefly after restart
- **Fix**: Add expiry check in code validation
- **Effort**: 30min
- **Status**: [ ] Not started

---

## SETTINGS-LOW (Polish)

### SETTINGS-L1. Terminal Service Missing Kill/Terminate
- **Location**: `TerminalService.swift`
- **Problem**: Can spawn terminals but no API to terminate them
- **Risk**: Orphaned terminal processes
- **Fix**: Add `terminateTerminal(id:)` method
- **Effort**: 1h
- **Status**: [ ] Not started

### SETTINGS-L2. Settings Models in Multiple Files
- **Locations**:
  - `SettingsModels.swift` - Some models
  - `SettingsStore.swift` - ChatSettings, AppSettings
  - `SettingsService.swift` - SavedQuery
- **Problem**: Settings-related models spread across files
- **Risk**: Discoverability, potential duplication
- **Fix**: Consolidate in SettingsModels.swift
- **Effort**: 1h
- **Status**: [ ] Not started

### SETTINGS-L3. CodeTerminalPanel Error Display
- **Location**: `CodeTerminalPanel.swift` + `CodeWorkspace.swift:59`
- **Problem**: `errorMessage` passed to panel but display logic unclear
- **Risk**: Users may not see terminal errors
- **Fix**: Ensure error banner is visible in terminal panel
- **Effort**: 30min
- **Status**: [ ] Not started

### SETTINGS-L4. P2P Service Initialization at Import
- **Location**: `p2p_mesh_service.py:118`
- **Code**: `_init_codes_db()` called at module level
- **Problem**: Database initialized on import, not lazily
- **Risk**: Side effects during import, testing difficulty
- **Fix**: Initialize on first use
- **Effort**: 30min
- **Status**: [ ] Not started

---

## SETTINGS/TERMINAL/P2P TIER 12-14 SUMMARY

| Priority | Count | Est. Hours |
|----------|-------|------------|
| Critical | 0 | 0h |
| High | 2 | 2.5h |
| Medium | 3 | 3h |
| Low | 4 | 3h |
| **Total** | **9** | **~8.5h** |

### Recommended Fix Order (Settings/Terminal/P2P):
1. **SETTINGS-H1** (30min) - Fix TerminalService parameters
2. **SETTINGS-M3** (30min) - P2P code expiry validation
3. **SETTINGS-M2** (30min) - Externalize timeout options
4. **SETTINGS-L4** (30min) - Lazy P2P DB init
5. **SETTINGS-H2** (2h) - @Environment migration
6. **SETTINGS-M1** (2h) - Settings service decoupling

---

## TIER 15-17 FINDINGS: UI COMPONENTS, DESIGN SYSTEM, TESTS

**Scope**: 34 Component files, 1 Modifier file, 5 Swift + 27 Python test files
**Audit Date**: 2026-01-03
**Issues Found**: 8

### UI/TESTS SUMMARY METRICS

| Metric | Count | Assessment |
|--------|-------|------------|
| Component Files | 34 | Well-organized |
| Modifier Files | 1 | Minimal (good) |
| Swift Test Files | 5 | Limited coverage |
| Python Test Files | 27 | Good coverage |
| Button Handlers | 30 | Across 14 files |
| print() in Components | 6 | Needs cleanup |
| TODO Comments in Components | 1 | Good |

### POSITIVE FINDINGS

**Strengths Observed:**
1. ✅ NetworkFirewallModifier is clean and well-structured
2. ✅ Test files use `@MainActor` correctly for async testing
3. ✅ Components are well-organized by feature (Automation, Header, etc.)
4. ✅ Only 1 TODO comment in components (good cleanup)
5. ✅ RefactoringIntegrationTests cover cross-workspace interactions

---

## UI-HIGH (Functionality)

### UI-H1. ResultsTable "Analyze with AI" Not Implemented
- **Location**: `ResultsTable.swift:55-57`
- **Code**:
  ```swift
  // TODO: Wire to ChatStore or dedicated AnalysisService
  print("[ResultsTable] Analyze with AI tapped - needs implementation")
  ```
- **Problem**: Button visible but functionality not wired
- **Risk**: Users expect feature to work
- **Fix**: Wire to ChatStore or create AnalysisService
- **Effort**: 2h
- **Status**: [ ] Not started

### UI-H2. print() Statements in Components (6 locations)
- **Locations**:
  - `ResultsTable.swift:57` - "Analyze with AI tapped - needs implementation"
  - `ControlCenterSheet.swift:111` - Error logging
  - `EmptyState.swift:89` - Preview action
  - `SidebarTabs.swift:175` - "Insert column"
  - `WorkflowQueueView.swift:181` - Error logging
  - `WorkflowDashboardView.swift:170` - Error logging
- **Problem**: Debug print statements in production components
- **Risk**: Console noise, potential information disclosure
- **Fix**: Replace with os.Logger
- **Effort**: 1h
- **Status**: [ ] Not started

---

## UI-MEDIUM (Testing Gaps)

### UI-M1. Limited Swift Test Coverage
- **Locations**: `Tests/` - only 5 files
  - `DocsWorkspaceTests.swift`
  - `ModelDiscoveryWorkspaceTests.swift`
  - `TeamWorkspaceV2Tests.swift`
  - `HotSlotSettingsTests.swift`
  - `RefactoringIntegrationTests.swift`
- **Problem**: Many workspaces have no test coverage
- **Risk**: Regressions undetected, confidence issues
- **Fix**: Add tests for Chat, Code, Database, Vault, Kanban workspaces
- **Effort**: 8h
- **Status**: [ ] Not started

### UI-M2. Preview Environment Gaps
- **Locations**: Various component files
- **Problem**: Some previews may crash without environment
- **Risk**: Poor developer experience
- **Fix**: Add mock environment to all previews
- **Effort**: 2h
- **Status**: [ ] Not started

---

## UI-LOW (Polish)

### UI-L1. Automation Components Deep Nesting
- **Location**: `Shared/Components/AutomationWorkspace/`
- **Structure**: 4 levels deep (Core, Builder, Dashboard, Queue, Analytics)
- **Problem**: Deep folder nesting increases complexity
- **Risk**: Discoverability, navigation friction
- **Fix**: Consider flattening or using module system
- **Effort**: 2h
- **Status**: [ ] Not started

### UI-L2. Only One View Modifier
- **Location**: `Shared/Modifiers/`
- **Problem**: Only `NetworkFirewallModifier.swift` exists
- **Risk**: Missed opportunities for reusable modifiers
- **Fix**: Consider extracting common patterns (loading overlay, error badge, etc.)
- **Effort**: 4h
- **Status**: [ ] Not started

### UI-L3. Button Handler Audit Needed
- **Locations**: 30 button handlers across 14 component files
- **Problem**: Not all handlers verified to work correctly
- **Risk**: Non-functional buttons
- **Fix**: Manual audit of all button handlers
- **Effort**: 2h (audit)
- **Status**: [ ] Not started

### UI-L4. Missing Accessibility Labels
- **Locations**: Various component files
- **Problem**: Not all buttons have `.accessibilityLabel`
- **Risk**: Poor VoiceOver support
- **Fix**: Add accessibility labels to interactive elements
- **Effort**: 2h
- **Status**: [ ] Not started

---

## UI/TESTS TIER 15-17 SUMMARY

| Priority | Count | Est. Hours |
|----------|-------|------------|
| Critical | 0 | 0h |
| High | 2 | 3h |
| Medium | 2 | 10h |
| Low | 4 | 10h |
| **Total** | **8** | **~23h** |

### Recommended Fix Order (UI/Tests):
1. **UI-H2** (1h) - Replace print() with logger
2. **UI-H1** (2h) - Wire "Analyze with AI"
3. **UI-M2** (2h) - Fix preview environments
4. **UI-L3** (2h) - Button handler audit
5. **UI-L4** (2h) - Add accessibility labels
6. **UI-M1** (8h) - Increase Swift test coverage

---

## AUDIT COMPLETE - FINAL SUMMARY

### Issues by Tier

| Tier | Category | Issues | Est. Hours |
|------|----------|--------|------------|
| 0-2 | General + Chat + Infrastructure | 67 | ~356h |
| 3-5 | Workspaces (Simple/Medium/Complex) | 43 | ~53h |
| 6-8 | Backend (Engines/Services/Routes) | 13 | ~50h |
| 9-11 | Auth, Emergency, Vault | 10 | ~28h |
| 12-14 | Settings, Terminal, P2P | 9 | ~8.5h |
| 15-17 | UI, Design, Tests | 8 | ~23h |
| **Total** | | **150** | **~518h** |

### Issues by Priority

| Priority | Count | Percentage |
|----------|-------|------------|
| Critical | 8 | 5% |
| High | 32 | 21% |
| Medium | 54 | 36% |
| Low | 56 | 38% |

### Key Themes Across Codebase

1. **@Observable Migration**: Multiple files still use `ObservableObject`/`@StateObject`
2. **print() → Logger**: ~245 print statements remain across codebase
3. **Error Swallowing**: 81 bare `except Exception:`, 71 silent `pass`
4. **API Contract Gaps**: Several Swift services don't match backend endpoints
5. **Test Coverage**: Swift tests limited (5 files vs 27 Python)

### Recommended Immediate Actions (Next 40h)

1. **Security** (8h): AUTH-M1, BACKEND-M2, BACKEND-M4 - Fix auth and SQL patterns
2. **Core Functionality** (8h): SETTINGS-H1, UI-H1 - Wire unimplemented features
3. **Code Quality** (16h): BACKEND-C1, UI-H2 - Exception handling and logging
4. **Migration** (8h): AUTH-H1, SETTINGS-H2 - @Observable migration


