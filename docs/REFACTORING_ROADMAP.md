# MagnetarStudio - Systematic Fix Plan
## Updated: 2025-12-26

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

### PHASE 6: MAJOR REFACTORINGS ✅ (Completed 2025-12-26)

All major refactorings have been completed:

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| TeamWorkspace.swift | 3,196 | 327 | 90% ✅ |
| AutomationWorkspace.swift | 2,040 | 145 | 93% ✅ |
| team/core.py | 1,785 | 723 | 59% ✅ |
| vault/core.py | 1,538 | 1,088 | 29% ✅ |

**Extracted modules:**
- Swift AutomationWorkspace: 18 modular files in organized directory structure
- Swift TeamWorkspace: 7+ TeamChat modules + Team directory modules
- Python team/: 12 modules (storage, vault, queues, workflows, roles, members, etc.)
- Python vault/: 16 modules (files, storage, sharing, automation, folders, etc.)

---

### TIER 5: SECURITY & COMPATIBILITY ✅ (Completed 2025-12-26)

**Commit:** `07767b09` - feat: Complete Tier 5 security and compatibility tasks

#### 5.1 P2P Trust Protocol Hardening ✅
- Mutual safety number verification (Signal-like fingerprints)
- Vouch chain validation with Byzantine fault tolerance
- Trust chain visualization with path verification
- SafetyNumberVerificationModal and VouchNodeModal in Swift
- TrustService with vouch/revoke/expire functionality
- 24 new trust router tests

#### 5.2 MagnetarCloud Authentication ✅
- Cloud authentication endpoints (`/api/v1/cloud/*`)
- Device pairing with cloud tokens (7-day expiry)
- Device fingerprint for token binding (SHA-256 hardware UUID)
- 30-day refresh tokens for offline renewal
- HubCloudManager.swift with Keychain storage
- Rate limiting (5 attempts/hour) on pairing
- 25 cloud auth tests

#### 5.3 Metal 4 Python 3.14+ Compatibility ✅
- Updated pyproject.toml: removed `<3.14` constraint
- Modernized type annotations (PEP 585/604) in 20+ Metal files
- Replaced deprecated `datetime.utcnow()` with `datetime.now(UTC)`
- Added `asyncio_default_fixture_loop_scope` to pytest config
- Verified Metal 4 stack on Apple M4 Max (128 GB unified memory)

---

### TIER 6: VALIDATED FROM MASTER ROADMAP ✅ (Completed)

Items from Master Roadmap (Dec 23) that were verified as complete:

| Item | Status | Notes |
|------|--------|-------|
| WebAuthn Sign Count | ✅ DONE | Counter fetched, validated, updated in DB |
| Cache Metrics Auth | ✅ DONE | Admin auth required, router registered |
| Logger force unwrap | ✅ DONE | No `error!` found in Logger.swift |
| Duplicate router registration | ✅ DONE | system_router via router_registry only |
| __all__ exports | ✅ DONE | 30+ init files have __all__ |
| Deprecation warnings | ✅ DONE | Fixed chat_service imports |
| Code workspace in NavigationRail | ✅ DONE | Lines 60-68 |
| Trash service size calculation | ✅ DONE | Lines 454-464 in trash_service.py |
| Test coverage 75%+ | ✅ DONE | 599 tests passing |
| @MainActor anti-pattern | ✅ MOSTLY | Only 1 instance remains |

---

## 🔲 REMAINING WORK (Ordered: Least → Most Complex)

---

### TIER 7: TRIVIAL FIXES (~5-15 min each)

Quick wins that can be done in a single edit.

#### 7.1 Empty Button Closures (Swift)
Wire up buttons that currently have empty `{ }` actions:

| File | Line | Button | Action Needed |
|------|------|--------|---------------|
| `ResultsTable.swift` | 70 | "Analyze with AI" | Connect to AI analysis |
| `ThreePaneLayout.swift` | 173 | Header action | Add callback |
| `TwoPaneLayout.swift` | 138 | "New Chat" | Create new chat |
| `TwoPaneLayout.swift` | 139 | "Select" | Toggle selection mode |
| `TwoPaneLayout.swift` | 141-142 | Icon buttons | Add actions |
| `HubModels.swift` | 333 | "Sync to Local" | Trigger cloud sync |

