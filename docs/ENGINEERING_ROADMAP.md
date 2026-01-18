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
| `AUTH_ERROR` doesn't exist | `routes/user_models.py` | 144, 213, 279, 401, 459 | Use `UNAUTHORIZED` | Pending |
| `RATE_LIMIT` doesn't exist | `routes/team/invitations.py` | 268 | Use `RATE_LIMITED` | Pending |
| `RATE_LIMIT` doesn't exist | `routes/vault/files/download.py` | 210 | Use `RATE_LIMITED` | Pending |
| `RATE_LIMIT` doesn't exist | `routes/vault/files/search.py` | 143, 225, 350, 487 | Use `RATE_LIMITED` | Pending |

#### Security & Stability

| Issue | Files | Fix | Status |
|-------|-------|-----|--------|
| Thread-unsafe global state | `core/state.py` | Add `threading.RLock` wrappers | Pending |
| Sessions router missing auth | `routes/sessions.py` | Add `Depends(get_current_user)` | Pending |
| Silent audit failures | `audit_logger.py` | Add fallback queue | Pending |
| Setup wizard admin bypass | `setup_wizard_routes.py` | Add users-exist check | Pending |
| WebSocket token in query params | `auth_middleware.py` | Remove query param fallback | Pending |

---

### P1 - High Priority (< 1 week)

#### SQL Injection Vulnerabilities

F-string SQL construction bypassing parameterization:

| File | Line(s) | Risk | Status |
|------|---------|------|--------|
| `insights/routes/recordings.py` | 263 | HIGH | Pending |
| `insights/routes/templates.py` | 153 | HIGH | Pending |
| `offline_data_sync.py` | 236, 586, 602, 609 | HIGH | Pending |
| `workflow_storage.py` | 195 | MEDIUM | Pending |
| `db_consolidation_migration.py` | 79, 82 | MEDIUM | Pending |

**Fix:** Use `quote_identifier()` from `api/security/sql_safety.py` or `SafeSQLBuilder`.

#### Swift Force-Unwrapped URLs (Crash Risk)

13 instances of `URL(string:)!` that will crash on invalid input:

| File | Line(s) | Status |
|------|---------|--------|
| `ModelManagementSettingsView.swift` | 263 | Pending |
| `TeamWorkspace.swift` | 251 | Pending |
| `SmartModelPicker.swift` | 153 | Pending |
| `ModelManagerWindow.swift` | 381, 401 | Pending |
| `SetupWizardView.swift` | 178 | Pending |
| `ModelMemoryTracker.swift` | 89 | Pending |
| `EmergencyModeService+Backend.swift` | 60 | Pending |
| `ModelTagService.swift` | 25, 57, 89, 128 | Pending |
| `SecurityManager.swift` | 219 | Pending |

**Fix:** Replace with guard-let pattern.

#### Code Duplication

| Duplicate | Locations | Action |
|-----------|-----------|--------|
| `compute_cosine_similarity()` | `data/semantic_search.py:174`, `vault/semantic_search.py:189` | Create `api/utils/math.py` |
| `embed_query()` | `data/semantic_search.py:142`, `vault/semantic_search.py:158` | Create `api/ml/embeddings.py` |

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
| `redshift_sql_processor.py` | 2,491 | Decompose into parser, executor, optimizer | Pending |
| `vault_auth.py` | 1,144 | Split auth flows, token mgmt, sessions | Pending |
| `workflow_orchestrator.py` | 1,139 | Extract stage handlers, condition evaluators | Pending |
| `vault/sharing.py` | 1,131 | Separate ACL, invitations, share links | Pending |
| `vault/core.py` | 1,088 | Extract file ops, metadata, encryption | Pending |
| `mesh_relay.py` | 1,078 | Separate connection pool, routing, handshake | Pending |
| `permissions/admin.py` | 1,040 | Extract role mgmt, audit, bulk ops | Pending |
| `team/storage.py` | 1,005 | Separate CRUD, caching, query builders | Pending |
| `terminal_api.py` | 972 | Extract WebSocket handlers, rate limiting | Pending |
| `workflow_storage.py` | 922 | Separate persistence, caching, migration | Pending |
| `codex_engine.py` | 918 | Extract analysis, suggestions, context | Pending |
| `metal4_engine.py` | 890 | Separate GPU ops, memory, shaders | Pending |
| `code_operations.py` | 881 | Extract file tree, workspace, git ops | Pending |
| `lan_discovery.py` | 866 | Separate mDNS, heartbeat, retry logic | Pending |

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

**365 direct SQLite connections** found. Consolidate through:

```python
# Target: apps/backend/api/db/registry.py
class DatabaseRegistry:
    """Single source of truth for all database connections"""
    _pools: dict[str, SQLiteConnectionPool] = {}

    @classmethod
    def get_connection(cls, db_name: str) -> ContextManager[sqlite3.Connection]:
        """All files should use this instead of sqlite3.connect()"""
```

#### Deprecated Facades to Remove

| Facade | Migration Target | Status |
|--------|------------------|--------|
| `chat_service.py` | `api.services.chat` | Pending |
| `vault_service.py` | `api.services.vault.core` | Pending |
| `team_service.py` | `api.services.team` | Pending |
| `workflow_service.py` | `api.services.workflow_orchestrator` | Pending |
| `p2p_chat_service.py` | `api.services.p2p_chat` | Pending |

---

### P3 - Low Priority (Ongoing)

| Item | Status |
|------|--------|
| Reorganize 141 root-level API files into packages | **COMPLETE** |
| Increase test coverage gaps | Pending |
| Update documentation | Pending |
| Remove try/except import wrappers (200+ files) | Pending |

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
