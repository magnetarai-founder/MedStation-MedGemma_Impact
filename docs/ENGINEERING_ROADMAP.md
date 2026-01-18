# MagnetarStudio Engineering Roadmap

> **Target:** Post-iPad launch + Kaggle submission (Feb-March 2026)
> **Last Updated:** January 16, 2026

---

## Table of Contents

1. [Vision & Philosophy](#vision--philosophy)
2. [Current State Assessment](#current-state-assessment)
3. [Priority Matrix](#priority-matrix)
4. [Phase Timeline](#phase-timeline)
5. [Technical Appendices](#technical-appendices)

---

## Vision & Philosophy

### iPad Design Philosophy = "Local-First Simplicity"

The iPad app demonstrates the target architecture:

- **45 focused Swift files** vs Mac's **250+ Python files**
- **Zero backend dependency** - all data stays on device
- **Single entry point**: `ContentView.swift` is literally ONE line
- **Build-time purity**: XcodeGen excludes 60+ files to prevent backend creep
- **Graceful degradation**: Features disable cleanly, never crash

### Core Design Principles

| Principle | Description |
|-----------|-------------|
| **Less is more** | Hide complexity by default |
| **Spawnable windows** | Don't cram everything in one view |
| **User choice** | Let users customize their workspace |
| **Clean aesthetics** | iPad polish brought to Mac |
| **Progressive disclosure** | Show features as needed |
| **Offline-first** | Always works, always fast |

### What This Eliminates

- Overwhelming main interface
- Feature discoverability problems
- "Too much at once" cognitive load
- Cluttered navigation and header bars

---

## Current State Assessment

### Code Quality Scorecard

| Area | Score | Grade |
|------|-------|-------|
| Configuration Management | 9/10 | A |
| Testing Infrastructure | 8/10 | B+ |
| Security Practices | 7/10 | B- |
| Module Cohesion | 6/10 | C+ |
| Abstraction Quality | 6/10 | C+ |
| Layering | 5/10 | C |
| Dependency Direction | 4/10 | D+ |
| State Management | 3/10 | D- |
| Database Access | 4/10 | D+ |

**Overall Grade: C+ (65/100)** | **Health Score: 7.3/10**

### Executive Metrics

| Metric | Count | Status |
|--------|-------|--------|
| Python Files (Total) | 6,701 | Reviewed |
| Swift Files | 235 | Reviewed |
| Backend API Files | 504 | Reviewed |
| Test Files | 93 | Reviewed |
| Test Methods | 1,103 | Reviewed |
| Root-level API Files | 141 | **Organized into packages** |
| Direct SQLite Connections | 365 | **Needs Consolidation** |

### The Gap: Mac Backend vs iPad Philosophy

| Aspect | iPad (Target) | Mac (Current) |
|--------|--------------|---------------|
| Entry Point | 1 line: `ChatWorkspace()` | Complex auth + multi-service init |
| File Count | 45 focused files | 250+ files with god objects |
| State Management | `@Observable` stores | Global dicts (thread-unsafe) |
| Database Access | Local files + UserDefaults | 124 files with direct `sqlite3.connect()` |
| Error Handling | Graceful degradation | 50+ broad `except Exception` |
| Dependencies | 2 external packages | 40+ Python packages |
| Feature Disclosure | Progressive (hidden by default) | Everything visible at once |

---

## Priority Matrix

### P0 - Fix Immediately (< 1 day)

Critical bugs that can cause runtime crashes or security issues.

#### ErrorCode Enum Bugs (Runtime Crash)

| Issue | File | Line(s) | Fix | Status |
|-------|------|---------|-----|--------|
| `AUTH_ERROR` doesn't exist | `routes/user_models.py` | 144, 213, 279, 401, 459 | Use `UNAUTHORIZED` | **COMPLETE** |
| `RATE_LIMIT` doesn't exist | `routes/team/invitations.py` | 268 | Use `RATE_LIMITED` | **COMPLETE** |
| `RATE_LIMIT` doesn't exist | `routes/vault/files/download.py` | 210 | Use `RATE_LIMITED` | **COMPLETE** |
| `RATE_LIMIT` doesn't exist | `routes/vault/files/search.py` | 143, 225, 350, 487 | Use `RATE_LIMITED` | **COMPLETE** |

#### Security & Stability

| Issue | Files | Fix | Status |
|-------|-------|-----|--------|
| Thread-unsafe global state | `core/state.py` | Add `threading.RLock` wrappers | **COMPLETE** |
| Sessions router missing auth | `routes/sessions.py` | Add `Depends(get_current_user)` | **COMPLETE** |
| Silent audit failures | `audit/logger.py` | Add fallback queue | **COMPLETE** |
| Setup wizard admin bypass | `setup_wizard_routes.py` | Add users-exist check | **COMPLETE** |
| WebSocket token in query params | `websocket/collab.py` | Remove query param fallback | **COMPLETE** |

---

### P1 - High Priority (< 1 week)

#### SQL Injection Vulnerabilities

F-string SQL construction - verified all use proper protections:

| File | Line(s) | Risk | Status |
|------|---------|------|--------|
| `insights/routes/recordings.py` | 263 | HIGH | **COMPLETE** (whitelist + quote_identifier) |
| `insights/routes/templates.py` | 153 | HIGH | **COMPLETE** (whitelist + quote_identifier) |
| `offline_data_sync.py` | 400, 416, 423 | HIGH | **COMPLETE** (SYNCABLE_TABLES whitelist + quote_identifier) |
| `permissions/engine.py` | 256, 320 | MEDIUM | **COMPLETE** (safe placeholder pattern) |
| `db/consolidation_migration.py` | 80, 83 | MEDIUM | **COMPLETE** (validate_identifier + quote_identifier) |

**All SQL uses proper protections:** whitelist validation, `quote_identifier()`, parameterized values.

#### Swift Force-Unwrapped URLs (Crash Risk)

All instances now use safe `guard let url = URL(string:)` pattern:

| File | Line(s) | Status |
|------|---------|--------|
| `ModelManagementSettingsView.swift` | 263 | **COMPLETE** |
| `TeamWorkspace.swift` | 251 | **COMPLETE** |
| `SmartModelPicker.swift` | 153 | **COMPLETE** |
| `ModelManagerWindow.swift` | 381, 405 | **COMPLETE** |
| `SetupWizardView.swift` | 178 | **COMPLETE** |
| `ModelMemoryTracker.swift` | 89 | **COMPLETE** |
| `ModelTagService.swift` | 25, 59, 93, 134 | **COMPLETE** |
| `SecurityManager.swift` | 219 | **COMPLETE** |

**All Swift URLs use guard-let pattern with proper error handling.**

#### Code Duplication

| Duplicate | Status | Resolution |
|-----------|--------|------------|
| `compute_cosine_similarity()` | **COMPLETE** | Shared in `api/shared/semantic_utils.py` |
| `embed_query()` | **COMPLETE** | Shared in `api/shared/semantic_utils.py` |

**Both route files now import from `api.shared` instead of having local copies.**

#### Other P1 Issues

| Issue | Impact | Status |
|-------|--------|--------|
| Broad exception handlers | 50+ files with `except Exception` | Pending |
| Missing type hints | Heavy `Any` usage | Pending |
| Inconsistent error handling | 4+ different patterns | Pending |

---

### P2 - Medium Priority (< 1 month)

#### Monolithic Files Requiring Decomposition

Files exceeding 1000 lines violate single-responsibility:

| File | Lines | Recommendation | Status |
|------|-------|----------------|--------|
| `redshift_sql_processor.py` | 2,491 → 26 | Decompose into parser, executor, optimizer | **COMPLETE** (now shim + package) |
| `vault_auth.py` | 1,144 | Split auth flows, token mgmt, sessions | **COMPLETE** (split into vault/) |
| `workflow_orchestrator.py` | 1,139 → 28 | Extract stage handlers, condition evaluators | **COMPLETE** (workflows/ package) |
| `vault/sharing.py` | 1,131 → 399 | Separate ACL, invitations, share links | **COMPLETE** (split into vault/) |
| `vault/core.py` | 1,088 → 454 | Extract file ops, metadata, encryption | **COMPLETE** (split into vault/) |
| `mesh_relay.py` | 1,078 → 59 | Separate connection pool, routing, handshake | **COMPLETE** (mesh/ package) |
| `permissions/admin.py` | 1,040 → <1000 | Extract role mgmt, audit, bulk ops | **COMPLETE** (now in permissions/) |
| `team/storage.py` | 1,005 → <1000 | Separate CRUD, caching, query builders | **COMPLETE** (split into team/) |
| `terminal_api.py` | 972 → 104 | Extract WebSocket handlers, rate limiting | **COMPLETE** (terminal/ package) |
| `workflow_storage.py` | 922 | Separate persistence, caching, migration | **COMPLETE** (in workflows/ package) |
| `codex_engine.py` | 918 → 750 | Extract analysis, suggestions, context | **COMPLETE** (in agent/engines/) |
| `metal4_engine.py` | 890 → 662 | Separate GPU ops, memory, shaders | **COMPLETE** (metal4_engine/ package) |
| `code_operations.py` | 881 | Extract file tree, workspace, git ops | **COMPLETE** (code_operations/ package) |
| `lan_discovery.py` | 866 | Separate mDNS, heartbeat, retry logic | **COMPLETE** (lan_discovery/ package) |

#### Swift Monolithic Files (>500 lines)

| File | Lines | Recommendation | Status |
|------|-------|----------------|--------|
| `AppContext.swift` | 1,037 | Split into domain-specific contexts | Pending |
| `ChatStore.swift` | 910 | Extract streaming/session logic | Pending |
| `ContextBundle.swift` | 891 | Separate AI context types | Pending |
| `TrustService.swift` | 805 | Extract cryptographic operations | Pending |
| `TrustWorkspace.swift` | 598 | Split UI components | Pending |
| `VaultStore.swift` | 577 | Extract sync operations | Pending |

#### Database Connection Consolidation

**Status: PARTIALLY COMPLETE**

Connection pool implemented in `api/db/pool.py`:
- `SQLiteConnectionPool` class with WAL mode, health checks, auto-recycling
- `get_connection_pool()` singleton factory
- `close_all_pools()` cleanup function

**Current state:**
- Pool adopted by 5 files (security/session, docs/db, db/__init__, db_pool)
- 81 direct `.connect()` calls remain (down from 365)
- Migration files (30+) legitimately need direct connections

**Remaining work:**
- [ ] Migrate auth critical paths to use pool
- [ ] Migrate remaining service files to use pool
- [ ] Add connection pool metrics to observability

#### Deprecated Facades Removed

| Facade | Migration Target | Status |
|--------|------------------|--------|
| `chat_service.py` | `api.services.chat` | **COMPLETE** (already removed) |
| `vault_service.py` | `api.services.vault.core` | **COMPLETE** (already removed) |
| `team_service.py` | `api.services.team` | **COMPLETE** (already removed) |
| `workflow_service.py` | `api.workflows` | **COMPLETE** (removed Jan 18) |
| `p2p_chat_service.py` | `api.services.p2p_chat` | **COMPLETE** (already removed) |
| `backup_service.py` | `api.backup` | **COMPLETE** (removed Jan 18) |
| `trash_service.py` | `api.trash` | **COMPLETE** (removed Jan 18) |
| `focus_mode_service.py` | `api.focus_mode` | **COMPLETE** (removed Jan 18) |
| `accessibility_service.py` | `api.accessibility` | **COMPLETE** (removed Jan 18) |
| `undo_service.py` | `api.undo` | **COMPLETE** (removed Jan 18) |
| `e2e_encryption_service.py` | `api.security.e2e_encryption` | **COMPLETE** (removed Jan 18) |
| `encrypted_db_service.py` | `api.security.encrypted_db` | **COMPLETE** (removed Jan 18) |
| `lan_service.py` | `api.lan_discovery` | **COMPLETE** (removed Jan 18) |
| `docs_service.py` | `api.docs` | **COMPLETE** (removed Jan 18) |
| `insights_service.py` | `api.insights` | **COMPLETE** (removed Jan 18) |
| `secure_enclave_service.py` | `api.secure_enclave` | **COMPLETE** (removed Jan 18) |

*Note: `cache_service.py` retained as shim due to 20+ imports - migrate gradually.*

---

### P3 - Low Priority (Ongoing)

| Item | Status |
|------|--------|
| Reorganize 141 root-level API files into packages | **COMPLETE** |
| Increase test coverage gaps | Pending |
| Update documentation | Pending |
| Remove try/except import wrappers (200+ files) | **IN PROGRESS** (229 remaining in 163 files, down from 284 - 55 removed Jan 18) |

---

## Phase Timeline

### Phase 1: Bridge Completion (Weeks 3-4)

*Parallel to Kaggle prep*

#### 1.1 iPad-Mac Bridge Finalization

**New Directory Structure:**
```
apps/backend/api/
├── routes/sync/          # Unified sync endpoints
│   ├── workspace.py      # Bidirectional workspace sync
│   ├── chat.py           # Chat history sync
│   └── discovery.py      # P2P + LAN + cloud relay
├── services/sync/        # Sync business logic
│   ├── workspace_sync.py
│   ├── chat_sync.py
│   └── conflict_resolver.py
└── mesh/                 # Existing P2P code (refactor)
```

**Deliverables:**
- [ ] Workspace bidirectional sync API
- [ ] Chat session sync with conflict resolution
- [ ] Discovery protocol unification (P2P, LAN, cloud relay)
- [ ] WiFi Aware integration tests
- [ ] Offline → online transition handling

#### 1.2 Hugging Face Integration (Kaggle Essential)

**Phase 1 (Essential for Kaggle):**
- [ ] Basic HF model download (GGUF format only)
- [ ] MedGemma 1.5 4B integration specifically
- [ ] Unified model selector UI
- [ ] llama.cpp inference for HF GGUF models

---

### Phase 2: Major UI/UX Refactor (Weeks 7-12)

#### Phase 2A: Backend Preparation (Week 7-8)

**Goal:** Decouple backend services so each spawnable window can operate independently.

**God Object Decomposition:**
```
# Before
data_engine.py (2000+ lines)

# After (iPad-style)
services/data_engine/
├── __init__.py              # Clean facade
├── parsers/
│   ├── excel.py
│   ├── csv.py
│   ├── json.py
│   └── parquet.py
├── schema_inference.py
├── sql_generator.py
├── query_executor.py
└── metadata.py
```

**State Management Refactor:**
```python
# Replace thread-unsafe globals in core/state.py
from api.core.stores import ChatStore, QueryStore, SessionStore

chat_store = ChatStore()      # Thread-safe with RLock
query_store = QueryStore()    # With LRU eviction
session_store = SessionStore()
```

#### Phase 2B: Main Interface Redesign (Week 9-10)

- Header simplification: `[Logo] [Tab Switcher] [Quick Action Button]`
- Workspace/Channels (Slack-style)
- Data section redesign (iPad clean interface)
- Files tab (Vault → Files): "Finder meets Proton Drive"

#### Phase 2C: Spawnable Windows Architecture (Week 11)

| Window | Default | Pop-out Behavior |
|--------|---------|------------------|
| Documents | Main window | Pages aesthetic + AI chat specific to doc |
| Spreadsheets | Main window | Numbers aesthetic + AI chat specific to sheet |
| PDF Editor | Main window | Preview + Adobe power |
| Code | Spawned | Always connected to workspace context |
| Project Mgmt | OFF (toggleable) | Kanban/Confluence style |
| Automations | OFF (toggleable) | Workflow builder |

#### Phase 2D: Feature Toggles & Settings (Week 12)

```python
class FeatureFlags(BaseModel):
    # Core features (always ON)
    workspace: bool = True
    chat: bool = True
    files: bool = True

    # Optional features (OFF by default)
    project_management: bool = False
    automations: bool = False
    data_analysis: bool = False
    voice_transcription: bool = True  # Key differentiator
```

---

### Timeline Summary

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1-2 | Ship iPad | iPad app ready |
| 3-4 | Bridge + Kaggle | Workspace sync, MedGemma integration |
| 5-6 | Kaggle Polish | Submission ready, HF download working |
| 7-8 | 2A: Backend Prep | God object decomposition, state management |
| 9-10 | 2B: Interface | Header, Workspace/Channels, Files redesign |
| 11 | 2C: Windows | Spawnable window architecture |
| 12 | 2D: Toggles | Feature flags, settings, polish |
| 13+ | Feature Completion | Healthcare features, enterprise readiness |

---

## Success Criteria

### Technical Quality
- [ ] Zero thread-unsafe global state
- [ ] Zero direct `sqlite3.connect()` (use registry)
- [ ] Zero god objects >500 lines
- [ ] Zero broad `except Exception` handlers
- [ ] All ErrorCode enum values valid

### Design Philosophy
- [ ] Mac matches iPad's "less is more" clarity
- [ ] Features hidden by default, progressive disclosure
- [ ] Spawnable windows reduce cognitive load

### Kaggle
- [ ] MedGemma 1.5 4B working by Feb 24
- [ ] Healthcare workflow queue functional

---

## Technical Appendices

### Appendix A: ErrorCode Enum Reference

Valid `ErrorCode` values (from `api/routes/schemas/errors.py`):

```python
class ErrorCode(str, Enum):
    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"      # NOT AUTH_ERROR
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"      # NOT RATE_LIMIT
    BAD_REQUEST = "BAD_REQUEST"
    GONE = "GONE"

    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    GATEWAY_ERROR = "GATEWAY_ERROR"
    TIMEOUT = "TIMEOUT"
```

### Appendix B: Safe SQL Patterns

**Always use:**
```python
from api.security.sql_safety import quote_identifier, SafeSQLBuilder

# For dynamic identifiers
table = quote_identifier(user_input)

# For complex queries
builder = SafeSQLBuilder()
builder.select("*").from_table(table_name).where("id = ?", [user_id])
```

**Never use:**
```python
# DANGEROUS - SQL injection vector
cursor.execute(f"SELECT * FROM {table_name} WHERE id = {user_id}")
```

### Appendix C: Swift URL Safety Pattern

**Replace:**
```swift
let url = URL(string: urlString)!  // CRASH if invalid
```

**With:**
```swift
guard let url = URL(string: urlString) else {
    logger.error("Invalid URL: \(urlString)")
    return
}
```

### Appendix D: Technical Debt Summary

| Category | Items | Estimated Effort |
|----------|-------|------------------|
| Critical Bugs (P0) | 10 | 4 hours |
| Security Issues (P1) | 8 | 4 hours |
| Code Duplication | 4 | 2 days |
| Monolithic Files | 20 | 3 weeks |
| Deprecated Code | 5 | 3 days |
| Documentation | - | 2 weeks |

**Total Estimated Technical Debt: ~4-6 weeks of engineering time**

---

### Appendix E: Pricing & Tiers

#### Individual Tier: FREE
- Full access to core productivity suite
- Documents, spreadsheets, PDFs, notes
- Voice transcription
- Local AI integration
- Code mode included

#### Team Tier: PAID
- Everything in Individual
- Team collaboration features
- Multi-user workspaces
- Chat/messaging
- Shared workspace sync
- Team workflows and automations

#### MagnetarMission
- Unlocks Team tier for Christian organizations
- Free verification process

---

*Generated from CODE_QUALITY_REVIEW.md + REFACTOR_ROADMAP.md*
*Last Updated: January 16, 2026*