#### 7.2 Config Alignment (Python)
Fix configuration mismatches:

- [ ] `config.py:100` - JWT expiry says 43200 min (30 days)
- [ ] `auth_middleware.py:99` - Hardcoded 1 hour
- [ ] **Fix:** Align to use config value consistently

#### 7.3 Remove Hardcoded Default Password
- [ ] `auth_bootstrap.py:73` - Remove `"ElohimOS_2024_Founder"` string
- [ ] Require `ELOHIM_FOUNDER_PASSWORD` env var even in dev

#### 7.4 Remove Debug Print Statements (from Master Roadmap)
**330 occurrences in 25 files** - Replace with `logger.debug()` or remove:

| File | Count | Priority |
|------|-------|----------|
| `permission_layer.py` | 70 | HIGH |
| `migrate_workflow_user_isolation.py` | 66 | LOW (migration) |
| `agent/dev_assistant.py` | 29 | MEDIUM |
| `agent/dev_orchestrator.py` | 29 | MEDIUM |
| `learning_system.py` | 21 | MEDIUM |
| `db_consolidation_migration.py` | 21 | LOW (migration) |
| Others | 94 | LOW |

#### 7.5 Fix Last @MainActor Anti-Pattern (from Master Roadmap)
**File:** `SafetyNumberVerificationModal.swift:348`
```swift
// Current:
DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { ... }
// Fix: Use Task { try await Task.sleep(...) }
```

---

### TIER 8: EASY FIXES (~15-30 min each)

Simple implementations with clear scope.

#### 8.1 Centralize Swift Localhost URLs
Replace hardcoded URLs with `APIConfiguration`:

| File | Line | Current |
|------|------|---------|
| `ModelsStore.swift` | 29 | `http://localhost:8000/api/v1/chat/models` |
| `ModelsStore.swift` | 73 | `http://localhost:11434/api/pull` |
| `ModelsStore.swift` | 122 | `http://localhost:11434/api/delete` |
| `ChatStore.swift` | 71 | `http://localhost:8000/api/v1/chat/models` |
| `ChatStore.swift` | 546 | `http://localhost:8000/.../messages` |
| `SmartModelPicker.swift` | 150 | `http://localhost:8000/api/v1/chat/models` |
| `ModelManagerWindow.swift` | 376, 396 | Multiple endpoints |
| `SetupWizardView.swift` | 175 | `http://localhost:8000/api/v1/setup/complete` |
| `TeamWorkspace.swift` | 248 | `http://localhost:8000/api/v1/vault/folders` |
| `ModelManagementSettingsView.swift` | 260 | Model endpoints |
| `AuthStore.swift` | 206 | Health check |

**Solution:** Use `APIConfiguration.shared.baseURL` everywhere

#### 8.2 Centralize Python Localhost URLs
Replace hardcoded URLs with config:

| File | Line | Current |
|------|------|---------|
| `bash_intelligence.py` | 240 | `http://localhost:11434/api/generate` |
| `jarvis_rag_pipeline.py` | 227 | `http://127.0.0.1:11434/api/embeddings` |
| `setup_wizard.py` | 89 | `http://localhost:11434` |

**Solution:** Use `settings.ollama_base_url` from config

#### 8.3 Add CORS Development Warning
- [ ] `middleware/cors.py` - Log warning if production uses dev CORS
- [ ] Add startup check for `ELOHIM_ENV=production` with `*` origins

#### 8.4 Wire Up Audit Logging to Backend
- [ ] `SecurityManager.swift:185` - Send audit events to `/api/v1/audit/log`
- [ ] `EmergencyModeService+Backend.swift:47` - Implement remote logging

#### 8.5 Delete Duplicate Model Recommendations File (from Master Roadmap)
**Both files exist - conflict:**
- `model_recommendations.py` (dynamic, team-policy aware) ✅ KEEP
- `models_recommendations.py` (static JSON) ❌ DELETE

---

### TIER 9: MODERATE FIXES (~30-60 min each)

Requires understanding of existing systems.

#### 9.1 Implement Emergency Mode Key Monitoring
**File:** `EmergencyConfirmationModal.swift:300-330`

All these are currently stubs that only print:
- [ ] `startKeyMonitoring()` - Monitor for panic key combo
- [ ] `startHoldTimer()` - Track hold duration
- [ ] `cancelHoldTimer()` - Cancel on release
- [ ] `stopKeyMonitoring()` - Clean up listeners

**Approach:** Use `NSEvent.addLocalMonitorForEvents` for key events

#### 9.2 Add Rate Limiting to Setup Endpoints
**File:** `routes/setup_wizard_routes.py`

- [ ] Add `@limiter.limit("5/minute")` to model download endpoints
- [ ] Add `@limiter.limit("10/minute")` to configuration endpoints
- [ ] Prevent DoS via repeated setup requests

#### 9.3 Add Exponential Backoff to Connection Codes
**File:** `rate_limiter.py:174-180`

Current: 5 attempts/minute, lockout after 15 failures

- [ ] Implement backoff: 1s → 2s → 4s → 8s → 16s → lockout
- [ ] Start backoff on first failure, not after threshold

#### 9.4 Graceful Model Listing Fallback
**File:** `routes/chat/models.py:40-52`

- [ ] Cache last successful model list
- [ ] Return cached list when Ollama unreachable
- [ ] Add `cached: true` flag to response

#### 9.5 Fix LAN Discovery IP Detection
**File:** `lan_discovery.py:156`

Current: Connects to `8.8.8.8:80` to find local IP (external dependency!)

- [ ] Use `netifaces` or `socket.gethostbyname(socket.gethostname())`
- [ ] Add fallback chain: link-local → multicast → loopback

#### 9.6 Decide ModelDiscoveryWorkspace Fate (from Master Roadmap)
**Current State:** Fully implemented but not accessible (not in NavigationRail)

**Options:**
1. Add to NavigationRail (new button)
2. Merge into MagnetarHub (already has model catalog)
3. Remove (if superseded by Hub)

---

### TIER 10: COMPLEX FIXES (~1-2 hours each)

Requires careful implementation and testing.

#### 10.1 Fix SQL Injection Vulnerabilities
**CRITICAL SECURITY**

| File | Line | Issue |
|------|------|-------|
| `elohimos_memory.py` | 19 | Direct f-string interpolation |
| `offline_data_sync.py` | 463-486 | Table/column names in SQL |
| `permissions/engine.py` | 255-325 | Dynamic query construction |
| `insights/routes/templates.py` | 151 | UPDATE with dynamic columns |

**Solution:**
- [ ] Create `quote_identifier()` utility for table/column names
- [ ] Validate all identifiers against allowlist before interpolation
- [ ] Use parameterized queries for all values

#### 10.2 Replace MockOrchestrator with Real Implementation
**File:** `OrchestratorInitializer.swift:24-25`

```swift
// CURRENT (broken):
let mock = MockOrchestrator()
manager.register(mock)
```

- [ ] Implement `RealOrchestrator` class
- [ ] Connect to backend `/api/v1/orchestrator/*` endpoints
- [ ] Handle offline fallback to local routing

#### 10.3 Offline Password Breach Check
**File:** `password_breach_checker.py`

Current: Requires HTTPS to HaveIBeenPwned API

- [ ] Add `ELOHIM_OFFLINE_MODE` env var check
- [ ] If offline, skip breach check with warning
- [ ] Cache breach results indefinitely (not 24h)
- [ ] Allow registration when air-gapped

#### 10.4 Persist Sync Operation Queue
**File:** `offline_data_sync.py:75`

Current: `pending_operations` is in-memory only

- [ ] Create `sync_queue` SQLite table
- [ ] Persist operations before attempting sync
- [ ] Mark as completed only after successful exchange
- [ ] Retry failed operations on restart

#### 10.5 N8N Workflow Offline Fallback
**File:** `n8n_integration.py:70-82`

Current: Raises exception on network failure

- [ ] Cache last known workflow list
- [ ] Return cached list with `stale: true` flag
- [ ] Queue workflow executions when offline

---

### TIER 11: MEDIUM TASKS (from Master Roadmap)

#### 11.1 Refactor Deprecated Facades
Both log deprecation warnings on load:

| File | Status | Action |
|------|--------|--------|
| `vault_service.py` | DEPRECATED | Migrate callers to `api.services.vault` |
| `team_service.py` | DEPRECATED | Migrate callers to `api.services.team` |

#### 11.2 Complete LAN Discovery Connection Logic (from Master Roadmap)
**File:** `lan_service.py`
- [ ] Actual mDNS discovery implementation
- [ ] Peer connection establishment
- [ ] Connection retry logic

#### 11.3 Add Type Hints to Legacy Services (from Master Roadmap)
**Files needing type hints:**
- [ ] Legacy route handlers
- [ ] Older service files
- [ ] Migration scripts

---

### TIER 12: SWIFT TODO ITEMS

Context and search integrations that need backend wiring.

#### 12.1 Context Engine Integration
| File | Line | TODO |
|------|------|------|
| `AppContext.swift` | 507 | Query backend ANE Context Engine |
| `AppContext.swift` | 778-779 | Determine workflow status from state |
| `AppContext.swift` | 784 | Implement KanbanStore/TeamStore |
| `ContextBundle.swift` | 342 | Semantic search for similar queries |
| `ContextBundle.swift` | 349 | DatabaseService query search |
| `ContextBundle.swift` | 451 | Integrate with MagnetarCode |
| `ContextBundle.swift` | 619 | Get models from HotSlotManager |
| `ChatStore.swift` | 409 | Semantic search for vault files |

#### 12.2 Workflow Queue
- [ ] `WorkflowQueueView.swift:218` - Add assignee field to WorkItem model

---

### TIER 13: OFFLINE-FIRST COMPLIANCE

Ensure all features work without network.

#### 13.1 Network Failure Graceful Degradation
| Component | Current Behavior | Required |
|-----------|------------------|----------|
| Password registration | Fails completely | Allow with warning |
| Model listing | HTTP 500 | Return cached |
| LAN discovery | Fails if no Google DNS | Use local methods |
| N8N workflows | Exception raised | Return cached |
| Sync operations | Data lost silently | Persist and retry |

#### 13.2 Air-Gap Mode
- [ ] Add `MAGNETAR_AIRGAP_MODE=true` env var
- [ ] Skip all external network calls
- [ ] Use local-only discovery
- [ ] Disable cloud features gracefully

---

### TIER 14: LARGE TASKS (from Master Roadmap)

#### 14.1 Complete Mesh Relay Implementation
**File:** `mesh_relay.py`

Current: All connection methods are stubs:
```python
async def send(self, message): pass  # TODO
async def ping(self): pass  # TODO
async def close(self): pass  # TODO
```

- [ ] Full libp2p relay implementation
- [ ] Message routing
- [ ] Peer discovery

#### 14.2 Implement Workflow Persistence (from Master Roadmap)
**File:** `automation_router.py`

Current: Workflows not persisted across restarts

- [ ] SQLite storage for automation definitions
- [ ] Workflow state recovery
- [ ] Execution history

---

## 🔲 FINAL: MAGNETARCLOUD FULL SYNC

**Prerequisites:** All above tiers complete
**Estimated Time:** 7-8 hours
**Risk Level:** HIGH - Cloud infrastructure and sync logic

### Already Completed (from Tier 5.2):
- ✅ Device pairing endpoints
- ✅ Cloud token management
- ✅ Token refresh flow
- ✅ Device fingerprinting
- ✅ Session management
- ✅ Emergency revocation

### Remaining Work:

#### 15.1: OAuth 2.0 Integration (2 hours)
**Backend:**
- [ ] OAuth client registration
- [ ] Authorization endpoint handler
- [ ] Token exchange endpoint
- [ ] Secure token storage (encrypted)

**Swift:**
- [ ] OAuthService.swift
- [ ] Authorization URL generation
- [ ] Redirect callback handling
- [ ] Keychain token storage
- [ ] Automatic token refresh

#### 15.2: Sync Service Backend (2 hours)
**Endpoints:**
- [ ] `/v1/cloud/sync/vault` - Vault sync
- [ ] `/v1/cloud/sync/workflows` - Workflow sync
- [ ] `/v1/cloud/sync/teams` - Team sync
- [ ] `/v1/cloud/sync/status` - Sync status
- [ ] `/v1/cloud/sync/conflicts` - Conflict resolution

**Database:**
- [ ] sync_state table
- [ ] sync_conflicts table
- [ ] sync_log table

#### 15.3: Sync Service Swift Client (1.5 hours)
- [ ] SyncService.swift - Main sync coordinator
- [ ] SyncState.swift - Sync status tracking
- [ ] ConflictResolver.swift - Conflict resolution UI
- [ ] Background sync with NSBackgroundActivityScheduler

#### 15.4: Cloud Storage Integration (1 hour)
- [ ] Chunked upload for large files
- [ ] Resume support after interruption
- [ ] Background upload queue
- [ ] Progress tracking

#### 15.5: MagnetarHub Cloud UI (0.5 hours)
- [ ] Cloud connection status indicator
- [ ] Sync now button
- [ ] Conflict resolution modal
- [ ] Cloud storage usage display

---

## 📊 CODEBASE HEALTH (2025-12-26)

### Test Suite
- **Tests:** 599 passing
- **Duration:** ~74 seconds
- **Coverage:** Estimated 75%+

### Code Metrics
| Language | Files | Lines |
|----------|-------|-------|
| Python | 495 | 133,094 |
| Swift | 230 | 44,190 |

### Technical Debt
| Issue | Count |
|-------|-------|
| TODO/FIXME (Python) | 12 |
| TODO/FIXME (Swift) | 20 |
| DEPRECATED markers | 56 |
| Empty button closures | 6 |
| Hardcoded localhost URLs | 18 |
| SQL injection risks | 4 |
| Debug print() statements | 330 |

### Files > 1,000 Lines (Future Refactoring)
1. workflow_orchestrator.py - 1,139 lines
2. vault/sharing.py - 1,130 lines
3. vault_auth.py - 1,121 lines
4. vault/core.py - 1,088 lines
5. mesh_relay.py - 1,078 lines
6. permissions/admin.py - 1,040 lines

---

## 📅 EFFORT SUMMARY

| Tier | Items | Est. Time | Priority |
|------|-------|-----------|----------|
| 7: Trivial | 10 | 1-2 hours | LOW |
| 8: Easy | 7 | 2-3 hours | MEDIUM |
| 9: Moderate | 6 | 3-4 hours | MEDIUM |
| 10: Complex | 5 | 6-8 hours | HIGH |
| 11: Medium Tasks | 3 | 3-4 hours | MEDIUM |
| 12: Swift TODOs | 9 | 4-5 hours | MEDIUM |
| 13: Offline-First | 2 | 2-3 hours | HIGH |
| 14: Large Tasks | 2 | 6-8 hours | LOW |
| 15: Cloud Sync | 5 | 7-8 hours | LOW |
| **TOTAL** | 49 | ~35-45 hours | |

---

## 📋 SUPERSEDES

This roadmap consolidates and supersedes:
- `MagnetarStudio_Master_Roadmap.md` (Dec 23, 2025)
- All previous roadmap documents in `/Documents/Roadmaps/`

---

**Last Updated:** 2025-12-26
**Status:** Tiers 7-14 pending, then MagnetarCloud Full Sync
